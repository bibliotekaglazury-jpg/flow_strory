"""Try-on projects: every generation is its own folder and its photos survive a reload."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Account, Asset, Base
from app.errors import DomainError
from app.schemas import LookProjectCreate, TryOn
from app.services import look_projects, try_on


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("IMAGE_PROVIDER", "mock")
    from app.config import settings

    settings.cache_clear()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for identifier, owner, role in [
            ("model", "alice", "person"),
            ("coat", "alice", "product"),
            ("hat", "alice", "product"),
            ("bob-model", "bob", "person"),
            ("bob-shoe", "bob", "product"),
        ]:
            session.add(
                Asset(
                    id=identifier,
                    user_id=owner,
                    role=role,
                    mime_type="image/png",
                    file_name=f"{identifier}.png",
                    size_bytes=1,
                    storage_key=f"{owner}/{identifier}",
                )
            )
        session.add(Account(user_id="alice", available=100, reserved=0))
        session.flush()
        yield session
    settings.cache_clear()


LOOK = {
    "productImageId": "coat",
    "personImageId": "model",
    "items": [{"assetId": "hat", "label": "hat"}],
}


def new_project(db, user="alice", look=LOOK):
    body = LookProjectCreate(inputAssets=look, scene="studio", aspectRatio="4:5")
    return look_projects.create(db, user, body)


def shot(project_id, key, **extra):
    return TryOn(
        inputAssets=LOOK,
        aspectRatio="4:5",
        idempotencyKey=key,
        projectId=project_id,
        **extra,
    )


async def test_photos_are_kept_in_their_project_in_shooting_order(db):
    project = new_project(db)
    front = await try_on.preview(db, "alice", shot(project["id"], "look-0001", angle="front"))
    await try_on.preview(
        db,
        "alice",
        shot(project["id"], "look-0002", angle="back", baseAssetId=front["asset"]["id"]),
    )

    saved = look_projects.detail(db, look_projects.owned(db, "alice", project["id"]))
    assert [p["label"] for p in saved["photos"]] == ["Front", "Back"]
    assert saved["photos"][0]["asset"]["id"] == front["asset"]["id"]
    # Reopening restores what was shot, not just the photos.
    assert saved["model"]["id"] == "model"
    assert [a["id"] for a in saved["products"]] == ["coat", "hat"]
    assert saved["aspectRatio"] == "4:5" and saved["scene"] == "studio"


async def test_every_generation_is_its_own_folder_newest_first(db):
    first = new_project(db)
    await try_on.preview(db, "alice", shot(first["id"], "look-0003"))
    second = new_project(db)
    await try_on.preview(db, "alice", shot(second["id"], "look-0004"))

    folders = look_projects.summaries(db, "alice")
    assert [f["id"] for f in folders] == [second["id"], first["id"]]
    assert all(f["photoCount"] == 1 and f["coverUrl"] for f in folders)


async def test_a_generation_that_produced_nothing_is_not_a_folder(db):
    new_project(db)
    assert look_projects.summaries(db, "alice") == []


async def test_another_users_project_is_refused_before_anything_is_paid_for(db, monkeypatch):
    bobs = new_project(
        db, user="bob", look={"productImageId": "bob-shoe", "personImageId": "bob-model"}
    )

    async def must_not_run(*args):
        raise AssertionError("the image provider was called for a foreign project")

    monkeypatch.setattr(
        try_on, "provider", lambda: type("P", (), {"generate": staticmethod(must_not_run)})()
    )
    with pytest.raises(DomainError) as exc:
        await try_on.preview(db, "alice", shot(bobs["id"], "look-0005"))
    assert exc.value.code == "LOOK_PROJECT_NOT_FOUND"
    assert look_projects.summaries(db, "alice") == []
    with pytest.raises(DomainError):
        look_projects.owned(db, "alice", bobs["id"])


def test_a_project_cannot_be_built_from_someone_elses_photos(db):
    with pytest.raises(DomainError) as exc:
        new_project(db, look={"productImageId": "bob-shoe", "personImageId": "model"})
    assert exc.value.code == "INVALID_ASSET"


async def test_deleting_a_project_removes_it_and_its_photos(db):
    from app.db import LookPhoto, LookProject
    from sqlalchemy import func, select

    project = new_project(db)
    await try_on.preview(db, "alice", shot(project["id"], "look-0006"))
    project_id = project["id"]

    look_projects.delete(db, "alice", project_id)

    assert db.scalar(select(func.count()).select_from(LookProject)) == 0
    assert db.scalar(select(func.count()).select_from(LookPhoto)) == 0
    with pytest.raises(DomainError):
        look_projects.owned(db, "alice", project_id)
    # The photo asset itself is a reusable library asset, not owned by the project.
    assert db.get(Asset, "model") is not None


def test_deleting_someone_elses_project_is_a_clean_404(db):
    bobs = new_project(
        db, user="bob", look={"productImageId": "bob-shoe", "personImageId": "bob-model"}
    )
    with pytest.raises(DomainError) as exc:
        look_projects.delete(db, "alice", bobs["id"])
    assert exc.value.code == "LOOK_PROJECT_NOT_FOUND"
    assert look_projects.owned(db, "bob", bobs["id"]).id == bobs["id"]


def test_deleting_an_unknown_project_is_a_clean_404(db):
    with pytest.raises(DomainError) as exc:
        look_projects.delete(db, "alice", "no-such-project")
    assert exc.value.code == "LOOK_PROJECT_NOT_FOUND"
