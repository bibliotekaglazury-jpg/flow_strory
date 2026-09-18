"""Subtitle Studio export: immutable snapshot render, storage keys, retry, restart recovery."""

import asyncio
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Asset, Base, SubtitleExport, SubtitleJob, SubtitleProject
from app.providers.base import ProviderError
from app.services.storage import Storage
from app.subtitles import jobs, service
from app.subtitles.schemas import (
    SubtitleCueIn,
    SubtitleExportCreate,
    SubtitleProjectCreate,
    SubtitleProjectPatch,
    SubtitleStyleIn,
)


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("STORAGE_MODE", "local")
    settings.cache_clear()
    value = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(value)
    with Session(value) as seed, seed.begin():
        seed.add(
            Asset(
                id="clip", user_id="alice", role="source_video", mime_type="video/mp4",
                file_name="clip.mp4", size_bytes=4, storage_key="alice/clip", duration_seconds=10.0,
            )
        )
    Storage().put("alice/clip", b"mp4!", "video/mp4")
    yield value
    settings.cache_clear()


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


def style():
    return SubtitleStyleIn(
        preset="impact", position="center", size="large", safeArea=True,
        textColor="#FFFFFF", highlightColor="#C9FF27",
    )


def exported(db, text="Hello world"):
    project = service.create(db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="16:9"), "k")
    project.status = "ready"
    cue = SubtitleCueIn(id="c1", startMs=0, endMs=1000, text=text, words=[])
    service.update(db, "alice", project.id, SubtitleProjectPatch(revision=0, aspectRatio="16:9", cues=[cue], style=style()))
    export = service.create_export(db, "alice", project.id, SubtitleExportCreate(revision=1), "ek")
    job = db.scalar(select(SubtitleJob).where(SubtitleJob.export_id == export.id))
    job.lease_owner, job.attempts = "worker", 1
    db.flush()
    return project, export, job


def fake_renderer(calls, progress_during=None):
    async def render(context, on_progress):
        calls.append(context)
        if progress_during is not None:
            progress_during(context)
        if on_progress:
            on_progress(40)
        return b"rendered-mp4", b"rendered-webp"

    return render


@pytest.mark.asyncio
async def test_completed_render_stores_assets_under_the_export_prefix(db, tmp_path):
    project, export, job = exported(db)
    calls, seen = [], []
    await jobs.run_render(db, job, renderer=fake_renderer(calls), on_progress=seen.append)

    assert export.status == "completed" and export.progress == 100 and export.error is None
    assert job.submission_state == "done"
    assert seen == [40]
    prefix = f"users/alice/subtitle-projects/{project.id}/exports/{export.id}/"
    output = db.get(Asset, export.output_asset_id)
    assert output.storage_key == prefix + "output.mp4"
    assert output.role == "output_video" and (output.width, output.height) == (1920, 1080)
    assert output.duration_seconds == pytest.approx(10.0)
    thumbnail = db.scalar(select(Asset).where(Asset.storage_key == prefix + "thumbnail.webp"))
    assert thumbnail and thumbnail.role == "thumbnail"
    assert (tmp_path / prefix / "output.mp4").read_bytes() == b"rendered-mp4"
    assert service.export_view(db, export)["outputAsset"]["id"] == output.id


@pytest.mark.asyncio
async def test_export_is_rendering_while_the_renderer_runs(db):
    _, export, job = exported(db)
    states = []
    await jobs.run_render(db, job, renderer=fake_renderer([], lambda _: states.append(export.status)))
    assert states == ["rendering"]


@pytest.mark.asyncio
async def test_render_uses_the_frozen_snapshot_not_later_edits(db):
    project, _, job = exported(db, text="Frozen words")
    project.cues = [{"id": "x", "startMs": 0, "endMs": 900, "text": "Edited later", "words": []}]
    project.style = {**project.style, "preset": "classic"}
    db.flush()
    calls = []
    await jobs.run_render(db, job, renderer=fake_renderer(calls))
    assert calls[0]["cues"][0]["text"] == "Frozen words"
    # The renderer learns the uploaded file's frame size so captions follow its orientation.
    assert "sourceWidth" in calls[0] and "sourceHeight" in calls[0]
    assert calls[0]["style"]["preset"] == "impact"


@pytest.mark.asyncio
async def test_retryable_failure_requeues_then_exhaustion_fails_the_export(db):
    _, export, job = exported(db)

    async def broken(context, on_progress):
        raise ProviderError("RENDER_FAILED", "boom", retryable=True)

    await jobs.run_render(db, job, renderer=broken)
    assert export.status == "queued" and export.progress is None
    assert job.submission_state == "pending" and job.lease_owner is None

    job.lease_owner, job.attempts = "worker", jobs.MAX_ATTEMPTS
    await jobs.run_render(db, job, renderer=broken)
    assert export.status == "failed"
    assert export.error == {"code": "RENDER_FAILED", "message": "boom", "retryable": True}
    assert job.submission_state == "done"
    assert export.output_asset_id is None


@pytest.mark.asyncio
async def test_restart_after_committed_output_completes_without_rendering_again(db):
    _, export, job = exported(db)
    export.output_asset_id, export.status = "clip", "rendering"
    db.flush()

    async def must_not_run(context, on_progress):
        raise AssertionError("renderer invoked twice")

    await jobs.run_render(db, job, renderer=must_not_run)
    assert export.status == "completed" and job.submission_state == "done"


@pytest.mark.asyncio
async def test_a_terminal_export_is_never_rendered(db):
    _, export, job = exported(db)
    export.status = "failed"
    db.flush()
    calls = []
    await jobs.run_render(db, job, renderer=fake_renderer(calls))
    assert calls == [] and job.submission_state == "done"


class FakeProcess:
    def __init__(self, lines, returncode):
        self._lines, self._code, self.returncode, self.pid = lines, returncode, None, 0
        self.stdout = self._stream()

    async def _stream(self):
        for line in self._lines:
            yield line

    async def wait(self):
        self.returncode = self._code
        return self._code


@pytest.mark.asyncio
async def test_renderer_receives_user_text_only_through_the_input_file(engine, monkeypatch):
    seen = {}

    async def exec_(*args, **kwargs):
        seen["args"] = args
        job_file = args[args.index("--input") + 1]
        seen["job"] = json.loads(open(job_file, encoding="utf-8").read())
        output = args[args.index("--output") + 1]
        open(output, "wb").write(b"mp4")
        open(output.replace(".mp4", ".webp"), "wb").write(b"webp")
        return FakeProcess([b'{"progress": 10}\n', b"Bundle compiled\n", b'{"progress": 100}\n'], 0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", exec_)
    hostile = 'Hi"; rm -rf / $(whoami) `id`'
    context = {
        "exportId": "e", "userId": "alice", "projectId": "p", "aspectRatio": "9:16", "durationMs": 10000,
        "cues": [{"id": "c", "startMs": 0, "endMs": 1000, "text": hostile, "words": []}],
        "style": {"preset": "modern", "position": "bottom", "size": "medium", "safeArea": True,
                  "textColor": "#FFFFFF", "highlightColor": "#C9FF27"},
        "sourceKey": "alice/clip", "sourceWidth": 720, "sourceHeight": 1280,
    }
    progress = []
    video, thumbnail = await jobs.render_export(context, progress.append)
    assert (video, thumbnail) == (b"mp4", b"webp")
    assert progress == [10, 100]
    assert all(hostile not in str(arg) for arg in seen["args"])
    assert "scripts/subtitles/render-subtitle.ts" in seen["args"]
    assert seen["job"]["props"]["cues"][0]["text"] == hostile
    assert seen["job"]["props"]["preset"] == "modern"
    assert (seen["job"]["props"]["sourceWidth"], seen["job"]["props"]["sourceHeight"]) == (720, 1280)


@pytest.mark.asyncio
async def test_a_failed_renderer_process_is_a_retryable_render_error(engine, monkeypatch):
    async def exec_(*args, **kwargs):
        return FakeProcess([b"boom\n"], 1)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", exec_)
    context = {
        "exportId": "e", "userId": "alice", "projectId": "p", "aspectRatio": "9:16", "durationMs": 10000,
        "cues": [], "style": {}, "sourceKey": "alice/clip",
    }
    with pytest.raises(ProviderError) as exc:
        await jobs.render_export(context)
    assert exc.value.code == "RENDER_FAILED" and exc.value.retryable is True


@pytest.mark.asyncio
async def test_production_loop_runs_transcribe_then_render_in_separate_transactions(engine, monkeypatch):
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(jobs, "SessionLocal", factory)

    async def audio(db, asset_id, **kwargs):
        return b"audio", "audio/aac"

    monkeypatch.setattr(jobs, "_source_audio", audio)
    monkeypatch.setattr(jobs, "render_export", fake_renderer([]))
    from app.subtitles.providers import MockTranscriptionProvider

    with factory.begin() as db:
        project = service.create(db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16"), "k")
        project_id = project.id
    provider = MockTranscriptionProvider()
    assert await jobs.run_next("worker", provider) is True
    with factory.begin() as db:
        assert db.get(SubtitleProject, project_id).status == "ready"
        export_id = service.create_export(db, "alice", project_id, SubtitleExportCreate(revision=0), "ek").id
    assert await jobs.run_next("worker", provider) is True
    with factory.begin() as db:
        export = db.get(SubtitleExport, export_id)
        assert export.status == "completed" and export.output_asset_id
    assert await jobs.run_next("worker", provider) is False


@pytest.mark.asyncio
async def test_a_host_without_node_fails_the_export_clearly_instead_of_retrying(engine, monkeypatch):
    async def missing(*args, **kwargs):
        raise FileNotFoundError("node")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", missing)
    context = {
        "exportId": "e", "userId": "alice", "projectId": "p", "aspectRatio": "9:16", "durationMs": 10000,
        "cues": [], "style": {}, "sourceKey": "alice/clip",
    }
    with pytest.raises(ProviderError) as exc:
        await jobs.render_export(context)
    assert exc.value.code == "RENDER_UNAVAILABLE" and exc.value.retryable is False


@pytest.mark.asyncio
async def test_an_unexpected_transcription_crash_uses_the_bounded_retry_path(db, monkeypatch):
    project = service.create(db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16"), "t")

    async def crash(db, asset_id, **kwargs):
        raise KeyError("storage moved")

    monkeypatch.setattr(jobs, "_source_audio", crash)
    job = db.scalar(select(SubtitleJob).where(SubtitleJob.project_id == project.id))
    job.lease_owner, job.attempts = "worker", jobs.MAX_ATTEMPTS
    await jobs.run_transcribe(db, job, provider=None)
    assert project.status == "failed"
    assert project.error["code"] == "TRANSCRIPTION_FAILED"
    assert job.submission_state == "done"



def test_export_time_budget_grows_with_video_length(engine):
    # A fixed 10-minute budget would kill every export of a long video half way.
    assert jobs.render_timeout(10_000) == settings().render_timeout_seconds
    assert jobs.render_timeout(20 * 60 * 1000) == 300 + 20 * 60 * 6
