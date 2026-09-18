"""Durable subtitle_jobs leasing: transcribe and render.

Deliberately simpler than the video generation_jobs state machine: transcription and
render are each one attempt against a provider/subprocess per lease, not a submit-then-
poll cycle against a third-party async job id, so there is no submission_state beyond
"pending" (runnable) and "done" (terminal, success or failure already recorded on the
owning project/export row).
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path

from sqlalchemy import or_, select

from app.config import settings
from app.db import Asset, SessionLocal, SubtitleExport, SubtitleJob, SubtitleProject, now
from app.providers.base import ProviderError
from app.services.assets import store_rendered_asset
from app.services.product import download_public
from app.services.storage import Storage
from app.subtitles.providers import transcription_provider

log = logging.getLogger(__name__)

LEASE_SECONDS = 180
MAX_ATTEMPTS = 5
# Long videos are transcribed in parts: one provider answer for 20 minutes of speech would
# overrun the model's output limit and the request timeout. Timing is shifted back onto the
# video's own timeline; nothing is estimated.
CHUNK_MS = 5 * 60 * 1000
EXPORT_TERMINAL = {"completed", "failed"}
SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080)}


def claim(db, owner, kinds=None):
    """Lease one runnable job; row lock keeps concurrent workers from double-claiming."""
    query = select(SubtitleJob).where(
        SubtitleJob.submission_state == "pending",
        SubtitleJob.next_run_at <= now(),
        or_(SubtitleJob.lease_until.is_(None), SubtitleJob.lease_until < now()),
    )
    if kinds:
        query = query.where(SubtitleJob.kind.in_(kinds))
    job = db.scalar(
        query
        .order_by(SubtitleJob.next_run_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job:
        job.lease_owner = owner
        job.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
        job.attempts += 1
        db.flush()
    return job


def release(db, job, seconds):
    """Free the lease for a later retry, backed off by seconds."""
    job.lease_owner = None
    job.lease_until = None
    job.next_run_at = now() + timedelta(seconds=seconds)
    db.flush()


def backoff(attempts):
    return min(60, 2 ** min(attempts, 6))


def render_timeout(duration_ms):
    """A 20-minute export cannot fit a fixed 10-minute budget; allow ~6s of render per video
    second on top of bundling, never less than the configured floor."""
    return max(settings().render_timeout_seconds, 300 + int((duration_ms or 0) / 1000 * 6))


def _error(exc):
    return {"code": exc.code, "message": exc.message, "retryable": exc.retryable}


def _extract_audio(video_path, start_ms=0, length_ms=None):
    """MP3 mono at 64kbps: every transcription API accepts it (raw ADTS AAC is not a Whisper
    upload format), and a 5-minute part is about 2.4MB."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as out:
        try:
            subprocess.run(
                [
                    settings().ffmpeg_path,
                    "-y",
                    "-nostdin",
                    "-ss",
                    f"{start_ms / 1000:.3f}",
                    "-i",
                    str(video_path),
                    *(["-t", f"{length_ms / 1000:.3f}"] if length_ms else []),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "64k",
                    "-f",
                    "mp3",
                    out.name,
                ],
                capture_output=True,
                timeout=300,
                check=True,
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
            raise ProviderError(
                "AUDIO_EXTRACTION_FAILED", "The video's audio could not be read.", retryable=True
            ) from exc
        out.flush()
        return Path(out.name).read_bytes(), "audio/mpeg"


async def _source_audio(db, asset_id, start_ms=0, length_ms=None, cache=None):
    """Audio for one part of the source video. Object storage is downloaded once per job and
    reused for every part through cache, not once per part."""
    asset = db.get(Asset, asset_id)
    storage = Storage()
    if not storage.s3:
        path = storage.path(asset.storage_key)
    else:
        cache = cache if cache is not None else {}
        path = cache.get("path")
        if not path:
            video, _, _ = await download_public(
                storage.url(asset.storage_key)[0], 500 * 1024 * 1024, "video/*"
            )
            folder = cache.setdefault("dir", tempfile.TemporaryDirectory(prefix="ugc-transcribe-"))
            path = Path(folder.name) / "source.mp4"
            path.write_bytes(video)
            cache["path"] = path
    return await asyncio.to_thread(_extract_audio, path, start_ms, length_ms)


async def _transcribe_parts(db, project, provider):
    duration = project.duration_ms or 0
    offsets = list(range(0, duration, CHUNK_MS)) if duration else [0]
    cues, language, cache = [], None, {}
    try:
        for offset in offsets:
            length = min(CHUNK_MS, duration - offset) if duration else None
            audio, mime = await _source_audio(
                db, project.source_asset_id, start_ms=offset, length_ms=length, cache=cache
            )
            part = await provider.transcribe(audio, mime)
            language = language or part.language
            for cue in part.cues:
                shifted = {
                    **cue,
                    "startMs": cue["startMs"] + offset,
                    "endMs": cue["endMs"] + offset,
                    "words": [
                        {**word, "startMs": word["startMs"] + offset, "endMs": word["endMs"] + offset}
                        for word in cue["words"]
                    ],
                }
                if cues and shifted["startMs"] < cues[-1]["endMs"]:
                    raise ProviderError(
                        "TRANSCRIPTION_INVALID",
                        "Caption timing overlapped between two parts of the video.",
                        retryable=True,
                    )
                cues.append(shifted)
    finally:
        if "dir" in cache:
            cache["dir"].cleanup()
    return cues, language


async def run_transcribe(db, job, provider):
    """One lease attempt: extract audio, ask the provider, normalize into the project.

    A project already moved out of "transcribing" (e.g. by a restart racing a prior
    attempt that actually finished) is left untouched — the job just closes.
    """
    project = db.get(SubtitleProject, job.project_id)
    if not project or project.status != "transcribing":
        job.submission_state = "done"
        db.flush()
        return
    try:
        try:
            cues, language = await _transcribe_parts(db, project, provider)
        except ProviderError:
            raise
        except Exception as exc:
            # Anything unexpected still goes through the bounded retry path, so a project can
            # never sit in "transcribing" forever behind a job that keeps crashing.
            log.exception("subtitle_transcribe_unexpected job=%s", job.id)
            raise ProviderError(
                "TRANSCRIPTION_FAILED", "The transcription could not be completed.", retryable=True
            ) from exc
    except ProviderError as exc:
        if exc.retryable and job.attempts < MAX_ATTEMPTS:
            release(db, job, backoff(job.attempts))
            log.warning(
                "subtitle_transcribe_retry job=%s attempt=%s code=%s", job.id, job.attempts, exc.code
            )
            return
        project.status = "failed"
        project.error = _error(exc)
        project.updated_at = now()
        job.submission_state = "done"
        db.flush()
        log.warning("subtitle_transcribe_failed job=%s code=%s", job.id, exc.code)
        return
    project.cues = cues
    project.language = language
    project.status = "ready"
    project.updated_at = now()
    job.submission_state = "done"
    db.flush()


def begin_render(db, job):
    """Mark the export rendering and return its frozen snapshot, or None when there is
    nothing to render (already terminal, or a restart after the output was committed)."""
    export = db.get(SubtitleExport, job.export_id)
    if not export or export.status in EXPORT_TERMINAL:
        job.submission_state = "done"
        db.flush()
        return None
    if export.output_asset_id:
        # The asset transaction committed before a crash; the render is already stored.
        export.status = "completed"
        export.progress = 100
        export.updated_at = now()
        job.submission_state = "done"
        db.flush()
        return None
    project = db.get(SubtitleProject, export.project_id)
    source = db.get(Asset, project.source_asset_id) if project else None
    if not source:
        export.status = "failed"
        export.error = {
            "code": "SOURCE_UNAVAILABLE",
            "message": "The source video is no longer available.",
            "retryable": False,
        }
        export.updated_at = now()
        job.submission_state = "done"
        db.flush()
        return None
    export.status = "rendering"
    export.progress = 0
    export.updated_at = now()
    # A render can run up to the renderer timeout; the lease must outlive it.
    job.lease_until = now() + timedelta(seconds=render_timeout(project.duration_ms) + 180)
    db.flush()
    return {
        "exportId": export.id,
        "userId": export.user_id,
        "projectId": export.project_id,
        "aspectRatio": export.aspect_ratio,
        "durationMs": project.duration_ms,
        "cues": export.cues,
        "style": export.style,
        "sourceKey": source.storage_key,
        # The caption layout follows the uploaded file's orientation, same as the preview.
        "sourceWidth": source.width,
        "sourceHeight": source.height,
    }


def complete_render(db, job, context, video, thumbnail):
    export = db.get(SubtitleExport, context["exportId"])
    if not export or export.status in EXPORT_TERMINAL:
        job.submission_state = "done"
        db.flush()
        return
    storage = Storage()
    base = (
        f"users/{context['userId']}/subtitle-projects/{context['projectId']}"
        f"/exports/{context['exportId']}/"
    )
    width, height = SIZES[context["aspectRatio"]]
    output = store_rendered_asset(
        db, storage, context["userId"], "output_video", video, "subtitles.mp4",
        base + "output.mp4", "video/mp4", width, height, context["durationMs"] / 1000,
    )
    store_rendered_asset(
        db, storage, context["userId"], "thumbnail", thumbnail, "subtitles.webp",
        base + "thumbnail.webp", "image/webp", width, height, None,
    )
    # Terminal state lands in the same transaction as the asset rows, never before.
    export.output_asset_id = output.id
    export.status = "completed"
    export.progress = 100
    export.error = None
    export.updated_at = now()
    job.submission_state = "done"
    db.flush()


def fail_render(db, job, exc):
    export = db.get(SubtitleExport, job.export_id)
    if not export or export.status in EXPORT_TERMINAL:
        job.submission_state = "done"
        db.flush()
        return
    if exc.retryable and job.attempts < MAX_ATTEMPTS:
        export.status = "queued"
        export.progress = None
        export.updated_at = now()
        release(db, job, backoff(job.attempts))
        log.warning("subtitle_render_retry job=%s attempt=%s code=%s", job.id, job.attempts, exc.code)
        return
    export.status = "failed"
    export.error = _error(exc)
    export.updated_at = now()
    job.submission_state = "done"
    db.flush()
    log.warning("subtitle_render_failed job=%s code=%s", job.id, exc.code)


async def render_export(context, on_progress=None):
    """Run the registered Remotion composition in a subprocess.

    Cue text reaches the renderer only through a JSON file; the argument vector is fixed
    strings and temp paths, so nothing a user typed can become part of a command.
    """
    from app.services.templates import ROOT

    cfg = settings()
    storage = Storage()
    with tempfile.TemporaryDirectory(prefix="ugc-subtitles-") as directory:
        folder = Path(directory)
        source = folder / "source.mp4"
        if storage.s3:
            await asyncio.to_thread(
                storage.s3.download_file, storage.cfg.s3_bucket, context["sourceKey"], str(source)
            )
        else:
            source.write_bytes(storage.path(context["sourceKey"]).read_bytes())
        job_file, output = folder / "job.json", folder / "output.mp4"
        job_file.write_text(
            json.dumps(
                {
                    "aspectRatio": context["aspectRatio"],
                    "durationMs": context["durationMs"],
                    "sourcePath": str(source),
                    "props": {
                        "cues": context["cues"],
                        **context["style"],
                        "sourceWidth": context.get("sourceWidth"),
                        "sourceHeight": context.get("sourceHeight"),
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        try:
            process = await asyncio.create_subprocess_exec(
                cfg.render_node_path,
                "--import",
                "tsx",
                "scripts/subtitles/render-subtitle.ts",
                "--input",
                str(job_file),
                "--output",
                str(output),
                cwd=ROOT,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            # No Node runtime on this host: fail the export clearly instead of retrying forever.
            raise ProviderError(
                "RENDER_UNAVAILABLE", "Video export is not available on this server.", retryable=False
            ) from None

        async def pump():
            async for line in process.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if on_progress and isinstance(event, dict) and isinstance(event.get("progress"), int):
                    on_progress(max(0, min(100, event["progress"])))
            await process.wait()

        try:
            await asyncio.wait_for(pump(), timeout=render_timeout(context["durationMs"]))
        except TimeoutError:
            raise ProviderError("RENDER_TIMEOUT", "The export took too long.", retryable=True) from None
        finally:
            if process.returncode is None:
                os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
        thumbnail = output.with_suffix(".webp")
        if process.returncode != 0 or not output.exists() or not thumbnail.exists():
            raise ProviderError("RENDER_FAILED", "The export could not be rendered.", retryable=True)
        return output.read_bytes(), thumbnail.read_bytes()


async def run_render(db, job, renderer=None, on_progress=None):
    """Single-session composition of the render phases (used by tests and poll_once)."""
    context = begin_render(db, job)
    if not context:
        return
    try:
        video, thumbnail = await (renderer or render_export)(context, on_progress)
    except ProviderError as exc:
        fail_render(db, job, exc)
        return
    complete_render(db, job, context, video, thumbnail)


async def poll_once(db, owner, provider):
    """Claim and run at most one job; returns False when nothing was runnable."""
    job = claim(db, owner)
    if not job:
        return False
    if job.kind == "transcribe":
        await run_transcribe(db, job, provider)
    elif job.kind == "render":
        await run_render(db, job)
    return True


def _leased(db, job_id, owner):
    """Reload a job only while this worker still owns its lease."""
    return db.scalar(
        select(SubtitleJob)
        .where(SubtitleJob.id == job_id, SubtitleJob.lease_owner == owner)
        .with_for_update()
    )


def _progress_writer(export_id):
    last = {"value": -1}

    def write(percent):
        # Real renderer events only, and only in 5% steps so polling sees movement without
        # a database write per frame.
        if percent != 100 and percent - last["value"] < 5:
            return
        last["value"] = percent
        with SessionLocal.begin() as db:
            export = db.get(SubtitleExport, export_id)
            if export and export.status == "rendering":
                export.progress = percent
                export.updated_at = now()

    return write


async def run_next(owner, provider, kinds=None):
    """Production path: short transactions around each phase, so a long render never holds
    a row lock and progress writes are visible to polling clients while it runs."""
    with SessionLocal.begin() as db:
        job = claim(db, owner, kinds)
        if not job:
            return False
        job_id, kind = job.id, job.kind
    if kind == "transcribe":
        with SessionLocal.begin() as db:
            job = _leased(db, job_id, owner)
            if job:
                await run_transcribe(db, job, provider)
        return True
    if kind != "render":
        return True
    with SessionLocal.begin() as db:
        job = _leased(db, job_id, owner)
        context = begin_render(db, job) if job else None
    if not context:
        return True
    try:
        try:
            video, thumbnail = await render_export(context, _progress_writer(context["exportId"]))
        except ProviderError:
            raise
        except Exception as exc:
            log.exception("subtitle_render_unexpected job=%s", job_id)
            raise ProviderError("RENDER_FAILED", "The export could not be rendered.", retryable=True) from exc
    except ProviderError as exc:
        with SessionLocal.begin() as db:
            job = _leased(db, job_id, owner)
            if job:
                fail_render(db, job, exc)
        return True
    with SessionLocal.begin() as db:
        job = _leased(db, job_id, owner)
        if job:
            complete_render(db, job, context, video, thumbnail)
    return True


async def run_forever(owner, provider=None, idle_seconds=2, kinds=None):
    provider = provider or transcription_provider(settings())
    while True:
        try:
            ran = await run_next(owner, provider, kinds)
        except Exception:
            log.exception("subtitle_job_loop_error")
            ran = False
        if not ran:
            await asyncio.sleep(idle_seconds)
