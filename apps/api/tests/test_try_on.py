"""A look preview answers in one request: no quote, no job, no polling."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Account, Asset, Base, Ledger
from app.errors import DomainError
from app.prompts.tryon import ANGLES, compose
from app.providers.base import ProviderError
from app.schemas import TryOn
from app.services import try_on


def png():
    from io import BytesIO

    from PIL import Image

    data = BytesIO()
    Image.new("RGB", (8, 8), "white").save(data, format="PNG")
    return data.getvalue()


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
            ("trousers", "alice", "product"),
            ("stranger", "bob", "product"),
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


def request(**overrides):
    body = {
        "inputAssets": {
            "productImageId": "coat",
            "personImageId": "model",
            "items": [{"assetId": "trousers", "label": "trousers"}],
        },
        "aspectRatio": "9:16",
        "idempotencyKey": "preview-0001",
    }
    return TryOn(**{**body, **overrides})


async def test_a_preview_returns_a_stored_image_in_the_same_request(db):
    result = await try_on.preview(db, "alice", request())

    assert result["asset"]["kind"] == "image"
    assert result["asset"]["role"] == "tryon_photo"
    stored = db.scalar(select(Asset).where(Asset.id == result["asset"]["id"]))
    assert stored.user_id == "alice" and stored.mime_type == "image/png"


async def test_every_piece_of_the_look_reaches_the_model(db, monkeypatch):
    seen = {}

    async def capture(image_urls, prompt, aspect_ratio):
        seen["urls"], seen["prompt"] = image_urls, prompt
        return png()

    monkeypatch.setattr(try_on, "provider", lambda: type("P", (), {"generate": staticmethod(capture)})())
    await try_on.preview(db, "alice", request())

    # Person first, then both garments: the instruction block depends on that order.
    assert len(seen["urls"]) == 3
    assert "alice/model" in seen["urls"][0]
    assert all(f"alice/{piece}/" in seen["urls"][i + 1] for i, piece in enumerate(("coat", "trousers")))
    # Only supplied items may change; the person's own clothes and bag stay as photographed.
    assert "Change only what is supplied" in seen["prompt"]
    assert "never swap trousers for a dress" in seen["prompt"]
    assert "one complete outfit" not in seen["prompt"]


async def test_a_preview_without_a_model_photo_is_refused(db):
    with pytest.raises(DomainError) as exc:
        await try_on.preview(db, "alice", request(inputAssets={"productImageId": "coat"}))
    assert exc.value.code == "PREVIEW_INPUT_MISSING"


async def test_someone_elses_photo_cannot_be_used(db):
    with pytest.raises(DomainError) as exc:
        await try_on.preview(
            db,
            "alice",
            request(inputAssets={"personImageId": "model", "productImageId": "stranger"}),
        )
    assert exc.value.code == "INVALID_ASSET"


async def test_credits_are_charged_once_per_key_and_never_on_failure(db, monkeypatch):
    monkeypatch.setenv("IMAGE_CREDITS_PER_GENERATION", "4")
    from app.config import settings

    settings.cache_clear()

    await try_on.preview(db, "alice", request())
    await try_on.preview(db, "alice", request())
    assert db.scalar(select(Account).where(Account.user_id == "alice")).available == 96
    assert len(list(db.scalars(select(Ledger).where(Ledger.kind == "look_preview")))) == 1

    async def fail(*args):
        raise ProviderError("IMAGE_SERVICE_ERROR", "The preview could not be created.")

    monkeypatch.setattr(try_on, "provider", lambda: type("P", (), {"generate": staticmethod(fail)})())
    with pytest.raises(ProviderError):
        await try_on.preview(db, "alice", request(idempotencyKey="preview-0002"))
    assert db.scalar(select(Account).where(Account.user_id == "alice")).available == 96


async def test_another_angle_reshoots_an_approved_preview(db, monkeypatch):
    first = await try_on.preview(db, "alice", request())
    seen = {}

    async def capture(image_urls, prompt, aspect_ratio):
        seen["urls"], seen["prompt"] = image_urls, prompt
        return png()

    monkeypatch.setattr(try_on, "provider", lambda: type("P", (), {"generate": staticmethod(capture)})())
    await try_on.preview(
        db,
        "alice",
        request(angle="back", baseAssetId=first["asset"]["id"], idempotencyKey="preview-0003"),
    )

    # The approved preview replaces the person photo as the thing being re-shot.
    base = db.scalar(select(Asset).where(Asset.id == first["asset"]["id"]))
    assert base.storage_key in seen["urls"][0]
    assert ANGLES["back"] in seen["prompt"]
    assert "change only the camera position" in seen["prompt"]


async def test_an_unknown_base_preview_is_refused(db):
    with pytest.raises(DomainError) as exc:
        await try_on.preview(db, "alice", request(baseAssetId="coat"))
    assert exc.value.code == "INVALID_ASSET"


def test_angle_instructions_come_from_our_catalogue_not_the_request():
    assert compose(None, False).count("\n\n") == 4
    assert compose("detail", False).endswith(ANGLES["detail"])
    # An unknown label is ignored rather than passed through to the model.
    assert compose("../../etc", False) == compose(None, False)
