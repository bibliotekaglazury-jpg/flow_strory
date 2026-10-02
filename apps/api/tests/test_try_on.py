"""A look preview answers in one request: no quote, no job, no polling."""

import pytest
from sqlalchemy import create_engine, func, select
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


async def test_a_repeated_key_never_calls_the_provider_or_creates_a_second_asset(db, monkeypatch):
    """The credit ledger being idempotent is not enough on its own: a lost response must
    not re-run the paid provider call or leave a duplicate photo behind either."""
    calls = 0

    async def capture(*args):
        nonlocal calls
        calls += 1
        return png()

    monkeypatch.setattr(try_on, "provider", lambda: type("P", (), {"generate": staticmethod(capture)})())

    first = await try_on.preview(db, "alice", request())
    second = await try_on.preview(db, "alice", request())

    assert calls == 1
    assert first["asset"]["id"] == second["asset"]["id"]
    assert second["creditsCharged"] == 0
    assert db.scalar(select(Account).where(Account.user_id == "alice")).available == 100
    assert (
        db.scalar(select(func.count()).select_from(Asset).where(Asset.role == "tryon_photo")) == 1
    )


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


async def test_two_users_reusing_the_same_client_generated_key_never_collide(db, monkeypatch):
    session_key = "preview-0001"  # e.g. both browser tabs generated the same uuid by coincidence

    async def capture(*args):
        return png()

    monkeypatch.setattr(try_on, "provider", lambda: type("P", (), {"generate": staticmethod(capture)})())
    db.add(Account(user_id="bob", available=100, reserved=0))
    db.add(
        Asset(
            id="bob-model",
            user_id="bob",
            role="person",
            mime_type="image/png",
            file_name="bob-model.png",
            size_bytes=1,
            storage_key="bob/bob-model",
        )
    )
    db.flush()
    alice = await try_on.preview(db, "alice", request(idempotencyKey=session_key))
    bob = await try_on.preview(
        db,
        "bob",
        request(
            idempotencyKey=session_key,
            inputAssets={"productImageId": "stranger", "personImageId": "bob-model", "items": []},
        ),
    )
    assert alice["asset"]["id"] != bob["asset"]["id"]


async def test_an_unknown_base_preview_is_refused(db):
    with pytest.raises(DomainError) as exc:
        await try_on.preview(db, "alice", request(baseAssetId="coat"))
    assert exc.value.code == "INVALID_ASSET"


def test_angle_instructions_come_from_our_catalogue_not_the_request():
    assert compose(None, False).count("\n\n") == 4
    assert compose("detail", False).endswith(ANGLES["detail"])
    # An unknown label is ignored rather than passed through to the model.
    assert compose("../../etc", False) == compose(None, False)


def counting_provider(monkeypatch, fail=False):
    calls = []

    async def generate(*args):
        calls.append(args)
        if fail:
            raise ProviderError("IMAGE_SERVICE_ERROR", "The preview could not be created.")
        return png()

    monkeypatch.setattr(try_on, "provider", lambda: type("P", (), {"generate": staticmethod(generate)})())
    return calls


def priced(monkeypatch, price, app_env="development"):
    from types import SimpleNamespace

    monkeypatch.setattr(
        try_on, "settings", lambda: SimpleNamespace(image_credits_per_generation=price, app_env=app_env)
    )


async def test_the_price_is_reserved_before_the_provider_is_called(db, monkeypatch):
    calls = counting_provider(monkeypatch)
    priced(monkeypatch, 500)
    with pytest.raises(DomainError) as exc:
        await try_on.preview(db, "alice", request())
    assert exc.value.code == "INSUFFICIENT_CREDITS"
    assert calls == []


async def test_a_failed_generation_refunds_the_reserved_price(db, monkeypatch):
    counting_provider(monkeypatch, fail=True)
    priced(monkeypatch, 4)
    with pytest.raises(ProviderError):
        await try_on.preview(db, "alice", request())
    account = db.scalar(select(Account).where(Account.user_id == "alice"))
    assert (account.available, account.reserved) == (100, 0)
    kinds = sorted(row.kind for row in db.scalars(select(Ledger)))
    assert kinds == ["look_preview_refund", "look_preview_reserve"]

    # The same key can be retried after a refunded failure and is charged once.
    counting_provider(monkeypatch)
    result = await try_on.preview(db, "alice", request())
    assert result["creditsCharged"] == 4
    account = db.scalar(select(Account).where(Account.user_id == "alice"))
    assert (account.available, account.reserved) == (96, 0)


async def test_a_free_preview_outside_development_refuses_to_start(db, monkeypatch):
    calls = counting_provider(monkeypatch)
    priced(monkeypatch, 0, app_env="production")
    with pytest.raises(DomainError) as exc:
        await try_on.preview(db, "alice", request())
    assert exc.value.code == "PREVIEW_UNAVAILABLE"
    assert calls == []


async def test_a_karma_reserved_preview_never_debits_ugc_credits(db, monkeypatch):
    counting_provider(monkeypatch)
    priced(monkeypatch, 4, app_env="production")
    result = await try_on.preview(db, "alice", request(), reservation="hold-1")
    assert result["creditsCharged"] == 0
    account = db.scalar(select(Account).where(Account.user_id == "alice"))
    assert (account.available, account.reserved) == (100, 0)
    assert [row.kind for row in db.scalars(select(Ledger))] == [
        "karma_reservation",
        "karma_reservation_result",
    ]

    with pytest.raises(DomainError) as exc:
        await try_on.preview(db, "alice", request(idempotencyKey="preview-0009"), reservation="hold-1")
    assert exc.value.code == "RESERVATION_ALREADY_USED"


def test_openrouter_image_records_real_cost_and_per_model_limit():
    import asyncio
    import base64

    import httpx

    from app.providers.openrouter_image import OpenRouterImageProvider

    png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 16).decode()

    def handler(request):
        return httpx.Response(200, json={"data": [{"b64_json": png}], "usage": {"cost": 0.01}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenRouterImageProvider("k", "meta/muse-image", client=client)
            assert provider.max_references == 10
            urls = [f"https://media.example/{i}.png" for i in range(5)]
            await provider.generate(urls, "prompt", "4:5")
            return provider.last_cost_usd

    assert asyncio.run(run()) == 0.01
    assert OpenRouterImageProvider("k", "google/gemini-3-pro-image").max_references == 6
