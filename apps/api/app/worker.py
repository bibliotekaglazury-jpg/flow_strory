"""Durable database worker. Redis notifications are optional; polling always recovers lost notifications."""

import asyncio
import logging
from datetime import timedelta
from pathlib import Path

from sqlalchemy import or_, select

from app.db import Generation, Job, Output, SessionLocal, now, uid
from app.providers import ProviderError
from app.services.assets import owned_inputs, store_asset
from app.services.credits import TERMINAL, finish
from app.services.generations import provider_input, registry
from app.services.product import download_public
from app.services.storage import Storage

log = logging.getLogger("ugc.worker")
LEASE_SECONDS = 120


def claim(db, owner):
    job = db.scalar(
        select(Job)
        .where(
            Job.submission_state.in_(["pending", "submitted", "intent"]),
            Job.next_run_at <= now(),
            or_(Job.lease_until.is_(None), Job.lease_until < now()),
        )
        .order_by(Job.next_run_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job:
        job.lease_owner = owner
        job.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
        job.attempts += 1
        db.flush()
        return job.id
    return None


def lock_job(db, job_id, owner):
    generation_id = db.scalar(select(Job.generation_id).where(Job.id == job_id))
    g = db.scalar(select(Generation).where(Generation.id == generation_id).with_for_update())
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if not job or job.lease_owner != owner:
        return None, None
    return g, job


def release(job, seconds=3):
    job.lease_owner = None
    job.lease_until = None
    job.next_run_at = now() + timedelta(seconds=seconds)


def simulation_fixture(duration, ratio):
    if duration not in {15, 20, 30} or ratio not in {"9:16", "1:1", "16:9"}:
        raise ValueError("Unsupported fixture configuration")
    return (
        Path(__file__).parent / "fixtures" / f"demo-{duration}-{ratio.replace(':', 'x')}.mp4"
    ).read_bytes()


async def process_render(job_id, owner):
    from app.config import settings
    from app.services.rendering import render, validate_inputs
    from app.services.templates import get_template, definition_fingerprint

    storage = Storage()
    try:
        with SessionLocal.begin() as db:
            g, job = lock_job(db, job_id, owner)
            if not g:
                return
            if g.status in TERMINAL:
                job.submission_state = "done"
                release(job)
                return
            snapshot = dict(g.snapshot)
            spec = get_template(snapshot["templateId"])
            if snapshot.get("renderDefinitionFingerprint") != definition_fingerprint(spec):
                raise ValueError("Template definition changed after admission")
            assets = validate_inputs(
                db, g.user_id, get_template(snapshot["templateId"]), snapshot.get("normalizedInputs")
            )
            # Local deterministic work may safely retry after a crashed lease; no external charge exists.
            job.submission_state = "intent"
            job.lease_until = now() + timedelta(seconds=settings().render_timeout_seconds + 180)
            g.status, g.updated_at = "generating", now()
            # Keep only immutable asset fields after the transaction closes.
            from types import SimpleNamespace

            assets = {
                key: SimpleNamespace(storage_key=a.storage_key, mime_type=a.mime_type)
                for key, a in assets.items()
            }
        data, thumbnail = await render(snapshot, assets, storage)
        with SessionLocal.begin() as db:
            g, job = lock_job(db, job_id, owner)
            if not g or g.status in TERMINAL:
                return
            for role, content, filename in [
                ("output_video", data, "template-render.mp4"),
                ("thumbnail", thumbnail, "template-render.webp"),
            ]:
                asset = store_asset(db, storage, g.user_id, role, content, filename)
                db.add(Output(generation_id=g.id, asset_id=asset.id))
            finish(db, g, "completed", actual=g.estimated)
            job.submission_state = "done"
            release(job)
    except Exception as exc:
        with SessionLocal.begin() as db:
            g, job = lock_job(db, job_id, owner)
            if not g or g.status in TERMINAL:
                return
            finish(
                db,
                g,
                "failed",
                error={
                    "code": "RENDER_FAILED",
                    "message": "Template rendering failed. Try again.",
                    "retryable": True,
                },
            )
            job.submission_state = "done"
            release(job)
        log.warning("template_render_failed", extra={"exception_type": type(exc).__name__})


async def process(job_id, owner):
    with SessionLocal.begin() as db:
        selected_model = db.scalar(
            select(Generation.selected_model)
            .join(Job, Job.generation_id == Generation.id)
            .where(Job.id == job_id)
        )
    if selected_model == "render_only":
        await process_render(job_id, owner)
        return
    storage = Storage()
    with SessionLocal.begin() as db:
        g, job = lock_job(db, job_id, owner)
        if not g:
            return
        if g.status in TERMINAL:
            job.submission_state = "done"
            release(job)
            return
        selected = next((m for m in registry() if m.id == g.selected_model), None)
        if not selected:
            # Configuration loss must not discard a possibly accepted remote operation.
            if job.submission_state in {"intent", "submitted"}:
                job.submission_state = "reconciliation"
                release(job)
                return
            finish(
                db,
                g,
                "failed",
                error={
                    "code": "GENERATION_UNAVAILABLE",
                    "message": "Generation is no longer configured.",
                    "retryable": False,
                },
            )
            job.submission_state = "done"
            release(job)
            return
        provider = selected.provider
        if job.submission_state == "intent" and not provider.supports_idempotency:
            job.submission_state = "reconciliation"
            release(job)
            return
        request = provider_input(g.snapshot, owned_inputs(db, g.user_id, g.snapshot["inputAssets"]), storage)
        remote_id = job.provider_job_id
        if not remote_id:
            job.submission_state = "intent"
            if g.snapshot.get("creativePlanning"):
                # Review evidence only: never persist credentials or signed reference URLs.
                g.snapshot = {**g.snapshot, "providerRequestMetadata": {
                    "provider": provider.key,
                    "model": getattr(provider, "model", None),
                    "duration": request.duration_seconds,
                    "aspectRatio": request.aspect_ratio,
                    "nativeAudio": getattr(provider, "requires_native_audio", False),
                    "imageReferences": len(request.reference_image_urls),
                    "videoReferences": len(request.reference_video_urls),
                    "submissionStartedAt": now().isoformat(),
                }}
        g.status = "generating"
        g.updated_at = now()
        generation_id = g.id
    try:
        if not remote_id:
            accepted = await provider.generate(request, idempotency_key=generation_id)
            remote_id = accepted.job_id
            with SessionLocal.begin() as db:
                g, job = lock_job(db, job_id, owner)
                if not g:
                    return
                job.provider_job_id = remote_id
                job.submission_state = "submitted"
                release(job, 1)
            return
        result = await provider.get_status(remote_id)
        if result.state not in {"completed", "failed", "cancelled"}:
            with SessionLocal.begin() as db:
                g, job = lock_job(db, job_id, owner)
                if g and g.status not in TERMINAL:
                    g.progress = result.progress
                    g.updated_at = now()
                    # Capped at 10s, not 30s: a finished render otherwise sits unnoticed
                    # for up to half a minute of the user's wait, and status calls are free.
                    release(job, min(10, 3 + job.attempts))
            return
        data = None
        if result.state == "completed":
            if result.simulated:
                data = await asyncio.to_thread(
                    simulation_fixture, request.duration_seconds, request.aspect_ratio
                )
            elif hasattr(provider, "download_output"):
                # OpenRouter may return its authenticated /content endpoint in
                # unsigned_urls. Let the adapter authenticate that request and
                # follow only the resulting public CDN redirect.
                data = await provider.download_output(remote_id)
            elif result.output_urls:
                data, _, _ = await download_public(result.output_urls[0], 500 * 1024 * 1024, "video/*")
            else:
                raise ProviderError("INVALID_PROVIDER_RESULT", "No playable output was returned.")
        if data is not None and getattr(provider, "requires_native_audio", False):
            from app.services.video_validation import validate_native_video

            if not validate_native_video(data, request.duration_seconds):
                data = None
                result = type(result)(
                    state="failed",
                    error=ProviderError(
                        "INVALID_VIDEO_OUTPUT",
                        "The video did not meet duration or native audio requirements.",
                    ),
                )
        with SessionLocal.begin() as db:
            g, job = lock_job(db, job_id, owner)
            if not g or g.status in TERMINAL:
                return
            if data is not None:
                asset = store_asset(
                    db,
                    storage,
                    g.user_id,
                    "output_video",
                    data,
                    "development-simulation.mp4" if result.simulated else "generated-video.mp4",
                )
                db.add(Output(generation_id=g.id, asset_id=asset.id))
                finish(db, g, "completed", actual=g.estimated)
            else:
                error = (
                    {
                        "code": result.error.code,
                        "message": result.error.message,
                        "retryable": result.error.retryable,
                    }
                    if result.error
                    else {
                        "code": "GENERATION_FAILED",
                        "message": "Generation did not complete.",
                        "retryable": False,
                    }
                )
                finish(
                    db,
                    g,
                    "failed" if result.state == "failed" else "cancelled",
                    error=error if result.state == "failed" else None,
                )
            job.submission_state = "done"
            release(job)
    except Exception as exc:
        with SessionLocal.begin() as db:
            g, job = lock_job(db, job_id, owner)
            if not g or g.status in TERMINAL:
                return
            if job.submission_state == "intent":
                # Even a process/socket error can occur after remote acceptance. Never blindly submit again.
                if isinstance(exc, ProviderError) and not exc.submission_unknown:
                    finish(
                        db,
                        g,
                        "failed",
                        error={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
                    )
                    job.submission_state = "done"
                else:
                    job.submission_state = "reconciliation"
            elif job.attempts >= 30:
                # Poll/download uncertainty is operational reconciliation, not proof that remote work failed.
                job.submission_state = "reconciliation"
            release(job, min(60, 2 ** min(job.attempts, 6)))
        log.warning(
            "job_attempt_incomplete",
            extra={"generation_id": generation_id, "exception_type": type(exc).__name__},
        )


async def run():
    owner = uid()
    from app.subtitles.jobs import run_forever as run_subtitle_jobs

    # Subtitle work has its own lease table and loops, so a long export never delays a video
    # poll, and transcriptions keep flowing while a 20-minute export renders.
    _transcribe_task = asyncio.create_task(run_subtitle_jobs(owner, kinds=("transcribe",)))
    _render_task = asyncio.create_task(run_subtitle_jobs(owner, kinds=("render",)))
    while True:
        with SessionLocal.begin() as db:
            job_id = claim(db, owner)
        if job_id:
            await process(job_id, owner)
        else:
            from app.services.notifications import wait_for_work

            await wait_for_work()


if __name__ == "__main__":
    asyncio.run(run())
