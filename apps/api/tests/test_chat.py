import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.chat_api import ChatContext, SendMessage, ApplyRecipe, SessionView
from app.db import Base, Account, Generation, Ledger, Prompt, ChatRecipeVersion
from app.errors import DomainError
from app.providers.chat import MockChatProvider
from app.schemas import Creative
from app.services import chat
from app.video_recipe import RecipeAnswer, compile_recipe


@pytest.fixture
def store(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(chat, "SessionLocal", factory)
    adapter = MockChatProvider()
    monkeypatch.setattr(chat, "provider", lambda: adapter)
    return factory


def message(text="Show the product in natural light"):
    return SendMessage(
        text=text,
        context=ChatContext(templateId="ugc_review", inputAssets={}, duration=15, aspectRatio="9:16"),
    )


@pytest.mark.asyncio
async def test_applying_a_concept_planned_with_look_items(store):
    # The staleness check used to read inputAssets' scalar values directly, so a look
    # item (a list) made "Use this concept" fail with a 500 instead of applying.
    from app.db import Asset

    with store.begin() as db:
        for identifier in ("hero", "scarf"):
            db.add(
                Asset(
                    id=identifier,
                    user_id="alice",
                    role="product",
                    mime_type="image/png",
                    file_name=f"{identifier}.png",
                    size_bytes=1,
                    storage_key=f"alice/{identifier}",
                )
            )
    assets = {"productImageId": "hero", "items": [{"assetId": "scarf", "label": "scarf"}]}
    session = await chat.create("alice")
    session = await chat.send(
        "alice",
        session["id"],
        SendMessage(
            text="Show the sunglasses and the scarf worn together",
            context=ChatContext(
                templateId="ugc_review", inputAssets=assets, duration=15, aspectRatio="9:16"
            ),
        ),
    )
    result = chat.apply(
        "alice",
        session["id"],
        ApplyRecipe(
            revision=session["revision"],
            creative=Creative(
                templateId="ugc_review",
                inputAssets=assets,
                brief="Original",
                duration=15,
                aspectRatio="9:16",
            ),
        ),
    )
    assert result["prompt"]["promptId"]
    assert result["creative"]["inputAssets"]["items"][0]["label"] == "scarf"


@pytest.mark.asyncio
async def test_persistence_continuation_apply_no_generation_or_credits(store):
    first = await chat.create("alice")
    first = await chat.send("alice", first["id"], message())
    second = await chat.send("alice", first["id"], message("Use a product close-up"))
    assert len(chat.get("alice", first["id"])["messages"]) == 4
    assert second["revision"] == 2
    assert "provider_thread_id" not in SessionView.model_validate(second).model_dump()
    creative = Creative(
        templateId="ugc_review",
        inputAssets={},
        productUrl="https://example.com/product",
        brief="Original",
        duration=20,
        aspectRatio="16:9",
    )
    body = ApplyRecipe(revision=2, creative=creative)
    result = chat.apply("alice", first["id"], body)
    assert result["creative"]["duration"] == 15
    assert result["creative"]["brief"] == "Use a product close-up"
    with store() as db:
        p = db.get(Prompt, result["prompt"]["promptId"])
        assert p.user_id == "alice" and "Scene 1" in p.text
        assert p.recipe["language"] == result["creative"]["language"]
        assert db.scalar(select(func.count()).select_from(ChatRecipeVersion)) == 2
        for table in (Generation, Ledger, Account):
            assert db.scalar(select(func.count()).select_from(table)) == 0
    with pytest.raises(DomainError, match="latest recipe"):
        chat.apply("alice", first["id"], body.model_copy(update={"revision": 1}))
    with pytest.raises(DomainError):
        chat.get("bob", first["id"])
    await chat.delete("alice", first["id"])
    with pytest.raises(DomainError):
        chat.get("alice", first["id"])


@pytest.mark.asyncio
async def test_schema_rejects_extra_fields_bad_timing_and_clarification():
    _, answer = await MockChatProvider().send_message("s", None, [{"text": "Product"}], {"duration": 15})
    value = answer.model_dump()
    value["recipe"]["scenes"][0]["duration"] = 20
    with pytest.raises(ValidationError):
        RecipeAnswer.model_validate(value)
    value = answer.model_dump()
    value["reasoning"] = "must never be persisted"
    with pytest.raises(ValidationError):
        RecipeAnswer.model_validate(value)
    value = answer.model_dump()
    value["needsMoreInformation"] = True
    with pytest.raises(ValidationError):
        RecipeAnswer.model_validate(value)
    assert "Product" in compile_recipe(answer.recipe)


def test_exported_schema_matches_canonical_pydantic():
    schema = Path(__file__).resolve().parents[3] / "packages/contracts/video-recipe.schema.json"
    assert json.loads(schema.read_text()) == RecipeAnswer.model_json_schema()


@pytest.mark.asyncio
async def test_failed_reply_keeps_user_message_but_no_provider_details(store, monkeypatch):
    item = await chat.create("alice")

    class Broken(MockChatProvider):
        async def send_message(self, *args):
            raise RuntimeError("private provider payload")

    monkeypatch.setattr(chat, "provider", Broken)
    with pytest.raises(DomainError) as error:
        await chat.send("alice", item["id"], message())
    assert "private" not in str(error.value)
    saved = chat.get("alice", item["id"])
    assert saved["status"] == "idle" and saved["answer"] is None
    assert len(saved["messages"]) == 1


@pytest.mark.asyncio
async def test_serial_turns_and_reset_discard_late_reply(store, monkeypatch):
    import asyncio

    started, cancelled = asyncio.Event(), asyncio.Event()

    class Slow(MockChatProvider):
        async def send_message(self, *args):
            started.set()
            await cancelled.wait()
            return await super().send_message(*args)

        async def cancel(self, session_id):
            cancelled.set()

    adapter = Slow()
    monkeypatch.setattr(chat, "provider", lambda: adapter)
    item = await chat.create("alice")
    task = asyncio.create_task(chat.send("alice", item["id"], message()))
    await started.wait()
    with pytest.raises(DomainError) as error:
        await chat.send("alice", item["id"], message("Another turn"))
    assert error.value.code == "CHAT_BUSY"
    await chat.delete("alice", item["id"])
    with pytest.raises(DomainError):
        await task
    with pytest.raises(DomainError):
        chat.get("alice", item["id"])


def test_http_contracts_are_owned_and_provider_neutral(monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool
    from app.main import app
    from app.auth import identity

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(chat, "SessionLocal", sessionmaker(engine, expire_on_commit=False))
    monkeypatch.setattr(chat, "provider", MockChatProvider)
    app.dependency_overrides[identity] = lambda: "alice"
    try:
        with TestClient(app) as client:
            created = client.post("/api/chat/sessions", json={})
            assert created.status_code == 201
            path = "/api/chat/sessions/" + created.json()["id"]
            response = client.post(path + "/messages", json=message().model_dump())
            assert response.status_code == 200
            assert len(client.get(path + "/messages").json()) == 2
            assert client.get(path).json()["answer"]["recipe"]["qualityTier"] == "auto"
            bad = message().model_dump() | {"providerThreadId": "injected"}
            assert client.post(path + "/messages", json=bad).status_code == 422
            assert "provider_thread" not in response.text and "reasoning" not in response.text
            assert client.delete(path).json() == {"deleted": True}
            assert client.get(path).status_code == 404
    finally:
        app.dependency_overrides.pop(identity, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("gateway", ["mock", "openrouter-transport"])
async def test_mock_video_uses_existing_worker_storage_and_history(tmp_path, monkeypatch, gateway):
    from app import worker
    from app.db import Job, Asset, Output, now
    from app.providers.mock import MockVideoProvider
    from app.providers.registry import RegisteredModel
    from app.services.credits import grant, reserve
    from app.services.generations import view

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    adapter = MockVideoProvider()
    if gateway == "openrouter-transport":
        import httpx
        from app.providers.openrouter import OpenRouterVideoProvider

        def handle(req):
            return httpx.Response(
                202 if req.method == "POST" else 200,
                json={
                    "id": "fixture-job",
                    "status": "pending" if req.method == "POST" else "completed",
                    "unsigned_urls": (
                        []
                        if req.method == "POST"
                        else ["https://openrouter.ai/api/v1/videos/fixture-job/content?index=0"]
                    ),
                },
            )

        adapter = OpenRouterVideoProvider(
            "fake", 1, client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
        )

        async def download(_):
            return worker.simulation_fixture(15, "9:16")

        monkeypatch.setattr(adapter, "download_output", download)

        async def reject_public_download(*_args, **_kwargs):
            raise AssertionError("OpenRouter content must be downloaded with provider authentication")

        monkeypatch.setattr(worker, "download_public", reject_public_download)
        # Validation itself has separate audio/duration tests; this fixture tests worker/ledger storage only.
        monkeypatch.setattr(
            "app.services.video_validation.validate_native_video",
            lambda data, duration: bool(data) and duration == 15,
        )
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "registry", lambda: (RegisteredModel("test-video", "Test", adapter),))

    class LocalStorage:
        def url(self, key):
            return "http://localhost/" + key, now().isoformat()

    monkeypatch.setattr(worker, "Storage", LocalStorage)

    # Store through the worker's normal Asset/Output boundary, retaining actual fixture bytes.
    def store_asset(db, storage, user, role, data, filename):
        (tmp_path / filename).write_bytes(data)
        asset = Asset(
            user_id=user,
            role=role,
            mime_type="video/mp4",
            file_name=filename,
            size_bytes=len(data),
            storage_key=filename,
            width=360,
            height=640,
            duration_seconds=15,
        )
        db.add(asset)
        db.flush()
        return asset

    monkeypatch.setattr(worker, "store_asset", store_asset)
    with factory.begin() as db:
        db.add(Account(user_id="alice", available=0, reserved=0))
        db.flush()
        grant(db, "alice", 100, "initial")
        generation = Generation(
            id="g",
            user_id="alice",
            selected_model="test-video",
            snapshot={
                "templateId": "ugc_review",
                "duration": 15,
                "aspectRatio": "9:16",
                "inputAssets": {},
                "prompt": "Show product",
                "model": "auto",
            },
            request_hash="x",
            idempotency_key="k",
            estimated=15,
        )
        db.add(generation)
        db.flush()
        reserve(db, generation)
        job = Job(id="j", generation_id="g", lease_owner="worker", lease_until=now())
        db.add(job)
    await worker.process("j", "worker")
    with factory.begin() as db:
        job = db.get(Job, "j")
        assert job.submission_state == "submitted"
        # Advance simulated time without waiting or calling any vendor.
        job.provider_job_id = "simulation:0:fixture" if gateway == "mock" else "fixture-job"
        job.lease_owner = "worker"
    await worker.process("j", "worker")
    with factory() as db:
        generation = db.get(Generation, "g")
        assert generation.status == "completed" and generation.charged == 15
        assert db.scalar(select(func.count()).select_from(Output)) == 1
        assert db.get(Account, "alice").reserved == 0
        public = view(db, generation, LocalStorage())
        assert public["status"] == "completed" and len(public["outputAssets"]) == 1
    assert (
        tmp_path / ("development-simulation.mp4" if gateway == "mock" else "generated-video.mp4")
    ).stat().st_size > 1000


@pytest.mark.asyncio
async def test_old_demo_is_not_restored_as_live_chat(store, monkeypatch):
    item = await chat.create("alice")

    class Live(MockChatProvider):
        key = "claude"

    monkeypatch.setattr(chat, "provider", Live)
    with pytest.raises(DomainError) as error:
        chat.get("alice", item["id"])
    assert error.value.code == "CHAT_PROVIDER_CHANGED"


@pytest.mark.asyncio
async def test_url_apply_does_not_refetch_remote_page(store, monkeypatch):
    from app.services import chat_context

    item = await chat.create("alice")
    item = await chat.send("alice", item["id"], message())
    monkeypatch.setattr(chat.provider(), "key", "claude")

    async def enrich(context, references):
        raise AssertionError("Apply must use the already resolved URL, not fetch it again")

    monkeypatch.setattr(chat_context, "enrich", enrich)
    creative = Creative(
        templateId="ugc_review",
        inputAssets={},
        productUrl="https://example.com/product",
        brief="Product",
        duration=15,
        aspectRatio="9:16",
    )
    result = await chat.apply_with_references(
        "alice", item["id"], ApplyRecipe(revision=item["revision"], creative=creative)
    )
    with store() as db:
        prompt = db.get(Prompt, result["prompt"]["promptId"])
        assert prompt.snapshot["productUrl"] == "https://example.com/product"
        assert db.scalar(select(func.count()).select_from(Generation)) == 0
