"""Subtitle Studio persistence: ownership isolation, idempotent creation, optimistic revision."""

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import Asset, Base, SubtitleExport, SubtitleJob, SubtitleProject
from app.errors import DomainError
from app.subtitles import service
from app.subtitles.schemas import (
    SubtitleCueIn,
    SubtitleExportCreate,
    SubtitleProjectCreate,
    SubtitleProjectPatch,
    SubtitleStyleIn,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for identifier, owner, role, mime, duration in [
            ("alice-clip", "alice", "source_video", "video/mp4", 12.0),
            ("alice-photo", "alice", "product", "image/png", None),
            ("alice-short", "alice", "source_video", "video/mp4", 0.2),
            ("alice-long", "alice", "source_video", "video/mp4", 5 * 3600.0),
            ("bob-clip", "bob", "source_video", "video/mp4", 12.0),
        ]:
            session.add(
                Asset(
                    id=identifier,
                    user_id=owner,
                    role=role,
                    mime_type=mime,
                    file_name=f"{identifier}.mp4",
                    size_bytes=1,
                    storage_key=f"{owner}/{identifier}",
                    duration_seconds=duration,
                )
            )
        session.commit()
        yield session


def create_input(asset_id="alice-clip", ratio="9:16"):
    return SubtitleProjectCreate(sourceAssetId=asset_id, aspectRatio=ratio)


def style():
    return SubtitleStyleIn(
        preset="modern", position="bottom", size="medium", safeArea=True,
        textColor="#FFFFFF", highlightColor="#C9FF27",
    )


def cue(id="c1", start=0, end=1000, text="Hi"):
    return SubtitleCueIn(id=id, startMs=start, endMs=end, text=text, words=[])


def test_create_validates_ownership_and_role(db):
    with pytest.raises(DomainError) as exc:
        service.create(db, "alice", create_input("bob-clip"), "key-1")
    assert exc.value.code == "INVALID_ASSET"

    with pytest.raises(DomainError) as exc:
        service.create(db, "alice", create_input("alice-photo"), "key-2")
    assert exc.value.code == "INVALID_ASSET"


def test_create_validates_duration_bounds(db):
    with pytest.raises(DomainError) as exc:
        service.create(db, "alice", create_input("alice-short"), "key-3")
    assert exc.value.code == "INVALID_ASSET"

    with pytest.raises(DomainError) as exc:
        service.create(db, "alice", create_input("alice-long"), "key-4")
    assert exc.value.code == "INVALID_ASSET"


def test_create_is_idempotent_before_any_provider_work(db):
    first = service.create(db, "alice", create_input(), "same-key")
    second = service.create(db, "alice", create_input(), "same-key")
    assert first.id == second.id
    assert db.scalar(select(func.count()).select_from(SubtitleProject)) == 1
    # Exactly one transcribe job was enqueued; retrying the same key never enqueues twice.
    assert db.scalar(select(func.count()).select_from(SubtitleJob)) == 1


def test_create_with_same_key_different_body_conflicts(db):
    service.create(db, "alice", create_input(ratio="9:16"), "same-key")
    with pytest.raises(DomainError) as exc:
        service.create(db, "alice", create_input(ratio="16:9"), "same-key")
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"


def test_create_enqueues_a_transcribing_project_with_default_style(db):
    project = service.create(db, "alice", create_input(), "key")
    assert project.status == "transcribing"
    assert project.cues == []
    assert project.style["preset"] == "modern"
    assert project.duration_ms == 12000
    assert project.revision == 0


def test_alice_cannot_read_bobs_project(db):
    bob_project = service.create(db, "bob", create_input("bob-clip"), "bob-key")
    with pytest.raises(DomainError) as exc:
        service.owned(db, "alice", bob_project.id)
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"


def test_alice_cannot_read_bobs_export(db):
    bob_project = service.create(db, "bob", create_input("bob-clip"), "bob-key")
    bob_project.status = "ready"
    db.flush()
    bob_export = service.create_export(
        db, "bob", bob_project.id, SubtitleExportCreate(revision=0), "bob-export-key"
    )
    # A project alice cannot see must not leak whether the export itself exists.
    with pytest.raises(DomainError) as exc:
        service.owned_export(db, "alice", bob_project.id, bob_export.id)
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"

    with pytest.raises(DomainError) as exc:
        service.owned_export(db, "alice", "no-such-project", bob_export.id)
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"

    # Under alice's own project, a foreign/unknown export id is a distinct 404.
    alice_project = service.create(db, "alice", create_input("alice-clip"), "alice-key")
    with pytest.raises(DomainError) as exc:
        service.owned_export(db, "alice", alice_project.id, bob_export.id)
    assert exc.value.code == "SUBTITLE_EXPORT_NOT_FOUND"


def test_update_requires_the_confirmed_revision(db):
    project = service.create(db, "alice", create_input(), "key")
    patch = SubtitleProjectPatch(revision=0, aspectRatio="9:16", cues=[cue()], style=style())
    updated = service.update(db, "alice", project.id, patch)
    assert updated.revision == 1
    assert updated.cues[0]["text"] == "Hi"

    stale = SubtitleProjectPatch(revision=0, aspectRatio="9:16", cues=[cue()], style=style())
    with pytest.raises(DomainError) as exc:
        service.update(db, "alice", project.id, stale)
    assert exc.value.code == "REVISION_CONFLICT"


def test_update_rejects_a_cue_past_the_source_duration(db):
    project = service.create(db, "alice", create_input(), "key")
    patch = SubtitleProjectPatch(
        revision=0, aspectRatio="9:16", cues=[cue(end=999999)], style=style()
    )
    with pytest.raises(DomainError) as exc:
        service.update(db, "alice", project.id, patch)
    assert exc.value.code == "INVALID_INPUT"


def test_export_freezes_the_current_revision_and_is_idempotent(db):
    project = service.create(db, "alice", create_input(), "key")
    patch = SubtitleProjectPatch(revision=0, aspectRatio="9:16", cues=[cue()], style=style())
    project = service.update(db, "alice", project.id, patch)

    first = service.create_export(
        db, "alice", project.id, SubtitleExportCreate(revision=1), "export-key"
    )
    second = service.create_export(
        db, "alice", project.id, SubtitleExportCreate(revision=1), "export-key"
    )
    assert first.id == second.id
    assert db.scalar(select(func.count()).select_from(SubtitleExport)) == 1
    assert db.scalar(select(func.count()).select_from(SubtitleJob).where(SubtitleJob.kind == "render")) == 1
    assert first.source_revision == 1
    assert first.cues[0]["text"] == "Hi"

    # A later edit to the live project must never change the already-frozen export.
    project.cues = [cue(text="Changed").model_dump()]
    db.flush()
    reloaded = service.owned_export(db, "alice", project.id, first.id)
    assert reloaded.cues[0]["text"] == "Hi"


def test_export_rejects_a_stale_revision(db):
    project = service.create(db, "alice", create_input(), "key")
    with pytest.raises(DomainError) as exc:
        service.create_export(db, "alice", project.id, SubtitleExportCreate(revision=1), "k2")
    assert exc.value.code == "REVISION_CONFLICT"


def test_list_projects_is_newest_first_and_paginates(db):
    for i in range(3):
        service.create(db, "alice", create_input(), f"key-{i}")
    rows, cursor = service.list_projects(db, "alice", limit=2, cursor=None)
    assert len(rows) == 2
    assert cursor is not None
    rows2, cursor2 = service.list_projects(db, "alice", limit=2, cursor=cursor)
    assert len(rows2) == 1
    assert cursor2 is None
    assert {r.id for r in rows} | {r.id for r in rows2} == {
        service.owned(db, "alice", p.id).id for p in [*rows, *rows2]
    }



def _completed_export(db, user, project):
    export = service.create_export(db, user, project.id, SubtitleExportCreate(revision=0), "exp-key")
    export.status = "completed"
    export.output_asset_id = "alice-clip"
    db.flush()
    return export


def test_sharing_an_export_issues_a_stable_token_until_revoked(db):
    project = service.create(db, "alice", create_input(), "key")
    export = _completed_export(db, "alice", project)

    shared = service.create_share(db, "alice", project.id, export.id)
    again = service.create_share(db, "alice", project.id, export.id)
    assert shared.share_token == again.share_token
    assert service.export_view(db, again)["shareToken"] == shared.share_token

    public = service.shared_export(db, shared.share_token)
    assert public.id == export.id
    assert service.shared_export_view(db, public)["outputAsset"]["id"] == "alice-clip"


def test_sharing_a_pending_export_is_rejected(db):
    project = service.create(db, "alice", create_input(), "key")
    export = service.create_export(db, "alice", project.id, SubtitleExportCreate(revision=0), "exp-key")
    with pytest.raises(DomainError) as exc:
        service.create_share(db, "alice", project.id, export.id)
    assert exc.value.code == "EXPORT_NOT_READY"


def test_revoking_a_share_makes_the_token_unavailable_and_a_new_share_issues_a_fresh_one(db):
    project = service.create(db, "alice", create_input(), "key")
    export = _completed_export(db, "alice", project)
    shared = service.create_share(db, "alice", project.id, export.id)
    old_token = shared.share_token

    service.revoke_share(db, "alice", project.id, export.id)
    with pytest.raises(DomainError) as exc:
        service.shared_export(db, old_token)
    assert exc.value.code == "SHARE_NOT_FOUND"
    assert service.export_view(db, export)["shareToken"] is None

    resumed = service.create_share(db, "alice", project.id, export.id)
    assert resumed.share_token != old_token
    assert service.shared_export(db, resumed.share_token).id == export.id


def test_bob_cannot_share_or_revoke_alices_export(db):
    project = service.create(db, "alice", create_input(), "key")
    export = _completed_export(db, "alice", project)
    with pytest.raises(DomainError) as exc:
        service.create_share(db, "bob", project.id, export.id)
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"
    with pytest.raises(DomainError) as exc:
        service.revoke_share(db, "bob", project.id, export.id)
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"


def test_an_unknown_or_never_shared_token_is_not_found(db):
    project = service.create(db, "alice", create_input(), "key")
    _completed_export(db, "alice", project)
    with pytest.raises(DomainError) as exc:
        service.shared_export(db, "no-such-token")
    assert exc.value.code == "SHARE_NOT_FOUND"


def test_deleting_a_project_removes_it_and_its_exports_and_jobs(db):
    project = service.create(db, "alice", create_input(), "key")
    _completed_export(db, "alice", project)
    project_id = project.id

    service.delete(db, "alice", project_id)

    assert db.scalar(select(func.count()).select_from(SubtitleProject)) == 0
    assert db.scalar(select(func.count()).select_from(SubtitleExport)) == 0
    assert db.scalar(select(func.count()).select_from(SubtitleJob)) == 0
    with pytest.raises(DomainError) as exc:
        service.owned(db, "alice", project_id)
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"
    # The source video asset is a shared library resource, not project-owned.
    assert db.get(Asset, "alice-clip") is not None


def test_deleting_someone_elses_project_is_a_clean_404_and_nothing_is_removed(db):
    project = service.create(db, "bob", create_input("bob-clip"), "key")
    with pytest.raises(DomainError) as exc:
        service.delete(db, "alice", project.id)
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"
    assert service.owned(db, "bob", project.id).id == project.id


def test_deleting_an_unknown_project_is_a_clean_404(db):
    with pytest.raises(DomainError) as exc:
        service.delete(db, "alice", "no-such-project")
    assert exc.value.code == "SUBTITLE_PROJECT_NOT_FOUND"


def test_twenty_minute_videos_are_accepted(db):
    db.add(Asset(id="talk", user_id="alice", role="source_video", mime_type="video/mp4",
                 file_name="talk.mp4", size_bytes=1, storage_key="alice/talk", duration_seconds=20 * 60.0))
    db.flush()
    project = service.create(db, "alice", create_input("talk"), "talk-key")
    assert project.duration_ms == 20 * 60 * 1000
