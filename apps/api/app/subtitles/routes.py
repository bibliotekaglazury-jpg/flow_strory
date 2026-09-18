"""Subtitle Studio API: ownership-enforced project/export CRUD over app.subtitles.service."""

from fastapi import APIRouter, Depends, Header, Query, Response

from app.auth import identity
from app.db import session as db_session
from app.errors import DomainError
from app.subtitles import service
from app.subtitles.schemas import SubtitleExportCreate, SubtitleProjectCreate, SubtitleProjectPatch
from app.subtitles.srt import render_srt
from app.responses import (
    SubtitleExportPollResponse,
    SubtitleExportResponse,
    SubtitleExportSrtResponse,
    SubtitleProjectResponse,
    SubtitleProjectsResponse,
    SubtitleSharedExportResponse,
)

router = APIRouter(prefix="/api/subtitle-projects")
public_router = APIRouter(prefix="/api/subtitle-shares")


@router.post("", response_model=SubtitleProjectResponse, status_code=202)
def create(
    body: SubtitleProjectCreate,
    idempotency_key: str = Header(),
    user=Depends(identity),
    db=Depends(db_session),
):
    return {"project": service.view(db, service.create(db, user, body, idempotency_key))}


@router.get("", response_model=SubtitleProjectsResponse)
def list_projects(
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user=Depends(identity),
    db=Depends(db_session),
):
    rows, next_cursor = service.list_projects(db, user, limit, cursor)
    return {
        "projects": [service.summary_view(db, project) for project in rows],
        "nextCursor": next_cursor,
    }


@router.get("/{project_id}", response_model=SubtitleProjectResponse)
def get(project_id: str, user=Depends(identity), db=Depends(db_session)):
    return {"project": service.view(db, service.owned(db, user, project_id))}


@router.patch("/{project_id}", response_model=SubtitleProjectResponse)
def update(
    project_id: str,
    body: SubtitleProjectPatch,
    user=Depends(identity),
    db=Depends(db_session),
):
    return {"project": service.view(db, service.update(db, user, project_id, body))}


@router.delete("/{project_id}", status_code=204)
def delete(project_id: str, user=Depends(identity), db=Depends(db_session)):
    service.delete(db, user, project_id)
    return Response(status_code=204)


@router.post("/{project_id}/exports", response_model=SubtitleExportResponse, status_code=202)
def create_export(
    project_id: str,
    body: SubtitleExportCreate,
    idempotency_key: str = Header(),
    user=Depends(identity),
    db=Depends(db_session),
):
    export = service.create_export(db, user, project_id, body, idempotency_key)
    return {"export": service.export_view(db, export)}


@router.get("/{project_id}/exports/{export_id}", response_model=SubtitleExportPollResponse)
def get_export(project_id: str, export_id: str, user=Depends(identity), db=Depends(db_session)):
    export = service.owned_export(db, user, project_id, export_id)
    return {
        "export": service.export_view(db, export),
        "pollAfterMs": None if export.status in service.EXPORT_TERMINAL else 2000,
    }


@router.get("/{project_id}/exports/{export_id}/srt", response_model=SubtitleExportSrtResponse)
def get_export_srt(project_id: str, export_id: str, user=Depends(identity), db=Depends(db_session)):
    export = service.owned_export(db, user, project_id, export_id)
    if export.status != "completed":
        raise DomainError("EXPORT_NOT_READY", "This export has not finished rendering yet.", 409)
    return {"content": render_srt(export.cues), "fileName": f"{export.id}.srt"}


@router.post("/{project_id}/exports/{export_id}/share", response_model=SubtitleExportResponse)
def share_export(project_id: str, export_id: str, user=Depends(identity), db=Depends(db_session)):
    export = service.create_share(db, user, project_id, export_id)
    return {"export": service.export_view(db, export)}


@router.delete("/{project_id}/exports/{export_id}/share", response_model=SubtitleExportResponse)
def unshare_export(project_id: str, export_id: str, user=Depends(identity), db=Depends(db_session)):
    export = service.revoke_share(db, user, project_id, export_id)
    return {"export": service.export_view(db, export)}


@public_router.get("/{token}", response_model=SubtitleSharedExportResponse)
def get_shared_export(token: str, db=Depends(db_session)):
    export = service.shared_export(db, token)
    return {"export": service.shared_export_view(db, export)}
