import json
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.errors import DomainError
from app.providers.claude import (
    ClaudeCreativeDirectorAdapter,
    parse_director_envelope,
    transport_schema,
)


def response(value, usage=None, stop="end_turn", thinking=True):
    if isinstance(value, dict) and "answer" in value:
        answer = value["answer"]
        value = {
            "assistantMessage": answer["assistantMessage"],
            "assessment": answer["assessment"],
            "clarificationQuestion": answer["clarificationQuestion"],
            "creativePlanJson": (
                json.dumps(answer["creativePlan"]) if answer["creativePlan"] is not None else None
            ),
            "videoPlanJson": (json.dumps(answer["videoPlan"]) if answer["videoPlan"] is not None else None),
            "auditJson": json.dumps(value["audit"]) if value["audit"] is not None else None,
        }
    blocks = [SimpleNamespace(type="thinking", thinking="PRIVATE-THINKING")] if thinking else []
    blocks.append(SimpleNamespace(type="text", text=json.dumps(value)))
    return SimpleNamespace(
        content=blocks,
        stop_reason=stop,
        model="claude-sonnet-5",
        usage=SimpleNamespace(**(usage or {"input_tokens": 100, "output_tokens": 200})),
    )


class Client:
    def __init__(self, replies):
        self.messages = self
        self.replies = iter(replies)
        self.calls = []
        self.counted = []

    async def count_tokens(self, **kwargs):
        # The real endpoint rejects server tools; record kwargs so tests can hold that line.
        self.counted.append(kwargs)
        return SimpleNamespace(input_tokens=100)

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


def preparation(**overrides):
    return {
        "skillIds": [],
        "consumptionModels": [],
        "research": "none",
        "query": None,
        "offerIdentified": True,
        "contextAdequate": True,
        "researchRequested": False,
        "researchDeclined": False,
        **overrides,
    }


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


def adapter(replies, **cfg):
    client = Client(replies)
    return ClaudeCreativeDirectorAdapter(
        # Existing cases script the assessment reply; skipping it has its own tests below.
        Settings(
            _env_file=None,
            anthropic_api_key="fake",
            **{"claude_skip_preparation_without_url": False, **cfg},
        ),
        client=client,
    ), client


def test_transport_schema_is_bounded_and_keeps_strict_object_shape():
    from app.creative_audit import DirectorEnvelope

    schema = transport_schema(DirectorEnvelope)
    serialized = json.dumps(schema)
    assert len(serialized) < 6000
    assert '"pattern"' not in serialized and '"maxLength"' not in serialized
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "assistantMessage",
        "assessment",
        "clarificationQuestion",
        "creativePlanJson",
        "videoPlanJson",
        "auditJson",
    }


@pytest.mark.asyncio
async def test_native_images_structured_output_and_no_thinking_leak():
    a, client = adapter([response(preparation()), response(clarification())])
    result = await a.send_message(
        "s",
        None,
        [{"role": "user", "text": "Kurs online"}],
        {"contextBundle": {}, "images": [{"role": "product", "data": b"image"}]},
    )
    assert result.answer.assessment == "clarification_needed"
    assert "PRIVATE-THINKING" not in repr(result)
    assert "PRIVATE-THINKING" not in repr(client.calls)
    assert len(client.calls) == 2
    assert client.calls[-1]["output_config"]["format"]["type"] == "json_schema"
    assert client.calls[-1]["thinking"] == {"type": "adaptive"}
    assert client.calls[-1]["output_config"]["effort"] == "medium"
    assert any(b["type"] == "image" for b in client.calls[-1]["messages"][-1]["content"])
    assert all("temperature" not in call and "tools" not in call for call in client.calls)


@pytest.mark.asyncio
async def test_complete_offer_denies_requested_search():
    a, client = adapter(
        [response(preparation(research="search", query="private data")), response(clarification())]
    )
    await a.send_message("s", None, [], {"contextBundle": {}})
    assert all("tools" not in call for call in client.calls)


@pytest.mark.asyncio
async def test_budget_failure_makes_no_model_call():
    a, client = adapter([response(preparation())], claude_session_budget_cents=1)
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {"contextBundle": {}})
    assert exc.value.code == "CHAT_BUDGET_EXCEEDED"
    assert not client.calls


@pytest.mark.asyncio
async def test_context_limit_applies_to_each_request_not_the_sum_of_rounds():
    per_request_tokens = 15_535
    a, client = adapter(
        [
            response(
                preparation(),
                usage={"input_tokens": per_request_tokens, "output_tokens": 10},
            ),
            response(
                clarification(),
                usage={"input_tokens": per_request_tokens, "output_tokens": 10},
            ),
        ],
        claude_max_input_tokens=24_000,
    )

    async def count_tokens(**kwargs):
        return SimpleNamespace(input_tokens=per_request_tokens)

    client.count_tokens = count_tokens

    result = await a.send_message("s", None, [], {"contextBundle": {}})

    assert result.answer.assessment == "clarification_needed"
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_validation_errors_log_field_and_type_only(caplog):
    import logging

    malformed = ready()
    malformed["answer"]["creativePlan"]["hookStrategy"] = "not-a-real-strategy"
    a, c = adapter(
        [response(preparation()), response(malformed), response({}, stop="max_tokens")]
    )
    with caplog.at_level(logging.INFO, logger="app.providers.claude"):
        with pytest.raises(DomainError):
            await a.send_message("s", None, [], {})
    records = [r for r in caplog.records if r.message.startswith("creative_director_validation_error")]
    assert len(records) == 1
    assert records[0].message == "creative_director_validation_error round=0 errors=['hookStrategy:literal_error']"
    logged = caplog.text
    assert "not-a-real-strategy" not in logged
    assert "PRIVATE-THINKING" not in logged


@pytest.mark.asyncio
async def test_one_repair_only_and_truncated_result_not_accepted():
    a, client = adapter(
        [response(preparation()), response({}, stop="max_tokens"), response({}, stop="max_tokens")]
    )
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {"contextBundle": {}})
    assert exc.value.code == "CHAT_INVALID_RESPONSE"
    assert len(client.calls) == 3


@pytest.mark.asyncio
async def test_missing_key_health_no_request():
    a, client = adapter([])
    a.cfg.anthropic_api_key = type(a.cfg.anthropic_api_key)("")
    assert not await a.health()
    assert not client.calls


def ready(mechanism="curiosity-reveal", score=4):
    from app.creative_audit import MINIMUM_SCORES

    # Reuse only the established schema fixture, not production creative logic.
    from app.providers.chat import mock_director
    from app.video_recipe import VideoRecipe

    recipe = VideoRecipe.model_validate(
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
    answer = mock_director(recipe).model_dump()
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


def test_provider_mechanism_labels_are_normalized_before_strict_validation():
    value = ready()
    value["answer"]["creativePlan"]["creativeMechanism"] = "Visual Contrast / Reveal"
    value["audit"]["candidates"][0]["mechanism"] = "Visual Contrast / Reveal"
    transport = json.loads(response(value, thinking=False).content[0].text)
    envelope = parse_director_envelope(json.dumps(transport))
    assert envelope.answer.creativePlan.creativeMechanism == "visual-contrast-reveal"
    assert envelope.audit.candidates[0].mechanism == "visual-contrast-reveal"


def test_out_of_range_confidence_is_rescaled_not_rejected():
    # Observed live: a weaker model reused the neighbouring 0-5 quality-score scale for
    # confidence, which is documented as a 0-1 probability.
    value = ready()
    value["answer"]["creativePlan"]["confidence"] = 4
    transport = json.loads(response(value, thinking=False).content[0].text)
    envelope = parse_director_envelope(json.dumps(transport))
    assert envelope.answer.creativePlan.confidence == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_low_quality_repairs_once_and_retains_no_invalid_output():
    a, c = adapter([response(preparation()), response(ready(score=1)), response(ready())])
    result = await a.send_message("s", None, [], {"contextBundle": {}})
    assert result.answer.creativePlan.creativeMechanism == "curiosity-reveal"
    assert len(c.calls) == 3
    assert "CREATIVE_QUALITY_LOW" in str(c.calls[-1])


@pytest.mark.asyncio
async def test_second_structurally_valid_low_scored_answer_is_returned():
    a, c = adapter(
        [response(preparation()), response(ready(score=1)), response(ready(score=2))]
    )

    result = await a.send_message("s", None, [], {"contextBundle": {}})

    assert result.answer.assessment == "enough_to_plan"
    assert result.audit["qualityGatePassed"] is False
    assert len(c.calls) == 3


@pytest.mark.asyncio
async def test_repeated_mechanism_exhausted_and_next_turn_resets_repair():
    a, c = adapter(
        [
            response(preparation()),
            response(ready()),
            response(ready()),
            response(preparation()),
            response(ready(score=1)),
            response(ready()),
        ]
    )
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {"excludedMechanisms": ["curiosity-reveal"]})
    assert exc.value.code == "CONCEPT_SPACE_EXHAUSTED"
    result = await a.send_message("s", None, [], {})
    assert result.answer.assessment == "enough_to_plan"
    assert len(c.calls) == 6


@pytest.mark.asyncio
async def test_explicit_research_refusal_overrides_hostile_preparation():
    a, c = adapter(
        [
            response(
                preparation(contextAdequate=False, research="search", query="x", researchRequested=True)
            ),
            response(clarification()),
        ]
    )
    await a.send_message("s", None, [{"role": "user", "text": "Do not research. Sell my course."}], {})
    assert all("tools" not in call for call in c.calls)


@pytest.mark.asyncio
async def test_research_cannot_spend_final_round():
    a, c = adapter(
        [
            response(preparation(contextAdequate=False, research="search", query="x")),
            response(clarification()),
        ],
        claude_max_rounds=2,
    )
    await a.send_message("s", None, [], {})
    assert len(c.calls) == 2
    assert all("tools" not in call for call in c.calls)


@pytest.mark.asyncio
async def test_search_preserves_only_cited_evidence_not_thinking_or_ciphertext():
    researched = response("UNSOURCED CLAIM")
    researched.content += [
        SimpleNamespace(
            type="web_search_tool_result",
            content=[
                SimpleNamespace(
                    url="https://example.com/product", title="Coffee cup", encrypted_content="CIPHER"
                )
            ],
        )
    ]
    researched.content[1].citations = [
        SimpleNamespace(url="https://example.com/product", cited_text="Ceramic cup")
    ]
    a, c = adapter(
        [
            response(preparation(contextAdequate=False, research="search", query="cup")),
            researched,
            response(clarification()),
        ]
    )
    result = await a.send_message("s", None, [], {})
    assert len(c.calls) == 3
    assert "format" not in c.calls[1]["output_config"]
    assert "product-marketing" in result.audit["skills"]
    final = str(c.calls[-1])
    assert "Ceramic cup" in final and "CIPHER" not in final and "UNSOURCED CLAIM" not in final
    assert result.audit["sourceDomains"] == ["example.com"]


@pytest.mark.asyncio
async def test_wrong_aspect_ratio_triggers_repair_instead_of_losing_the_turn():
    # compile_plan runs outside the repair loop, so a ratio mismatch there would surface
    # as a generic CHAT_FAILED. The gate must catch it while a retry is still possible.
    wrong = ready()
    wrong["answer"]["videoPlan"]["aspectRatio"] = "16:9"
    a, c = adapter([response(preparation()), response(wrong), response(ready())])
    result = await a.send_message(
        "s", None, [], {"contextBundle": {"selectedFormat": "ugc_review", "aspectRatio": "9:16"}}
    )
    assert result.answer.videoPlan.aspectRatio == "9:16"
    assert len(c.calls) == 3
    assert "CREATIVE_RATIO_MISMATCH" in str(c.calls[-1])


@pytest.mark.asyncio
async def test_matching_aspect_ratio_passes_without_a_repair():
    a, c = adapter([response(preparation()), response(ready())])
    await a.send_message(
        "s", None, [], {"contextBundle": {"selectedFormat": "ugc_review", "aspectRatio": "9:16"}}
    )
    assert len(c.calls) == 2


@pytest.mark.asyncio
async def test_wrong_language_triggers_repair_instead_of_silently_defaulting():
    # The exact bug: Auto mode's filler text is English, so without requestedLanguage
    # the director would infer English even when the user picked Polish.
    wrong = ready()
    wrong["answer"]["creativePlan"]["language"] = "en"
    wrong["answer"]["creativePlan"]["spokenLanguage"] = "en"
    wrong["answer"]["videoPlan"]["language"] = "en"
    wrong["answer"]["videoPlan"]["spokenLanguage"] = "en"
    fixed = ready()
    fixed["answer"]["creativePlan"]["language"] = "pl"
    fixed["answer"]["creativePlan"]["spokenLanguage"] = "pl"
    fixed["answer"]["videoPlan"]["language"] = "pl"
    fixed["answer"]["videoPlan"]["spokenLanguage"] = "pl"
    a, c = adapter([response(preparation()), response(wrong), response(fixed)])
    result = await a.send_message(
        "s",
        None,
        [],
        {"contextBundle": {"selectedFormat": "ugc_review", "requestedLanguage": "pl"}},
    )
    assert result.answer.videoPlan.spokenLanguage == "pl"
    assert len(c.calls) == 3
    assert "CREATIVE_LANGUAGE_MISMATCH" in str(c.calls[-1])


@pytest.mark.asyncio
async def test_recreate_repairs_a_plan_that_drifts_off_the_reused_mechanism():
    # Recreate applies a proven mechanism to a different offer, so the slug is a
    # requirement; everything else in the plan is still written from scratch.
    a, c = adapter(
        [
            response(preparation()),
            response(ready(mechanism="something-else")),
            response(ready(mechanism="curiosity-reveal")),
        ]
    )
    result = await a.send_message(
        "s",
        None,
        [],
        {
            "contextBundle": {
                "selectedFormat": "ugc_review",
                "preferredMechanism": "curiosity-reveal",
            }
        },
    )
    assert result.answer.creativePlan.creativeMechanism == "curiosity-reveal"
    assert len(c.calls) == 3
    assert "CREATIVE_MECHANISM_MISMATCH" in str(c.calls[-1])


@pytest.mark.asyncio
async def test_offer_profile_reaches_the_director_with_one_category_overlay():
    a, c = adapter(
        [
            response(preparation(consumptionModels=["narrative_immersion", "collectible_aesthetic"])),
            response(ready()),
        ]
    )
    await a.send_message(
        "s",
        None,
        [],
        {
            "contextBundle": {
                "selectedFormat": "auto",
                "userText": "wypromuj ksiazke w nowej kolorowej edycji",
                "brief": "",
                "availableAssets": [],
                "sourceFacts": [],
            },
            "pageStatus": "not_requested",
        },
    )
    reference = reference_block(c.calls[-1])
    assert reference["consumptionModels"] == ["narrative_immersion", "collectible_aesthetic"]
    assert reference["categoryOverlay"]["niche"] == "narrative_media"
    assert 2 <= len(reference["categoryOverlay"]["forbiddenReductions"]) <= 4
    assert reference["evidenceAvailable"] == []
    # Hybrid consumption widens retrieval; narrative structures must actually be offered.
    assert len(reference["structures"]) == 10
    assert any("narrative_media" in s["niche"] for s in reference["structures"])


@pytest.mark.asyncio
async def test_unknown_consumption_models_are_dropped_not_forwarded():
    a, c = adapter(
        [response(preparation(consumptionModels=["not_a_real_model", "narrative_immersion"])), response(ready())]
    )
    await a.send_message("s", None, [], {"contextBundle": {"selectedFormat": "ugc_review"}})
    assert reference_block(c.calls[-1])["consumptionModels"] == ["narrative_immersion"]


def test_vision_slots_rank_by_who_chose_the_image():
    from app.providers.claude import VISION_SLOTS, vision_slots

    images = [
        {"role": "product", "label": "sunglasses"},
        {"role": "product page image"},
        {"role": "source video frame"},
        {"role": "person"},
        {"role": "product", "label": "scarf"},
        {"role": "product", "label": "bag"},
        {"role": "source video frame"},
    ]
    ordered = vision_slots(images)
    assert len(ordered) == VISION_SLOTS
    # Uploaded items first, in upload order; then presenter, then sampled frames.
    assert [i.get("label") for i in ordered[:3]] == ["sunglasses", "scarf", "bag"]
    assert ordered[3]["role"] == "person"
    assert ordered[4]["role"] == "source video frame"
    # The one image nobody deliberately chose is what gets dropped.
    assert all("page" not in i["role"] for i in ordered)


@pytest.mark.asyncio
async def test_look_item_labels_are_named_next_to_their_image():
    a, c = adapter([response(preparation()), response(ready())])
    await a.send_message(
        "s",
        None,
        [],
        {
            "contextBundle": {"selectedFormat": "ugc_review"},
            "images": [
                {"role": "product", "data": b"one", "label": "sunglasses"},
                {"role": "person", "data": b"two", "label": None},
            ],
        },
    )
    labels = [
        b["text"]
        for b in c.calls[-1]["messages"][-1]["content"]
        if b.get("text", "").startswith("Reference role:")
    ]
    assert "Reference role: product — sunglasses" in labels
    assert "Reference role: person" in labels


@pytest.mark.asyncio
async def test_page_imagery_reaches_structure_retrieval():
    a, c = adapter([response(preparation()), response(ready())])
    await a.send_message(
        "s",
        None,
        [],
        {
            "contextBundle": {"selectedFormat": "ugc_review", "availableAssets": []},
            "images": [{"role": "product page image", "data": b"image"}],
        },
    )
    offered = reference_block(c.calls[-1])["structures"]
    assert any("product_image" in s["assetRequirements"] for s in offered)


@pytest.mark.asyncio
async def test_director_instructions_are_cached_and_repairs_reuse_them():
    a, c = adapter([response(preparation()), response(ready(score=1)), response(ready())])
    await a.send_message("s", None, [], {"contextBundle": {"selectedFormat": "ugc_review"}})
    director_calls = [call for call in c.calls if isinstance(call["system"], list)]
    assert len(director_calls) == 2
    for call in director_calls:
        assert [block["cache_control"] for block in call["system"]] == [{"type": "ephemeral"}]
        assert "CANONICAL INNER SCHEMAS" in call["system"][0]["text"]
    # The repair must reuse the identical cached prefix, or the cache never pays off.
    assert director_calls[0]["system"] == director_calls[1]["system"]
    # Preparation instructions stay below the cacheable minimum, so they are not marked.
    assert isinstance(c.calls[0]["system"], str)


@pytest.mark.asyncio
async def test_cached_system_is_measured_and_sent_identically():
    a, c = adapter([response(preparation()), response(ready())])
    await a.send_message("s", None, [], {"contextBundle": {}})
    assert c.counted[-1]["system"] == c.calls[-1]["system"]


@pytest.mark.asyncio
async def test_server_tools_never_reach_the_count_tokens_endpoint():
    # Real API: "Server tools are not supported in the count_tokens endpoint".
    researched = response("summary")
    researched.content += [
        SimpleNamespace(
            type="web_search_tool_result",
            content=[SimpleNamespace(url="https://example.com/x", title="X")],
        )
    ]
    a, c = adapter(
        [
            response(preparation(contextAdequate=False, research="search", query="cup")),
            researched,
            response(clarification()),
        ]
    )
    await a.send_message("s", None, [], {})
    assert any("tools" in call for call in c.calls)
    assert all("tools" not in counted for counted in c.counted)
    assert len(c.counted) == len(c.calls)


@pytest.mark.asyncio
async def test_unread_supplied_page_is_fetched_even_when_the_offer_is_unknown(monkeypatch):
    # Zalando blocks the server-side fetch, so the page arrives as failed and no product
    # is visible in the images. Asking "what is the product?" while its own page sits
    # unread is the wrong move; fetching is what identifies it.
    from urllib.parse import urlsplit

    monkeypatch.setattr("app.services.product.public_target", lambda u: (urlsplit(u), "1.1.1.1"))
    fetched = response("not evidence")
    fetched.content += [
        SimpleNamespace(
            type="web_fetch_tool_result",
            content=SimpleNamespace(
                type="web_fetch_result",
                url="https://example.com/bag",
                content=SimpleNamespace(source=SimpleNamespace(data="Brown shopper tote, 30x40cm")),
            ),
        )
    ]
    a, c = adapter(
        [
            response(
                preparation(research="fetch", offerIdentified=False, contextAdequate=False)
            ),
            fetched,
            response(clarification()),
        ]
    )
    result = await a.send_message(
        "s", None, [], {"productUrl": "https://example.com/bag", "pageStatus": "failed"}
    )
    assert result.usage["fetches"] == 1
    assert "Brown shopper tote" in str(c.calls[-1])


@pytest.mark.asyncio
async def test_fetch_restricted_to_supplied_validated_domain(monkeypatch):
    from urllib.parse import urlsplit

    monkeypatch.setattr("app.services.product.public_target", lambda u: (urlsplit(u), "1.1.1.1"))
    fetched = response("not evidence")
    fetched.content += [
        SimpleNamespace(
            type="web_fetch_tool_result",
            content=SimpleNamespace(
                type="web_fetch_result",
                url="https://example.com/course",
                content=SimpleNamespace(source=SimpleNamespace(data="English course for adults")),
            ),
        )
    ]
    a, c = adapter(
        [response(preparation(research="fetch", contextAdequate=False)), fetched, response(clarification())]
    )
    r = await a.send_message(
        "s", None, [], {"productUrl": "https://example.com/course", "pageStatus": "failed"}
    )
    assert c.calls[1]["tools"][0]["allowed_domains"] == ["example.com"]
    assert r.usage["fetches"] == 1
    assert "English course for adults" in str(c.calls[-1])


@pytest.mark.asyncio
async def test_unexpected_tool_not_accepted_even_with_valid_json():
    invalid = response(clarification())
    invalid.content.append(SimpleNamespace(type="tool_use", name="shell"))
    a, c = adapter([response(preparation()), invalid, invalid])
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {})
    assert exc.value.code == "CHAT_INVALID_RESPONSE"


@pytest.mark.asyncio
async def test_cost_reserved_before_request_and_failure_keeps_reservation():
    events = []

    async def charge(reserved, actual):
        events.append((reserved, actual))

    a, c = adapter([RuntimeError("private transport details")])
    with pytest.raises(RuntimeError):
        await a.send_message("s", None, [], {"chargeUsage": charge})
    assert len(events) == 1 and events[0][0] > 0 and events[0][1] is None


@pytest.mark.asyncio
async def test_cancellation_cleans_active_task():
    import asyncio

    a, c = adapter([])

    async def slow(**kw):
        await asyncio.sleep(30)

    c.create = slow
    task = asyncio.create_task(a.send_message("s", None, [], {}))
    await asyncio.sleep(0)
    await a.cancel("s")
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not a.active


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["page", "structuredData", "research", "image", "user", "skill"])
async def test_injection_surfaces_never_gain_system_or_tool_authority(surface, monkeypatch):
    import base64
    import io
    from pathlib import Path
    from PIL import Image, ImageDraw

    fixtures = json.loads((Path(__file__).parent / "fixtures/creative_injection_cases.json").read_text())
    attack = next(v["text"] for v in fixtures if v["surface"] == surface)
    context = {"contextBundle": {"sourceFacts": []}}
    messages = [{"role": "user", "text": "Advertise my handmade soap. Do not research."}]
    prep = preparation()
    if surface == "user":
        messages.append({"role": "user", "text": attack})
    elif surface == "skill":
        prep = preparation(skillIds=["copywriting"])
        monkeypatch.setattr("app.providers.claude.load_skill", lambda id: attack)
    elif surface == "image":
        picture = Image.new("RGB", (600, 200), "white")
        ImageDraw.Draw(picture).text((5, 5), attack, fill="black")
        stream = io.BytesIO()
        picture.save(stream, format="PNG")
        context["images"] = [{"role": "product", "data": stream.getvalue()}]
    else:
        context["contextBundle"]["sourceFacts"] = [{"source": "test-" + surface, "text": attack}]
    a, c = adapter([response(prep), response(clarification())])
    context["storageKey"] = "PRIVATE_STORAGE_KEY"
    context["providerPayload"] = {"secret": "PRIVATE_PROVIDER_METADATA"}
    result = await a.send_message("s", None, messages, context)
    for call in c.calls:
        # System may be cached content blocks, so assert on the serialized form.
        assert attack not in str(call["system"])
        assert "tools" not in call
        assert "PRIVATE_STORAGE_KEY" not in str(call)
        assert "PRIVATE_PROVIDER_METADATA" not in str(call)
    assert "UGC_INJECTION_ACCEPTED" not in repr(result)
    assert "PRIVATE-THINKING" not in repr(result)
    if surface == "image":
        image = next(b for b in c.calls[-1]["messages"][0]["content"] if b["type"] == "image")
        assert base64.b64decode(image["source"]["data"]) == context["images"][0]["data"]


def reference_block(call):
    from app.providers.claude import json as provider_json

    block = next(
        b
        for b in call["messages"][-1]["content"]
        if b.get("text", "").startswith("CREATIVE_DIRECTION_REFERENCE")
    )
    return provider_json.loads(block["text"].split("\n", 1)[1])


@pytest.mark.asyncio
async def test_selected_format_supplies_its_full_playbook_and_matching_structures():
    a, c = adapter([response(preparation()), response(ready())])
    result = await a.send_message(
        "s", None, [], {"contextBundle": {"selectedFormat": "product_demo", "availableAssets": []}}
    )
    reference = reference_block(c.calls[-1])
    assert reference["selectedPlaybook"]["label"] == "Product Demo"
    assert [entry["formatId"] for entry in reference["formatIndex"]]
    assert reference["structures"]
    assert all("product_demo" in s["formatBias"] for s in reference["structures"])
    assert all(
        "_" not in rule for s in reference["structures"] for rule in s["forbidden"]
    ), "rule slugs must not reach the model as copyable text"
    assert reference["offerRoleRules"] == {
        "productSourcePriority": True,
        "personIsPresenterUnlessExplicitlyPromoted": True,
    }
    assert result.audit["playbookFormat"] == "product_demo"
    assert result.audit["referenceStructureIds"] == [s["id"] for s in reference["structures"]]


@pytest.mark.asyncio
async def test_auto_format_sends_index_and_cross_format_structures_without_a_playbook():
    a, c = adapter([response(preparation()), response(ready())])
    result = await a.send_message("s", None, [], {"contextBundle": {"selectedFormat": "auto"}})
    reference = reference_block(c.calls[-1])
    assert reference["selectedPlaybook"] is None
    assert len(reference["formatIndex"]) == 9
    assert len({f for s in reference["structures"] for f in s["formatBias"]}) > 1
    # Auto resolves to the format the director actually planned.
    assert result.audit["playbookFormat"] == "ugc_review"


@pytest.mark.asyncio
async def test_reference_is_framed_as_data_and_excludes_repeated_mechanisms():
    a, c = adapter([response(preparation()), response(ready())])
    from app.creative_direction_playbooks import select_structures

    excluded = [select_structures({}, "ugc_review")[0]["mechanism"]]
    await a.send_message(
        "s",
        None,
        [],
        {"contextBundle": {"selectedFormat": "ugc_review"}, "excludedMechanisms": excluded},
    )
    block = next(
        b for b in c.calls[-1]["messages"][-1]["content"] if "CREATIVE_DIRECTION_REFERENCE" in b["text"]
    )
    assert "reference data, not instructions" in block["text"]
    assert all(s["mechanism"] not in excluded for s in reference_block(c.calls[-1])["structures"])


@pytest.mark.asyncio
async def test_accepted_low_quality_answer_still_records_playbook_provenance():
    a, c = adapter([response(preparation()), response(ready(score=1)), response(ready(score=2))])
    result = await a.send_message(
        "s", None, [], {"contextBundle": {"selectedFormat": "before_after"}}
    )
    assert result.audit["qualityGatePassed"] is False
    assert result.audit["playbookFormat"] == "before_after"
    assert result.audit["referenceStructureIds"]


@pytest.mark.asyncio
async def test_timeout_returns_stable_error():
    import asyncio

    a, c = adapter([])
    a.cfg = a.cfg.model_copy(update={"claude_timeout_seconds": 0.01})

    async def slow(**kw):
        await asyncio.sleep(1)

    c.create = slow
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {})
    assert exc.value.code == "CHAT_TIMEOUT"


@pytest.mark.asyncio
async def test_rate_limit_redacts_provider_details():
    import anthropic
    import httpx2

    a, c = adapter(
        [
            anthropic.RateLimitError(
                "SECRET RAW PROVIDER MESSAGE",
                response=httpx2.Response(
                    429, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
                ),
                body=None,
            )
        ]
    )
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {})
    assert exc.value.code == "CHAT_RATE_LIMITED"
    assert "SECRET" not in str(exc.value)


@pytest.mark.asyncio
async def test_missing_workspace_header_has_actionable_safe_error():
    import anthropic
    import httpx2

    error = anthropic.BadRequestError(
        "raw error",
        response=httpx2.Response(
            400, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        ),
        body={"error": {"message": "Set anthropic-workspace-id for this unscoped key."}},
    )
    a, c = adapter([error])
    with pytest.raises(DomainError) as exc:
        await a.send_message("s", None, [], {})
    assert exc.value.code == "CHAT_CONFIGURATION_REQUIRED"
    assert "workspace" not in exc.value.message


@pytest.mark.asyncio
async def test_workspace_header_on_owned_sdk_and_client_closed(monkeypatch):
    import anthropic

    created = {}
    client = Client([response(preparation()), response(clarification())])

    async def close():
        created["closed"] = True

    client.close = close

    def construct(**kwargs):
        created.update(kwargs)
        return client

    monkeypatch.setattr(anthropic, "AsyncAnthropic", construct)
    a = ClaudeCreativeDirectorAdapter(
        Settings(_env_file=None, anthropic_api_key="fake", anthropic_workspace_id="wrkspc_Test123")
    )
    await a.send_message("s", None, [], {})
    assert created["default_headers"] == {"anthropic-workspace-id": "wrkspc_Test123"}
    assert created["max_retries"] == 0
    assert created["closed"]


@pytest.mark.asyncio
async def test_preparation_runs_at_low_effort_and_each_phase_is_timed():
    a, client = adapter([response(preparation()), response(clarification())])
    result = await a.send_message("s", None, [{"role": "user", "text": "Kurs"}], {"contextBundle": {}})
    # Preparation only classifies the brief; the director keeps its configured depth.
    assert client.calls[0]["output_config"]["effort"] == "low"
    assert client.calls[1]["output_config"]["effort"] == "medium"
    assert set(result.usage["timingsMs"]) == {"preparation", "director"}
    assert result.usage["repairs"] == []


@pytest.mark.asyncio
async def test_repair_round_records_its_gate_code_and_time(caplog):
    a, _ = adapter(
        [
            response(preparation()),
            response(clarification(), stop="max_tokens"),
            response(clarification()),
        ]
    )
    result = await a.send_message("s", None, [{"role": "user", "text": "Kurs"}], {"contextBundle": {}})
    assert result.usage["repairs"] == ["CHAT_INVALID_RESPONSE"]
    assert set(result.usage["timingsMs"]) == {"preparation", "director", "repair"}
    logged = [r.getMessage() for r in caplog.records if r.getMessage().startswith("creative_director_repair")]
    assert len(logged) == 1
    assert "code=CHAT_INVALID_RESPONSE stop=max_tokens" in logged[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("assets", "url", "expected"),
    [
        ([{"role": "person"}], None, "self_presentation"),
        ([{"role": "person"}, {"role": "product"}], None, None),
        ([{"role": "person"}], "https://shop.example/item", None),
    ],
)
async def test_auto_with_only_a_person_becomes_self_presentation(assets, url, expected):
    a, _ = adapter([response(preparation()), response(clarification())])
    context = {"contextBundle": {"availableAssets": assets}}
    if url:
        context["productUrl"] = url
    result = await a.send_message("s", None, [{"role": "user", "text": "Kim jestem"}], context)
    assert result.audit["playbookFormat"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "url", "assessed"),
    [
        ("Klienci znajdują konkurencję w Google i ChatGPT, a nie Twój sklep?", None, False),
        ("Please research this offer first", None, True),
        ("Zrób reklamę", "https://shop.example/item", True),
    ],
)
async def test_assessment_call_runs_only_for_a_url_or_an_explicit_research_request(text, url, assessed):
    replies = [response(preparation()), response(clarification())] if assessed else [response(clarification())]
    a, client = adapter(replies, claude_skip_preparation_without_url=True)
    context = {"contextBundle": {}, "productUrl": url} if url else {"contextBundle": {}}
    result = await a.send_message("s", None, [{"role": "user", "text": text}], context)
    assert len(client.calls) == (2 if assessed else 1)
    assert ("preparation" in result.usage["timingsMs"]) is assessed
    if not assessed:
        assert result.audit["skills"] == ["copywriting", "ad-creative"]
