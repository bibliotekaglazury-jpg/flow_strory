"""Subtitle Studio persistence and ownership: projects, immutable exports, durable jobs.

Creation only validates, checks idempotency and enqueues a durable job row; the actual
Gemini call and render happen in the worker (app/subtitles/jobs.py, app/subtitles/providers.py),
same separation as Generation.create() vs the video worker.
"""

import base64
import json
import secrets
from datetime import datetime

from sqlalchemy import and_, delete as sa_delete, or_, select

from app.config import settings
from app.db import Asset, SubtitleExport, SubtitleJob, SubtitleProject, now
from app.errors import DomainError
from app.services.prompts import fingerprint
from app.services.storage import Storage, asset_view

EXPORT_TERMINAL = {"completed", "failed"}

MIN_DURATION_SECONDS = 1
DEFAULT_STYLE = {
    "preset": "modern",
    "position": "bottom",
    "size": "medium",
    "safeArea": True,
    "textColor": "#FFFFFF",
    "highlightColor": "#C9FF27",
}
LIST_LIMIT = 20


def _idempotency_key(key):
    if not key or len(key) > 200:
        raise DomainError("INVALID_IDEMPOTENCY_KEY", "Provide a valid Idempotency-Key.", 400)
    return key


def owned(db, user_id, project_id):
    project = db.scalar(
        select(SubtitleProject).where(
            SubtitleProject.id == project_id, SubtitleProject.user_id == user_id
        )
    )
    if not project:
        raise DomainError("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.", 404)
    return project


def owned_export(db, user_id, project_id, export_id):
    # owned() first, so a foreign project id 404s the same way a foreign export id does.
    owned(db, user_id, project_id)
    export = db.scalar(
        select(SubtitleExport).where(
            SubtitleExport.id == export_id,
            SubtitleExport.project_id == project_id,
            SubtitleExport.user_id == user_id,
        )
    )
    if not export:
        raise DomainError("SUBTITLE_EXPORT_NOT_FOUND", "That export is unavailable.", 404)
    return export


def delete(db, user_id, project_id):
    """Deletes a project and everything under it. Children are removed explicitly rather than
    left to the DB's ON DELETE CASCADE: SQLite (used in tests) does not enforce foreign keys by
    default, so relying on it silently orphans rows there while working in Postgres. The source
    video asset is left alone — it is a reusable library asset, not owned by this project."""
    project = owned(db, user_id, project_id)
    export_ids = list(db.scalars(select(SubtitleExport.id).where(SubtitleExport.project_id == project_id)))
    db.execute(
        sa_delete(SubtitleJob).where(
            or_(SubtitleJob.project_id == project_id, SubtitleJob.export_id.in_(export_ids))
        )
    )
    db.execute(sa_delete(SubtitleExport).where(SubtitleExport.project_id == project_id))
    db.delete(project)
    db.flush()


def _owned_source_video(db, user_id, asset_id):
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id))
    if not asset or asset.role not in ("source_video", "output_video"):
        raise DomainError("INVALID_ASSET", "Source video is unavailable.", 404)
    if not asset.mime_type.startswith("video/"):
        raise DomainError("INVALID_ASSET", "Source asset must be a video.", 422)
    duration = asset.duration_seconds or 0
    limit = settings().subtitle_max_duration_seconds
    if not (MIN_DURATION_SECONDS <= duration <= limit):
        raise DomainError(
            "INVALID_ASSET",
            f"Source video must be between 1 second and {limit // 60} minutes.",
            422,
        )
    return asset


def create(db, user_id, body, key):
    key = _idempotency_key(key)
    digest = fingerprint(body.model_dump())
    prior = db.scalar(
        select(SubtitleProject).where(
            SubtitleProject.user_id == user_id, SubtitleProject.idempotency_key == key
        )
    )
    if prior:
        if prior.idempotency_hash != digest:
            raise DomainError(
                "IDEMPOTENCY_CONFLICT", "This request key was already used for different inputs.", 409
            )
        return prior
    asset = _owned_source_video(db, user_id, body.sourceAssetId)
    project = SubtitleProject(
        user_id=user_id,
        source_asset_id=asset.id,
        status="transcribing",
        aspect_ratio=body.aspectRatio,
        language=None,
        duration_ms=round((asset.duration_seconds or 0) * 1000),
        revision=0,
        cues=[],
        style=dict(DEFAULT_STYLE),
        idempotency_key=key,
        idempotency_hash=digest,
    )
    db.add(project)
    db.flush()
    db.add(SubtitleJob(kind="transcribe", project_id=project.id))
    db.flush()
    return project


def list_projects(db, user_id, limit, cursor):
    query = select(SubtitleProject).where(SubtitleProject.user_id == user_id)
    if cursor:
        try:
            created, id = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            created = datetime.fromisoformat(created)
        except (ValueError, TypeError):
            raise DomainError("INVALID_CURSOR", "Project cursor is invalid.", 400) from None
        query = query.where(
            or_(
                SubtitleProject.created_at < created,
                and_(SubtitleProject.created_at == created, SubtitleProject.id < id),
            )
        )
    rows = list(
        db.scalars(
            query.order_by(SubtitleProject.created_at.desc(), SubtitleProject.id.desc()).limit(
                limit + 1
            )
        )
    )
    more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        base64.urlsafe_b64encode(
            json.dumps([rows[-1].created_at.isoformat(), rows[-1].id]).encode()
        )
        .decode()
        .rstrip("=")
        if more
        else None
    )
    return rows, next_cursor


def update(db, user_id, project_id, body):
    project = owned(db, user_id, project_id)
    if project.revision != body.revision:
        raise DomainError(
            "REVISION_CONFLICT", "The project changed. Reload it before saving again.", 409
        )
    last_end = project.duration_ms
    for cue in body.cues:
        if cue.endMs > last_end:
            raise DomainError("INVALID_INPUT", "A cue cannot extend past the source duration.", 422)
    project.aspect_ratio = body.aspectRatio
    project.cues = [cue.model_dump() for cue in body.cues]
    project.style = body.style.model_dump()
    project.revision += 1
    project.updated_at = now()
    db.flush()
    return project


def create_export(db, user_id, project_id, body, key):
    key = _idempotency_key(key)
    project = owned(db, user_id, project_id)
    digest = fingerprint({"projectId": project_id, **body.model_dump()})
    prior = db.scalar(
        select(SubtitleExport).where(
            SubtitleExport.user_id == user_id, SubtitleExport.idempotency_key == key
        )
    )
    if prior:
        if prior.idempotency_hash != digest:
            raise DomainError(
                "IDEMPOTENCY_CONFLICT", "This request key was already used for different inputs.", 409
            )
        return prior
    if project.revision != body.revision:
        raise DomainError(
            "REVISION_CONFLICT", "The project changed. Reload it before exporting again.", 409
        )
    export = SubtitleExport(
        project_id=project.id,
        user_id=user_id,
        source_revision=project.revision,
        # Frozen now: later edits to the live project must never reach this export.
        cues=list(project.cues),
        style=dict(project.style),
        aspect_ratio=project.aspect_ratio,
        status="queued",
        progress=None,
        output_asset_id=None,
        idempotency_key=key,
        idempotency_hash=digest,
    )
    db.add(export)
    db.flush()
    db.add(SubtitleJob(kind="render", export_id=export.id))
    db.flush()
    return export


def create_share(db, user_id, project_id, export_id):
    """Idempotent: pressing Share twice returns the same link instead of invalidating it.
    Only a completed export can be shared — there is nothing to watch otherwise."""
    export = owned_export(db, user_id, project_id, export_id)
    if export.status != "completed":
        raise DomainError("EXPORT_NOT_READY", "This export has not finished rendering yet.", 409)
    if export.share_token and not export.share_revoked_at:
        return export
    export.share_token = secrets.token_urlsafe(24)
    export.share_revoked_at = None
    export.updated_at = now()
    db.flush()
    return export


def revoke_share(db, user_id, project_id, export_id):
    export = owned_export(db, user_id, project_id, export_id)
    if export.share_token and not export.share_revoked_at:
        export.share_revoked_at = now()
        export.updated_at = now()
        db.flush()
    return export


def shared_export(db, token):
    """Public lookup by token only: no user_id filter, so this must never leak anything
    beyond what a stranger with the link is meant to see."""
    export = db.scalar(
        select(SubtitleExport).where(
            SubtitleExport.share_token == token, SubtitleExport.share_revoked_at.is_(None)
        )
    )
    if not export or export.status != "completed":
        raise DomainError("SHARE_NOT_FOUND", "This share link is unavailable.", 404)
    return export


def shared_export_view(db, export, storage=None):
    storage = storage or Storage()
    output = None
    if export.output_asset_id:
        asset = db.get(Asset, export.output_asset_id)
        output = asset_view(asset, storage) if asset else None
    return {"id": export.id, "outputAsset": output, "aspectRatio": export.aspect_ratio}


def _latest_export(db, project_id):
    return db.scalar(
        select(SubtitleExport)
        .where(SubtitleExport.project_id == project_id)
        .order_by(SubtitleExport.created_at.desc())
        .limit(1)
    )


def export_view(db, export, storage=None):
    storage = storage or Storage()
    output = None
    if export.output_asset_id:
        asset = db.get(Asset, export.output_asset_id)
        output = asset_view(asset, storage) if asset else None
    return {
        "id": export.id,
        "status": export.status,
        "progress": export.progress,
        "outputAsset": output,
        "error": export.error,
        # Present only while a share link is live; the frontend builds the full URL
        # (it knows its own origin, the API does not).
        "shareToken": export.share_token if export.share_token and not export.share_revoked_at else None,
        "createdAt": export.created_at,
        "updatedAt": export.updated_at,
    }


def view(db, project, storage=None):
    storage = storage or Storage()
    source = db.get(Asset, project.source_asset_id)
    latest = _latest_export(db, project.id)
    return {
        "id": project.id,
        "sourceAsset": asset_view(source, storage),
        "status": project.status,
        "aspectRatio": project.aspect_ratio,
        "language": project.language,
        "durationMs": project.duration_ms,
        "revision": project.revision,
        "cues": project.cues,
        "style": project.style,
        "latestExport": export_view(db, latest, storage) if latest else None,
        "error": project.error,
        "createdAt": project.created_at,
        "updatedAt": project.updated_at,
    }


def summary_view(db, project, storage=None):
    storage = storage or Storage()
    source = db.get(Asset, project.source_asset_id)
    latest = _latest_export(db, project.id)
    return {
        "id": project.id,
        "sourceAsset": asset_view(source, storage),
        "status": project.status,
        "aspectRatio": project.aspect_ratio,
        "durationMs": project.duration_ms,
        "latestExport": export_view(db, latest, storage) if latest else None,
        "createdAt": project.created_at,
        "updatedAt": project.updated_at,
    }
