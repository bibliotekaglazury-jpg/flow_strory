"""Offline service tests; provider traffic is replaced by fixtures."""

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.chat_api import ChatContext, SendMessage, ApplyRecipe
from app.db import Base, ChatSession, Account, Ledger, Generation
from app.errors import DomainError
from app.providers.chat import MockChatProvider
from app.schemas import Creative
from app.services import chat, chat_context


@pytest.fixture
def store(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(chat, "SessionLocal", factory)
    monkeypatch.setattr(chat, "provider", MockChatProvider)
    return factory


def message(text="Show the product", **context):
    return SendMessage(
        text=text,
        context=ChatContext(
            templateId="ugc_review", inputAssets={}, duration=15, aspectRatio="9:16", **context
        ),
    )


@pytest.mark.asyncio
async def test_failure_preserves_answer_but_cannot_apply_at_failed_revision(store, monkeypatch):
    session = await chat.create("alice")
    ready = await chat.send("alice", session["id"], message())

    class Broken(MockChatProvider):
        async def send_message(self, *args):
            raise ValueError("private provider payload")

    monkeypatch.setattr(chat, "provider", Broken)
    with pytest.raises(DomainError):
        await chat.send("alice", session["id"], message("Another concept"))
    failed = chat.get("alice", session["id"])
    assert failed["answer"] == ready["answer"]
    assert failed["revision"] == ready["revision"] + 1
    creative = Creative(
        templateId="ugc_review", inputAssets={}, brief="Product", duration=15, aspectRatio="9:16"
    )
    with pytest.raises(DomainError) as error:
        chat.apply("alice", session["id"], ApplyRecipe(revision=failed["revision"], creative=creative))
    assert error.value.code == "STALE_RECIPE"


@pytest.mark.asyncio
async def test_prior_concepts_survive_message_change_but_scope_changes_reset(store, monkeypatch):
    contexts = []

    class Capture(MockChatProvider):
        async def send_message(self, *args):
            contexts.append(args[-1])
            thread, answer = await super().send_message(*args)
            answer.creativePlan.creativeMechanism = "contrast-reveal"
            return thread, answer

    monkeypatch.setattr(chat, "provider", Capture)
    session = await chat.create("alice")
    await chat.send("alice", session["id"], message(brief="Original offer"))
    change = message("Change the concept", brief="Original offer").model_copy(
        update={"intent": "change_concept"}
    )
    await chat.send("alice", session["id"], change)
    assert contexts[1]["excludedMechanisms"] == ["contrast-reveal"]
    assert contexts[1]["contextBundle"]["priorConcepts"][0]["revision"] == 1
    await chat.send("alice", session["id"], message("Different offer", brief="New offer"))
    assert contexts[2]["priorConcepts"] == []


@pytest.mark.asyncio
async def test_durable_reservations_and_no_video_ledger_mutations(store, monkeypatch):
    monkeypatch.setattr(chat, "settings", lambda: SimpleNamespace(claude_session_budget_cents=10))
    with store.begin() as db:
        db.add(ChatSession(id="s", user_id="alice", provider="claude", status="responding", revision=1))
    first = chat.usage_charger("alice", "s", 1)
    await first(6, None)
    second = chat.usage_charger("alice", "s", 1)
    with pytest.raises(DomainError) as error:
        await second(5, None)
    assert error.value.code == "CHAT_BUDGET_EXCEEDED"
    await first(0, 2)
    await second(5, None)
    await second(0, 3)
    with store() as db:
        assert db.get(ChatSession, "s").planning_usage == {"spentCents": 5, "reservations": {}}
        for table in (Account, Ledger, Generation):
            assert db.scalar(select(func.count()).select_from(table)) == 0
    with pytest.raises(DomainError) as error:
        await chat.usage_charger("bob", "s", 1)(1, None)
    assert error.value.code == "CHAT_NOT_FOUND"


@pytest.mark.asyncio
async def test_changed_or_deleted_session_cannot_reserve_more(store, monkeypatch):
    monkeypatch.setattr(chat, "settings", lambda: SimpleNamespace(claude_session_budget_cents=10))
    with store.begin() as db:
        db.add(ChatSession(id="s", user_id="alice", provider="mock", status="responding", revision=1))
    charge = chat.usage_charger("alice", "s", 1)
    with store.begin() as db:
        db.get(ChatSession, "s").revision = 2
    with pytest.raises(DomainError) as error:
        await charge(1, None)
    assert error.value.code == "CHAT_CHANGED"
    await chat.delete("alice", "s")
    with pytest.raises(DomainError):
        await charge(1, None)


@pytest.mark.asyncio
async def test_concurrent_reservations_cannot_exceed_budget(store, monkeypatch):
    monkeypatch.setattr(chat, "settings", lambda: SimpleNamespace(claude_session_budget_cents=10))
    with store.begin() as db:
        db.add(ChatSession(id="s", user_id="alice", provider="claude", status="responding", revision=1))
    results = await asyncio.gather(
        *[chat.usage_charger("alice", "s", 1)(6, None) for _ in range(2)], return_exceptions=True
    )
    assert sum(isinstance(result, DomainError) for result in results) == 1
    with store() as db:
        assert sum(db.get(ChatSession, "s").planning_usage["reservations"].values()) == 6


@pytest.mark.asyncio
async def test_research_fallback_and_ssrf_fail_closed(monkeypatch):
    async def unavailable(*args):
        raise DomainError("PRODUCT_UNAVAILABLE", "Unavailable", 503)

    monkeypatch.setattr(chat_context, "download_public", unavailable)
    context = await chat_context.enrich(
        {"productUrl": "https://shop.example/product"}, [], allow_research=True
    )
    assert context["pageStatus"] == "failed" and context["page"] is None

    async def forbidden(*args):
        raise DomainError("INVALID_PRODUCT_URL", "Private target", 422)

    monkeypatch.setattr(chat_context, "download_public", forbidden)
    with pytest.raises(DomainError):
        await chat_context.enrich({"productUrl": "https://127.0.0.1"}, [], allow_research=True)


@pytest.mark.asyncio
async def test_structured_page_data_preserved_as_bounded_evidence(monkeypatch):
    async def download(url, *args):
        return (
            b'<title>Product</title><script type="application/ld+json">{"name":"Camera","offers":{"price":"30"}}</script><body>Camera details</body>',
            "text/html",
            url,
        )

    monkeypatch.setattr(chat_context, "download_public", download)
    context = await chat_context.enrich(
        message(productUrl="https://shop.example/product").context.model_dump(), []
    )
    facts = chat_context.bundle(context, [{"role": "user", "text": "Show camera"}], []).sourceFacts
    assert '"price": "30"' in facts[0].text
    assert context["pageStatus"] == "resolved"


@pytest.mark.asyncio
async def test_claude_service_stores_audit_and_usage_without_exposing_in_view(store, monkeypatch):
    from app.creative_audit import ChatProviderResult
    from app.db import ChatRecipeVersion

    class FixtureClaude(MockChatProvider):
        key = "claude"

        async def send_message(self, *args):
            context = args[-1]
            await context["chargeUsage"](4, None)
            await context["chargeUsage"](0, 2)
            thread, answer = await super().send_message(*args)
            return ChatProviderResult(thread, answer, {"selectedId": "fixture"}, {"costCents": 2})

    monkeypatch.setattr(chat, "provider", FixtureClaude)
    monkeypatch.setattr(
        chat, "settings", lambda: SimpleNamespace(claude_session_budget_cents=10, claude_timeout_seconds=5)
    )
    session = await chat.create("alice")
    result = await chat.send("alice", session["id"], message())
    assert "planning_usage" not in result and "creativeAudit" not in result
    with store() as db:
        assert db.get(ChatSession, session["id"]).planning_usage["spentCents"] == 2
        version = db.scalar(select(ChatRecipeVersion))
        assert version.recipe["planning"]["creativeAudit"]["selectedId"] == "fixture"
        assert version.recipe["planning"]["usage"]["costCents"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["error", "timeout", "cancel"])
async def test_failed_inflight_request_retains_budget_across_service_restart(store, monkeypatch, failure):
    started = asyncio.Event()

    class Interrupted(MockChatProvider):
        key = "claude"

        async def send_message(self, *args):
            await args[-1]["chargeUsage"](6, None)
            started.set()
            if failure == "error":
                raise RuntimeError("network delivery unknown")
            await asyncio.Event().wait()

    monkeypatch.setattr(chat, "provider", Interrupted)
    monkeypatch.setattr(
        chat, "settings", lambda: SimpleNamespace(claude_session_budget_cents=10, claude_timeout_seconds=0.02)
    )
    session = await chat.create("alice")
    task = asyncio.create_task(chat.send("alice", session["id"], message()))
    await started.wait()
    if failure == "cancel":
        task.cancel()
    with pytest.raises((DomainError, asyncio.CancelledError)):
        await task
    with store() as db:
        saved = db.get(ChatSession, session["id"])
        assert saved.status == "idle"
        assert sum(saved.planning_usage["reservations"].values()) == 6
    # A fresh provider instance and a new turn read persisted reservations.
    with pytest.raises(DomainError) as error:
        await chat.send("alice", session["id"], message("Retry"))
    assert error.value.code == "CHAT_BUDGET_EXCEEDED"
    with store() as db:
        assert sum(db.get(ChatSession, session["id"]).planning_usage["reservations"].values()) == 6


@pytest.mark.asyncio
async def test_legacy_tuple_recipe_answer_remains_compatible(store, monkeypatch):
    class Legacy(MockChatProvider):
        async def send_message(self, session_id, thread_id, messages, context):
            return await super().send_message(session_id, thread_id, messages, {"duration": 15})

    monkeypatch.setattr(chat, "provider", Legacy)
    session = await chat.create("alice")
    answer = await chat.send("alice", session["id"], message())
    assert answer["answer"]["recipe"] is not None
    assert answer["answer"]["creativePlan"] is None
