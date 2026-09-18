"""Model photos the try-on can offer again: only this user's, only uploaded in try-on."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Asset, Base
from app.services.assets import library


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    start = datetime(2026, 9, 13, tzinfo=UTC)
    with Session(engine) as session:
        for minute, (identifier, owner, role, source) in enumerate(
            [
                ("create-face", "alice", "person", None),
                ("old-face", "alice", "person", "try_on"),
                ("shirt", "alice", "product", "try_on"),
                ("new-face", "alice", "person", "try_on"),
                ("stranger-face", "bob", "person", "try_on"),
            ]
        ):
            session.add(
                Asset(
                    id=identifier,
                    user_id=owner,
                    role=role,
                    source=source,
                    mime_type="image/png",
                    file_name=f"{identifier}.png",
                    size_bytes=1,
                    storage_key=f"{owner}/{identifier}",
                    created_at=start + timedelta(minutes=minute),
                )
            )
        session.flush()
        yield session


def test_only_try_on_model_photos_of_this_user_come_back_newest_first(db):
    assert [a.id for a in library(db, "alice", "person", "try_on")] == ["new-face", "old-face"]


def test_photos_uploaded_on_the_create_screen_never_appear(db):
    assert "create-face" not in {a.id for a in library(db, "alice", "person", "try_on")}


def test_another_account_never_sees_them(db):
    assert [a.id for a in library(db, "bob", "person", "try_on")] == ["stranger-face"]
    assert library(db, "carol", "person", "try_on") == []


def test_the_product_role_is_a_separate_reusable_library_from_the_model_photos(db):
    assert [a.id for a in library(db, "alice", "product", "try_on")] == ["shirt"]
    assert "shirt" not in {a.id for a in library(db, "alice", "person", "try_on")}
