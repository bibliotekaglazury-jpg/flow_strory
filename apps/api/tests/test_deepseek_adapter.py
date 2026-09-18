import json

import httpx
import pytest

from app.config import Settings
from app.errors import DomainError
from app.providers.deepseek import DeepSeekCreativeDirectorAdapter
from app.providers.chat import mock_director
from app.video_recipe import VideoRecipe


def _recipe():
    return VideoRecipe.model_validate(
        {
            "intent": "Offer",
            "concept": "A meaningful reveal",
            "duration": 15,
            "aspectRatio": "9:16",
            "qualityTier": "auto",
            "subject": "Creator",
            "product": "Cup",
            "visualStyle": "UGC",
            "camera": "Still",
            "performance": "Natural",
            "scenes": [{"duration": 15, "description": "Reveal"}],
            "audio": "Native speech",
            "constraints": [],
            "negativeRules": [],
            "spokenContent": {"required": True, "language": "en", "dialogue": "Discover this cup."},
        }
    )


def ready(mechanism="curiosity-reveal", score=4):
    from app.creative_audit import MINIMUM_SCORES

    answer = mock_director(_recipe()).model_dump()
    answer["creativePlan"]["creativeMechanism"] = mechanism
    candidates = [
        {
            "id": str(i),
            "summary": "Bounded story summary",
            "mechanism": m,
            "scores": {k: score for k in MINIMUM_SCORES},
        }
        for i, m in enumerate([mechanism, "situational-interruption", "visual-comparison"])
    ]
    return {"answer": answer, "audit": {"candidates": candidates, "selectedId": "0"}}


def clarification():
    return {
        "answer": {
            "assistantMessage": "Co reklamujemy?",
            "assessment": "clarification_needed",
            "clarificationQuestion": "Co reklamujemy?",
            "creativePlan": None,
            "videoPlan": None,
        },
        "audit": None,
    }


def _compact(value):
    answer = value["answer"]
    return json.dumps(
        {
            "assistantMessage": answer["assistantMessage"],
            "assessment": answer["assessment"],
            "clarificationQuestion": answer["clarificationQuestion"],
            "creativePlanJson": (
                json.dumps(answer["creativePlan"]) if answer["creativePlan"] is not None else None
            ),
            "videoPlanJson": (json.dumps(answer["videoPlan"]) if answer["videoPlan"] is not None else None),
            "auditJson": json.dumps(value["audit"]) if value["audit"] is not None else None,
        }
    )


def _nested(value):
    """DeepSeek observed live: nests these as objects instead of escaping them as strings."""
    answer = value["answer"]
    return json.dumps(
        {
            "assistantMessage": answer["assistantMessage"],
            "assessment": answer["assessment"],
            "clarificationQuestion": answer["clarificationQuestion"],
            "creativePlanJson": answer["creativePlan"],
            "videoPlanJson": answer["videoPlan"],
            "auditJson": value["audit"],
        }
    )


def completion(
    value, finish_reason="stop", fenced=False, cost=0.002, prompt_tokens=1200, completion_tokens=400, nested=False
):
    text = _nested(value) if nested else _compact(value)
    if fenced:
        text = "```json\n" + text + "\n```"
    return {
        "choices": [{"message": {"content": text}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "cost": cost},
    }


class Client:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    async def post(self, url, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        body = next(self.replies)
        if isinstance(body, Exception):
            raise body
        status = body.pop("_status", 200)
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))


def adapter(replies, **cfg):
    client = Client(replies)
    return (
        DeepSeekCreativeDirectorAdapter(
            Settings(_env_file=None, openrouter_api_key="fake", **cfg), client=client
        ),
        client,
    )


@pytest.mark.asyncio
async def test_single_call_returns_a_ready_answer_with_no_vision_or_preparation_round():
    a, c = adapter([completion(ready())])
    result = await a.send_message("s", None, [{"role": "user", "text": "Sell a cup"}], {"contextBundle": {}})
    assert result.answer.assessment == "enough_to_plan"
    assert len(c.calls) == 1
    assert c.calls[0]["json"]["model"] == "deepseek/deepseek-chat"
    assert c.calls[0]["json"]["response_format"]["type"] == "json_schema"
    assert c.calls[0]["json"]["response_format"]["json_schema"]["strict"] is True
    assert result.audit["skills"] == ["copywriting", "ad-creative"]
    assert result.audit["researchUsed"] is False


@pytest.mark.asyncio
async def test_markdown_fences_around_the_json_body_are_stripped():
    a, c = adapter([completion(clarification(), fenced=True)])
    result = await a.send_message("s", None, [], {"contextBundle": {}})
    assert result.answer.assessment == "clarification_needed"


@pytest.mark.asyncio
async def test_actual_openrouter_cost_is_used_over_any_list_price():
    a, c = adapter([completion(clarification(), cost=0.00456)])
    result = await a.send_message("s", None, [], {"contextBundle": {}})
    assert result.usage["estimatedCents"] == pytest.approx(0.456)
    assert result.usage["inputTokens"] == 1200
    assert result.usage["outputTokens"] == 400


@pytest.mark.asyncio
async def test_one_repair_round_on_a_quality_gate_failure():
    a, c = adapter([completion(ready(score=1)), completion(ready())])
    result = await a.send_message("s", None, [], {"contextBundle": {}})
    assert result.answer.creativePlan.creativeMechanism == "curiosity-reveal"
    assert len(c.calls) == 2
    assert result.usage["repairs"] == ["CREATIVE_QUALITY_LOW"]
    assert "CREATIVE_QUALITY_LOW" in c.calls[-1]["json"]["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_truncated_output_is_not_accepted():
    a, c = adapter([completion(ready(), finish_reason="length"), completion(ready())])
    result = await a.send_message("s", None, [], {"contextBundle": {}})
    assert len(c.calls) == 2
    assert result.usage["repairs"] == ["CHAT_INVALID_RESPONSE"]


@pytest.mark.asyncio
async def test_rate_limit_maps_to_a_retryable_domain_error():
    a, c = adapter([{"_status": 429, "error": {"message": "rate limited"}}])
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {"contextBundle": {}})
    assert exc.value.code == "CHAT_RATE_LIMITED"
    assert exc.value.retryable is True


@pytest.mark.asyncio
async def test_health_requires_an_openrouter_key():
    a = DeepSeekCreativeDirectorAdapter(Settings(_env_file=None, openrouter_api_key=""))
    assert await a.health() is False
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {"contextBundle": {}})
    assert exc.value.code == "CHAT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_selected_format_still_supplies_its_playbook_and_structures():
    a, c = adapter([completion(ready())])
    await a.send_message(
        "s", None, [], {"contextBundle": {"selectedFormat": "product_demo", "availableAssets": []}}
    )
    body = c.calls[0]["json"]["messages"][-1]["content"]
    assert '"selectedPlaybook": {"label": "Product Demo"' in body or '"label":"Product Demo"' in body
    assert "CREATIVE_DIRECTION_REFERENCE" in body


@pytest.mark.asyncio
async def test_chat_service_selects_deepseek_and_records_real_planning_cost(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.chat_api import ChatContext, SendMessage
    from app.db import Base, ChatSession
    from app.services import chat

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(chat, "SessionLocal", factory)

    cfg = Settings(_env_file=None, chat_provider="deepseek", openrouter_api_key="fake")
    monkeypatch.setattr(chat, "settings", lambda: cfg)
    a, c = adapter([completion(clarification(), cost=0.003)], chat_provider="deepseek")
    monkeypatch.setattr(chat, "provider", lambda: a)

    session = await chat.create("alice")
    result = await chat.send(
        "alice",
        session["id"],
        SendMessage(
            text="Sell a cup",
            context=ChatContext(templateId="ugc_review", inputAssets={}, duration=15, aspectRatio="9:16"),
        ),
    )
    assert result["answer"]["needsMoreInformation"] is True
    with factory.begin() as db:
        assert db.get(ChatSession, session["id"]).planning_usage["spentCents"] == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_nested_json_objects_are_accepted_alongside_escaped_json_strings():
    # The system prompt asks for these fields as JSON strings; DeepSeek's json_object
    # mode has been observed nesting them as objects instead. Both parse the same way.
    a, c = adapter([completion(ready(), nested=True)])
    result = await a.send_message("s", None, [], {"contextBundle": {}})
    assert result.answer.assessment == "enough_to_plan"
    assert result.answer.creativePlan.creativeMechanism == "curiosity-reveal"
