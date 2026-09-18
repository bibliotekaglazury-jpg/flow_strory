"""Bounded decision records for creative planning; never model reasoning."""

import re
from dataclasses import dataclass, field
from typing import Annotated, Iterable

from pydantic import Field, model_validator

from app.creative_direction import CreativeMechanism, DirectorAnswer
from app.errors import DomainError
from app.video_recipe import RecipeAnswer, StrictModel

Score = Annotated[float, Field(ge=0, le=5)]
QUALITY_VERSION = "creative-quality-v1"
MINIMUM_SCORES = {
    "stoppingPower": 3,
    "relevance": 3,
    "creativeIdea": 3,
    "visualStory": 3,
    "productIntegration": 3,
    "payoff": 3,
    "distinctiveness": 3,
    "feasibility": 3,
}
MINIMUM_MEAN_SCORE = 3.5


class QualityScores(StrictModel):
    stoppingPower: Score
    relevance: Score
    creativeIdea: Score
    visualStory: Score
    productIntegration: Score
    payoff: Score
    distinctiveness: Score
    feasibility: Score


class CreativeCandidateAudit(StrictModel):
    id: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    summary: str = Field(min_length=1, max_length=300)
    mechanism: CreativeMechanism
    scores: QualityScores


class CreativeAudit(StrictModel):
    candidates: list[CreativeCandidateAudit] = Field(min_length=3, max_length=3)
    selectedId: str = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def distinct_candidates(self):
        ids = [candidate.id for candidate in self.candidates]
        mechanisms = [candidate.mechanism for candidate in self.candidates]
        if len(set(ids)) != len(ids) or self.selectedId not in ids:
            raise ValueError("Candidates need unique IDs and one selected candidate")
        if len(set(mechanisms)) != len(mechanisms):
            raise ValueError("Candidate mechanisms must be distinct")
        return self


class DirectorEnvelope(StrictModel):
    answer: DirectorAnswer
    audit: CreativeAudit | None

    @model_validator(mode="after")
    def consistent_audit(self):
        if self.answer.assessment == "clarification_needed":
            if self.audit is not None:
                raise ValueError("Clarification must have no candidate audit")
        else:
            if self.audit is None or not self.answer.creativePlan.creativeMechanism:
                raise ValueError("Ready Claude answers require a mechanism and candidate audit")
            selected = next(c for c in self.audit.candidates if c.id == self.audit.selectedId)
            if selected.mechanism != self.answer.creativePlan.creativeMechanism:
                raise ValueError("Selected mechanism must match the creative plan")
        return self


def validate_quality(envelope: DirectorEnvelope, excluded_mechanisms: Iterable[str] = ()) -> None:
    if envelope.audit is None:
        return
    selected = next(c for c in envelope.audit.candidates if c.id == envelope.audit.selectedId)
    if selected.mechanism in set(excluded_mechanisms):
        raise DomainError(
            "CREATIVE_MECHANISM_REPEATED", "The new concept repeats a previous mechanism.", 422, True
        )
    scores = selected.scores.model_dump()
    if any(scores[key] < minimum for key, minimum in MINIMUM_SCORES.items()) or (
        sum(scores.values()) / len(scores) < MINIMUM_MEAN_SCORE
    ):
        raise DomainError(
            "CREATIVE_QUALITY_LOW", "The proposed concept did not meet the creative quality threshold.", 422, True
        )


# A buyer/B2B audience text (evaluating or purchasing an offer) paired with a spoken
# line that books a clinic appointment or exam is the exact device-vs-service confusion
# the person/product role rule exists to prevent; catch it deterministically, since one
# more paragraph of prompt instruction was already insufficient (2026-09-12 eval, case 9).
BUYER_AUDIENCE_PATTERN = re.compile(
    r"zakup|kupi[cć]|kupno|nabyc|własny sprzęt|swój sprzęt|"
    r"rozważając(y)? (zakup|własny sprzęt)|purchas|\bbuy(ing)?\b|"
    r"considering (a )?purchase|owning (a |the )?device",
    re.IGNORECASE,
)
APPOINTMENT_CTA_PATTERN = re.compile(
    r"recepcj|umów\w* wizyt|zapisz\w* się na wizyt|zarezerwuj\w* wizyt|"
    r"wizytę (u nas|w gabinecie)|book an? appointment|"
    r"schedule an? (exam|appointment|consultation)|book a (consultation|session|exam)",
    re.IGNORECASE,
)


def validate_offer_role(envelope: DirectorEnvelope) -> None:
    """Deterministic guard: a buyer/B2B audience must not be handed a clinic-booking CTA."""
    plan = envelope.answer.creativePlan
    video = envelope.answer.videoPlan
    if not plan or not video or not video.clips:
        return
    audience_text = f"{plan.audience} {plan.objective}"
    script = video.clips[0].spokenScript
    if BUYER_AUDIENCE_PATTERN.search(audience_text) and APPOINTMENT_CTA_PATTERN.search(script):
        raise DomainError(
            "CREATIVE_OFFER_ROLE_MISMATCH",
            "The call to action must address the stated buyer audience and offer, "
            "not a clinic appointment or medical exam.",
            422,
            True,
        )


# Documented AI-tell hedge-opener/filler phrasing ("it's worth noting" and its Polish
# register equivalent "warto zauważyć/to sprawdzić..."). Source: the real, MIT-licensed
# Aboudjem/humanizer-skill vocabulary list (cli/lib/vocabulary.js PHRASES, pinned commit
# a58df065367550b6ce40ff3f648335018d8e0589) — not an invented category. Caught live on
# 2026-09-12: "Warto to sprawdzić do swojego gabinetu" read as templated ad phrasing, not
# a rewritten slogan/antithesis, so the existing v3.py rule didn't cover it.
AI_TELL_PATTERNS = re.compile(
    r"\bdelv\w*|\btapestry\b|\btestament\b|\bunderscor\w*|\bleverag\w*|\bmultifaceted\b|"
    r"\brealm\b|\binterplay\b|\bseamless\w*|\bgroundbreaking\b|"
    r"it'?s worth noting|it is worth noting|it is important to note|"
    r"in today'?s|rapidly evolving|cutting-edge|push(es|ing)? the boundaries|"
    r"\bwarto (zauważyć|zauwazyc|wspomnieć|wspomniec|podkreślić|podkreslic|"
    r"zaznaczyć|zaznaczyc|dodać|dodac|"
    r"(to )?(sprawdzić|sprawdzic|zobaczyć|zobaczyc|wypróbować|wyprobowac))\b",
    re.IGNORECASE,
)


def validate_requested_ratio(envelope: DirectorEnvelope, requested: str | None) -> None:
    """The frame the user picked is a requirement, not a hint.

    selectedFormat has been enforced in compile_plan since the start; aspectRatio was
    only ever passed as evidence, so nothing stopped a plan from coming back in a
    different frame than the one chosen in the UI.
    """
    video = envelope.answer.videoPlan
    if not video or not requested:
        return
    if video.aspectRatio != requested:
        raise DomainError(
            "CREATIVE_RATIO_MISMATCH",
            "The plan must use the aspect ratio selected for this video.",
            422,
            True,
        )


def validate_requested_language(envelope: DirectorEnvelope, requested: str | None) -> None:
    """The language the user picked is a requirement, not something to infer.

    Without an explicit signal the director reads language from the brief text — which
    fails when there is no real brief, e.g. Auto mode's filler message, silently
    defaulting to English regardless of what the user actually wants.
    """
    video = envelope.answer.videoPlan
    if not video or not requested:
        return
    if not video.spokenLanguage.startswith(requested):
        raise DomainError(
            "CREATIVE_LANGUAGE_MISMATCH",
            "The plan must be spoken in the language selected for this video.",
            422,
            True,
        )


def validate_preferred_mechanism(envelope: DirectorEnvelope, requested: str | None) -> None:
    """Recreate reuses a mechanism that already worked, on a different offer.

    Only the mechanism carries over: every fact, script line and CTA is written fresh
    from the new request's own evidence, so this checks the slug and nothing else.
    """
    creative = envelope.answer.creativePlan
    if not creative or not requested:
        return
    if creative.creativeMechanism != requested:
        raise DomainError(
            "CREATIVE_MECHANISM_MISMATCH",
            "The plan must use the creative mechanism selected for this video.",
            422,
            True,
        )


def validate_spoken_register(envelope: DirectorEnvelope) -> None:
    """Deterministic guard against documented AI-tell phrasing in the spoken line."""
    video = envelope.answer.videoPlan
    if not video or not video.clips:
        return
    script = video.clips[0].spokenScript
    if AI_TELL_PATTERNS.search(script):
        raise DomainError(
            "CREATIVE_DIALOGUE_AI_TELL",
            "The spoken line uses generic templated phrasing instead of natural speech.",
            422,
            True,
        )


@dataclass
class ChatProviderResult:
    thread_id: str | None
    answer: DirectorAnswer | RecipeAnswer
    audit: dict | None = None
    usage: dict = field(default_factory=dict)

    def __iter__(self):
        """Keep existing provider callers compatible during the adapter transition."""
        yield self.thread_id
        yield self.answer
