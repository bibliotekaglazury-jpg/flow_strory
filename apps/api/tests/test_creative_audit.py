"""Offline contract and deterministic quality-gate coverage."""

import copy

import pytest
from pydantic import ValidationError

from app.creative_audit import (
    ChatProviderResult,
    DirectorEnvelope,
    MINIMUM_SCORES,
    validate_offer_role,
    validate_preferred_mechanism,
    validate_quality,
    validate_requested_language,
    validate_requested_ratio,
    validate_spoken_register,
)
from app.creative_direction import ContextBundle, DirectorAnswer, PriorConcept
from app.errors import DomainError


@pytest.fixture
def payload():
    return {
        "answer": {
            "assistantMessage": "A strong concept is ready.",
            "assessment": "enough_to_plan",
            "clarificationQuestion": None,
            "creativePlan": {
                "creativeMechanism": "unexpected-comparison",
                "objective": "Introduce the offer", "audience": "Adults", "offer": "Language lessons",
                "coreTension": "Hesitation to speak", "creativeAngle": "Turn a hesitation into a conversation",
                "selectedFormat": "product_demo", "hookStrategy": "situational", "tone": "Warm",
                "visualMode": "Natural", "language": "en", "spokenLanguage": "en",
                "characterConcepts": [], "productPresentation": "A lesson", "audioDirection": "Native voice",
                "confidence": 0.8,
            },
            "videoPlan": {
                "duration": 15, "aspectRatio": "9:16", "language": "en", "spokenLanguage": "en",
                "continuity": "One scene", "characters": [], "productRules": [], "constraints": [],
                "negativeRules": [],
                "clips": [{
                    "start": 0, "end": 15, "role": "main", "narrativePurpose": "Show the lesson",
                    "visualDirection": "A lesson begins", "spokenScript": "Try your first lesson.",
                    "camera": "Medium shot", "performance": "Warm", "beats": [],
                    "audio": {"native": True, "speechRequired": True, "voiceTone": "Warm",
                              "ambience": "Quiet room", "music": None},
                }],
            },
        },
        "audit": {
            "candidates": [
                {"id": f"c{index}", "summary": f"Concept {index}", "mechanism": mechanism,
                 "scores": {key: 4 for key in MINIMUM_SCORES}}
                for index, mechanism in enumerate(
                    ["unexpected-comparison", "reversed-expectation", "visible-progress"]
                )
            ],
            "selectedId": "c0",
        },
    }


def test_offer_role_gate_catches_the_2026_09_12_case_9_regression(payload):
    # Live eval finding: audience says "doctors considering buying their own device",
    # but the CTA invited patients to book an exam at the presenter's clinic.
    payload["answer"]["creativePlan"]["audience"] = (
        "Lekarze i właściciele małych gabinetów medycznych rozważający własny sprzęt USG"
    )
    payload["answer"]["videoPlan"]["clips"][0]["spokenScript"] = (
        "Teraz aparat mam tu, na miejscu. Zapytajcie w recepcji o badanie USG u nas."
    )
    envelope = DirectorEnvelope.model_validate(payload)
    with pytest.raises(DomainError) as exc:
        validate_offer_role(envelope)
    assert exc.value.code == "CREATIVE_OFFER_ROLE_MISMATCH"


@pytest.mark.parametrize(
    "audience,script",
    [
        # Legitimate device purchase: buyer language, no clinic-booking CTA.
        (
            "Lekarze i technicy szukający mobilnego sprzętu diagnostycznego",
            "Teraz biorę to i mam obraz w minutę. Zobaczcie sami na stronie.",
        ),
        # Legitimate local service ad: appointment CTA, but no buyer/purchase audience.
        (
            "Osoby zestresowane szukające chwili odprężenia, lokalni klienci",
            "Chodź, rozluźnijmy to razem. Umów wizytę, link w bio.",
        ),
    ],
)
def test_offer_role_gate_requires_both_signals(payload, audience, script):
    payload["answer"]["creativePlan"]["audience"] = audience
    payload["answer"]["videoPlan"]["clips"][0]["spokenScript"] = script
    envelope = DirectorEnvelope.model_validate(payload)
    validate_offer_role(envelope)  # must not raise


def test_offer_role_gate_ignores_clarification_turns():
    envelope = DirectorEnvelope.model_validate(
        {
            "answer": {
                "assistantMessage": "Co reklamujemy?",
                "assessment": "clarification_needed",
                "clarificationQuestion": "Co reklamujemy?",
                "creativePlan": None,
                "videoPlan": None,
            },
            "audit": None,
        }
    )
    validate_offer_role(envelope)  # must not raise


# 10 cases across niches/languages, per the 2026-09-12 finding that "Warto to sprawdzić
# do swojego gabinetu" (a Polish "it's worth noting"-class hedge-opener) slipped through
# the existing slogan/antithesis prompt rule. Pattern source: the real, MIT-licensed
# Aboudjem/humanizer-skill vocabulary list (cli/lib/vocabulary.js PHRASES), not invented.
AI_TELL_CASES = [
    ("beauty_device_pl", "Warto to sprawdzić do swojego gabinetu.", True),
    ("saas_pl", "Warto zauważyć, że NextFlow uzupełnia dane z GUS automatycznie.", True),
    ("course_pl", "Warto wspomnieć, że lekcje odbywają się wieczorami.", True),
    ("ecommerce_en", "It is worth noting that this device saves you time every morning.", True),
    ("gadget_en", "This is a cutting-edge solution for people who hate slow mornings.", True),
    ("tourism_en", "Let us delve into what makes this food tour worth booking.", True),
    ("massage_pl", "Warto podkreślić, że każdy masaż jest dopasowany do klienta.", True),
    ("local_service_pl", "Znowu bolą Cię plecy po całym dniu? Umów się do mnie na Ursusie.", False),
    ("ecommerce_pl_legit", "Nogi ciążyły mi po całym dniu, a po piętnastu minutach czuję ulgę.", False),
    ("tourism_en_legit", "I got to Krakow this morning with zero idea what to eat here.", False),
]


@pytest.mark.parametrize("label,script,should_raise", AI_TELL_CASES, ids=[c[0] for c in AI_TELL_CASES])
def test_spoken_register_gate_across_niches_and_languages(payload, label, script, should_raise):
    payload["answer"]["videoPlan"]["clips"][0]["spokenScript"] = script
    envelope = DirectorEnvelope.model_validate(payload)
    if should_raise:
        with pytest.raises(DomainError) as exc:
            validate_spoken_register(envelope)
        assert exc.value.code == "CREATIVE_DIALOGUE_AI_TELL"
    else:
        validate_spoken_register(envelope)  # must not raise


def test_spoken_register_gate_ignores_clarification_turns():
    envelope = DirectorEnvelope.model_validate(
        {
            "answer": {
                "assistantMessage": "Co reklamujemy?",
                "assessment": "clarification_needed",
                "clarificationQuestion": "Co reklamujemy?",
                "creativePlan": None,
                "videoPlan": None,
            },
            "audit": None,
        }
    )
    validate_spoken_register(envelope)  # must not raise


@pytest.mark.parametrize("requested,should_raise", [("9:16", False), ("16:9", True), ("1:1", True)])
def test_selected_aspect_ratio_is_enforced_not_merely_suggested(payload, requested, should_raise):
    # selectedFormat was always enforced in compile_plan; aspectRatio was only evidence,
    # so a plan could come back in a frame the user never chose.
    assert payload["answer"]["videoPlan"]["aspectRatio"] == "9:16"
    envelope = DirectorEnvelope.model_validate(payload)
    if should_raise:
        with pytest.raises(DomainError) as exc:
            validate_requested_ratio(envelope, requested)
        assert exc.value.code == "CREATIVE_RATIO_MISMATCH"
    else:
        validate_requested_ratio(envelope, requested)


def test_ratio_gate_skips_clarification_turns_and_unknown_requests(payload):
    clarification = DirectorEnvelope.model_validate(
        {
            "answer": {
                "assistantMessage": "Co reklamujemy?",
                "assessment": "clarification_needed",
                "clarificationQuestion": "Co reklamujemy?",
                "creativePlan": None,
                "videoPlan": None,
            },
            "audit": None,
        }
    )
    validate_requested_ratio(clarification, "16:9")  # no plan to check
    validate_requested_ratio(DirectorEnvelope.model_validate(payload), None)  # nothing requested


@pytest.mark.parametrize(
    "requested,spoken,should_raise",
    [("pl", "pl-PL", False), ("en", "pl-PL", True), (None, "pl-PL", False)],
)
def test_selected_language_is_enforced_not_inferred(payload, requested, spoken, should_raise):
    # Auto mode sends filler English text with no real brief, so without an explicit
    # signal the director defaults to English regardless of what the user picked.
    payload["answer"]["videoPlan"]["spokenLanguage"] = spoken
    payload["answer"]["videoPlan"]["language"] = spoken
    payload["answer"]["creativePlan"]["language"] = spoken
    payload["answer"]["creativePlan"]["spokenLanguage"] = spoken
    envelope = DirectorEnvelope.model_validate(payload)
    if should_raise:
        with pytest.raises(DomainError) as exc:
            validate_requested_language(envelope, requested)
        assert exc.value.code == "CREATIVE_LANGUAGE_MISMATCH"
    else:
        validate_requested_language(envelope, requested)


@pytest.mark.parametrize(
    "requested,should_raise",
    [(None, False), ("unexpected-comparison", False), ("reversed-expectation", True)],
)
def test_recreate_pins_the_mechanism_and_nothing_else(payload, requested, should_raise):
    envelope = DirectorEnvelope.model_validate(payload)
    if should_raise:
        with pytest.raises(DomainError) as exc:
            validate_preferred_mechanism(envelope, requested)
        assert exc.value.code == "CREATIVE_MECHANISM_MISMATCH"
    else:
        validate_preferred_mechanism(envelope, requested)


def test_ready_envelope_and_tuple_transition(payload):
    envelope = DirectorEnvelope.model_validate(payload)
    validate_quality(envelope)
    result = ChatProviderResult("thread", envelope.answer, envelope.audit.model_dump())
    thread, answer = result
    assert thread == "thread" and answer is envelope.answer and result.usage == {}
    other = ChatProviderResult(None, answer)
    result.usage["inputTokens"] = 2
    assert other.usage == {}


@pytest.mark.parametrize(
    "change",
    ["mechanism", "audit", "duplicate", "selected", "mismatch", "reasoning", "count", "extra"],
)
def test_envelope_rejects_invalid_decision_records(payload, change):
    if change == "mechanism":
        del payload["answer"]["creativePlan"]["creativeMechanism"]
    elif change == "audit":
        payload["audit"] = None
    elif change == "duplicate":
        payload["audit"]["candidates"][1]["mechanism"] = "unexpected-comparison"
    elif change == "selected":
        payload["audit"]["selectedId"] = "missing"
    elif change == "mismatch":
        payload["answer"]["creativePlan"]["creativeMechanism"] = "something-else"
    elif change == "reasoning":
        payload["audit"]["candidates"][0]["reasoning"] = "private scratchpad"
    elif change == "extra":
        fourth = {**payload["audit"]["candidates"][0], "id": "4", "mechanism": "fourth-mechanism"}
        payload["audit"]["candidates"].append(fourth)
    else:
        payload["audit"]["candidates"].pop()
    with pytest.raises(ValidationError):
        DirectorEnvelope.model_validate(payload)


@pytest.mark.parametrize("value", ["", "A mechanism", "-bad", "x" * 81])
def test_mechanism_identifier_validation(payload, value):
    payload["answer"]["creativePlan"]["creativeMechanism"] = value
    with pytest.raises(ValidationError):
        DirectorAnswer.model_validate(payload["answer"])


def test_old_saved_answers_and_context_remain_valid(payload):
    del payload["answer"]["creativePlan"]["creativeMechanism"]
    assert DirectorAnswer.model_validate(payload["answer"]).creativePlan.creativeMechanism is None
    context = ContextBundle(
        userText="Lesson", brief="", productUrl=None, availableAssets=[], selectedFormat="auto",
        aspectRatio="9:16", sourceFacts=[], conversation=[],
    )
    assert context.priorConcepts == []
    prior = PriorConcept(mechanism="unexpected-comparison", summary="A comparison")
    assert prior.revision == 0 and prior.contextFingerprint == "" and prior.status == "selected"


@pytest.mark.parametrize("scores", [{key: 3 for key in MINIMUM_SCORES}, {**dict.fromkeys(MINIMUM_SCORES, 5), "payoff": 2}])
def test_selected_candidate_must_pass_all_thresholds(payload, scores):
    payload["audit"]["candidates"][0]["scores"] = scores
    with pytest.raises(DomainError) as caught:
        validate_quality(DirectorEnvelope.model_validate(payload))
    assert caught.value.code == "CREATIVE_QUALITY_LOW" and caught.value.retryable


def test_quality_threshold_boundary_and_score_bounds(payload):
    payload["audit"]["candidates"][0]["scores"] = dict.fromkeys(MINIMUM_SCORES, 3.5)
    validate_quality(DirectorEnvelope.model_validate(payload))
    for value in [-1, 6, True, "4", float("nan")]:
        invalid = copy.deepcopy(payload)
        invalid["audit"]["candidates"][0]["scores"]["relevance"] = value
        with pytest.raises(ValidationError):
            DirectorEnvelope.model_validate(invalid)


def test_only_explicit_exclusion_rejects_selected_mechanism(payload):
    envelope = DirectorEnvelope.model_validate(payload)
    validate_quality(envelope)
    with pytest.raises(DomainError) as caught:
        validate_quality(envelope, ["unexpected-comparison"])
    assert caught.value.code == "CREATIVE_MECHANISM_REPEATED"
    validate_quality(envelope, ["reversed-expectation"])


def test_clarification_requires_null_audit(payload):
    clarification = {
        "assistantMessage": "What offer?", "assessment": "clarification_needed",
        "clarificationQuestion": "What offer?", "creativePlan": None, "videoPlan": None,
    }
    validate_quality(DirectorEnvelope(answer=DirectorAnswer(**clarification), audit=None))
    with pytest.raises(ValidationError):
        DirectorEnvelope.model_validate({"answer": clarification, "audit": payload["audit"]})
