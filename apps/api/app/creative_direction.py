"""Provider-neutral 15-second planning contracts. No provider payloads or reasoning."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.video_recipe import StrictModel, Text, VideoRecipe, RecipeScene, SpokenContent, RecipeAnswer

Format = Literal[
    "ugc_review",
    "product_unboxing",
    "problem_solution",
    "product_demo",
    "testimonial",
    "trending_style",
    "hook_cta",
    "before_after",
    "self_presentation",
]
FORMAT_BIASES = {
    "auto": "Choose the most useful format for this offer and objective.",
    "ugc_review": "First-person perspective, authentic conversational voice, natural performance, low advertising tone.",
    "product_unboxing": "Discovery and reveal, anticipation, first-use feeling; adapt to the actual offer.",
    "problem_solution": "Recognizable friction and a natural introduction of the offer as resolution.",
    "product_demo": "Demonstration over explanation; make how the offer works clear.",
    "testimonial": "Personal perspective and credibility; never invent factual customer experiences or claims.",
    "trending_style": "Contemporary social rhythm appropriate to the audience, without arbitrary effects.",
    "hook_cta": "Earn attention early and finish with one clear action.",
    "before_after": "Visible contrast or state change; no impossible or fabricated outcomes.",
    "self_presentation": "The person on camera is the offer: they present themselves and their own service in first person.",
}

CreativeMechanism = Annotated[
    str, Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
]


class PriorConcept(StrictModel):
    revision: int = Field(default=0, ge=0)
    contextFingerprint: str = Field(default="", max_length=128)
    mechanism: CreativeMechanism | None
    summary: Text
    status: Literal["selected", "rejected"] = "selected"


class SourceFact(StrictModel):
    source: str = Field(max_length=2048)
    text: str = Field(max_length=24000)


class AssetContext(StrictModel):
    id: str
    role: str
    mimeType: str
    width: int | None
    height: int | None
    durationSeconds: float | None
    # Present for the pieces of a multi-item look ("sunglasses", "scarf"); the role of
    # every one of them is still "product".
    label: str | None = None


class ContextBundle(StrictModel):
    version: Literal["1"] = "1"
    userText: str = Field(max_length=4000)
    brief: str = Field(max_length=4000)
    productUrl: str | None
    offer: Text | None = None
    product: Text | None = None
    service: Text | None = None
    audience: Text | None = None
    objective: Text | None = None
    benefits: list[Text] = Field(default_factory=list, max_length=12)
    differentiators: list[Text] = Field(default_factory=list, max_length=12)
    proof: list[Text] = Field(default_factory=list, max_length=12)
    CTA: Text | None = None
    brandTone: Text | None = None
    availableAssets: list[AssetContext]
    selectedFormat: Literal["auto"] | Format
    aspectRatio: Literal["9:16", "1:1", "16:9"]
    # BCP-47 primary subtag (e.g. "pl", "en"); None lets the director infer from the
    # brief, as before. Set explicitly so spoken language is a user decision, not a guess
    # from whatever filler text a caller (like Auto mode) happened to send.
    requestedLanguage: str | None = Field(default=None, pattern=r"^[a-z]{2,3}$")
    # Recreate: reuse the creative mechanism that already worked, on a different offer.
    # The opposite of excludedMechanisms, which forbids repeats.
    preferredMechanism: CreativeMechanism | None = None
    sourceFacts: list[SourceFact]
    missingFacts: list[Text] = Field(default_factory=list, max_length=12)
    conversation: list[dict[str, str]]
    priorConcepts: list[PriorConcept] = Field(default_factory=list, max_length=24)


class CreativePlan(StrictModel):
    creativeMechanism: CreativeMechanism | None = None
    objective: Text
    audience: Text
    offer: Text
    coreTension: Text
    creativeAngle: Text
    selectedFormat: Format
    hookStrategy: Literal[
        "verbal",
        "visual",
        "situational",
        "emotional",
        "curiosity",
        "contradiction",
        "demonstration",
        "pattern_interrupt",
    ]
    tone: Text
    visualMode: Text
    language: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    spokenLanguage: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    characterConcepts: list[Text] = Field(max_length=3)
    productPresentation: Text
    audioDirection: Text
    # Labels of the supplied look items this concept actually puts on screen. Declared by
    # the director so a quietly dropped item is visible instead of silent.
    featuredItems: list[Text] = Field(default_factory=list, max_length=4)
    confidence: float = Field(ge=0, le=1)


class Beat(StrictModel):
    start: float = Field(ge=0, lt=15)
    end: float = Field(gt=0, le=15)
    purpose: Text
    action: Text


class AudioDirection(StrictModel):
    native: Literal[True]
    speechRequired: bool
    voiceTone: Text
    ambience: Text
    music: Text | None


class ClipPlan(StrictModel):
    start: Literal[0]
    end: Literal[15]
    role: Text
    narrativePurpose: Text
    visualDirection: Text
    spokenScript: str = Field(max_length=1500)
    camera: Text
    performance: Text
    audio: AudioDirection
    beats: list[Beat] = Field(max_length=5)

    @model_validator(mode="after")
    def timing(self):
        previous = 0
        for beat in self.beats:
            if beat.start < previous or beat.end <= beat.start:
                raise ValueError("Beats must be ordered and non-overlapping")
            previous = beat.end
        if self.audio.speechRequired != bool(self.spokenScript.strip()):
            raise ValueError("Speech direction must match the script")
        return self


class VideoPlan(StrictModel):
    duration: Literal[15]
    aspectRatio: Literal["9:16", "1:1", "16:9"]
    language: str
    spokenLanguage: str
    continuity: Text
    characters: list[Text] = Field(max_length=3)
    productRules: list[Text] = Field(max_length=5)
    constraints: list[Text] = Field(max_length=6)
    negativeRules: list[Text] = Field(max_length=12)
    clips: list[ClipPlan] = Field(min_length=1, max_length=1)


class DirectorAnswer(StrictModel):
    assistantMessage: Text
    assessment: Literal["enough_to_plan", "clarification_needed"]
    clarificationQuestion: Text | None
    creativePlan: CreativePlan | None
    videoPlan: VideoPlan | None

    @model_validator(mode="after")
    def consistency(self):
        if self.assessment == "clarification_needed":
            if not self.clarificationQuestion or self.creativePlan or self.videoPlan:
                raise ValueError("Ask one question without an applicable plan")
        else:
            if self.clarificationQuestion or not self.creativePlan or not self.videoPlan:
                raise ValueError("A ready concept needs both plans")
            if (self.creativePlan.language, self.creativePlan.spokenLanguage) != (
                self.videoPlan.language,
                self.videoPlan.spokenLanguage,
            ):
                raise ValueError("Plan languages must agree")
        return self


CanonicalVideoRecipe = VideoRecipe


def compile_plan(context: ContextBundle, creative: CreativePlan, video: VideoPlan) -> VideoRecipe:
    """CanonicalVideoRecipe reuses the existing validated VideoRecipe domain."""
    if context.selectedFormat != "auto" and creative.selectedFormat != context.selectedFormat:
        raise ValueError("The director must preserve the selected format")
    if video.aspectRatio != context.aspectRatio:
        raise ValueError("The director must preserve the selected aspect ratio")
    if context.requestedLanguage and not video.spokenLanguage.startswith(context.requestedLanguage):
        raise ValueError("The director must preserve the selected spoken language")
    if (creative.language, creative.spokenLanguage) != (video.language, video.spokenLanguage):
        raise ValueError("Plan languages must agree")
    clip = video.clips[0]
    audio = clip.audio
    return VideoRecipe(
        intent=creative.objective,
        concept=creative.creativeAngle,
        duration=15,
        aspectRatio=video.aspectRatio,
        language=video.spokenLanguage,
        qualityTier="auto",
        spokenContent=SpokenContent(
            required=audio.speechRequired, language=video.spokenLanguage, dialogue=clip.spokenScript
        ),
        subject="; ".join(video.characters) or "No on-screen character",
        product=creative.productPresentation,
        visualStyle=creative.visualMode,
        camera=clip.camera,
        performance=clip.performance,
        scenes=[
            RecipeScene(
                duration=15,
                description=clip.visualDirection
                + (
                    "\n" + "\n".join(f"{b.start:g}–{b.end:g}s: {b.action}" for b in clip.beats)
                    if clip.beats
                    else ""
                ),
            )
        ],
        audio=(
            f"Native audio. Voice: {audio.voiceTone}. Ambience: {audio.ambience}. "
            # The generator mixes the whole track itself, so the level relationship has to
            # be stated in words: left to itself it either buries the music or lets it
            # fight the dialogue.
            + (
                (
                    f"Music: {audio.music}. Keep the music a background bed under the voice — "
                    "audible but clearly quieter than the dialogue, never masking a word, and "
                    "never rising over the speech."
                    if audio.speechRequired
                    # Without dialogue there is nothing to sit under: the same "keep it
                    # quieter" wording made the generator drop the requested track
                    # altogether and deliver room noise only.
                    else f"Music: {audio.music}. There is no dialogue, so the music is the "
                    "main audio layer: play it clearly and continuously at a comfortable "
                    "listening level, with the ambience mixed quietly underneath it."
                )
                if audio.music
                else "Music: none. Do not add any music track."
            )
        ),
        constraints=[video.continuity, *video.productRules, *video.constraints],
        negativeRules=video.negativeRules,
    )


class PlannedAnswer(RecipeAnswer):
    creativePlan: CreativePlan | None = None
    videoPlan: VideoPlan | None = None


def normalize_answer(answer: DirectorAnswer, context: ContextBundle) -> PlannedAnswer:
    return PlannedAnswer(
        assistantMessage=answer.assistantMessage,
        needsMoreInformation=answer.assessment == "clarification_needed",
        clarificationQuestion=answer.clarificationQuestion,
        recipe=compile_plan(context, answer.creativePlan, answer.videoPlan)
        if answer.creativePlan and answer.videoPlan
        else None,
        creativePlan=answer.creativePlan,
        videoPlan=answer.videoPlan,
    )
