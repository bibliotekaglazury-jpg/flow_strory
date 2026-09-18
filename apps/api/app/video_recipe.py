"""Canonical planning contract; never accepts arbitrary provider JSON."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=1500)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RecipeScene(StrictModel):
    duration: int = Field(ge=1, le=30)
    description: Text


class SpokenContent(StrictModel):
    required: bool
    language: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", max_length=35)
    dialogue: str = Field(max_length=1500)


class VideoRecipe(StrictModel):
    language: str = Field(default="en", pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", max_length=35)
    spokenContent: SpokenContent | None = None
    intent: Text
    concept: Text
    duration: Literal[15, 20, 30]
    aspectRatio: Literal["9:16", "1:1", "16:9"]
    qualityTier: Literal["auto"]
    subject: Text
    product: Text
    visualStyle: Text
    camera: Text
    performance: Text
    scenes: list[RecipeScene] = Field(min_length=1, max_length=8)
    audio: Text
    constraints: list[Text] = Field(max_length=12)
    negativeRules: list[Text] = Field(max_length=12)

    @model_validator(mode="after")
    def valid_timing(self):
        if self.spokenContent and self.spokenContent.language != self.language:
            raise ValueError("Spoken language must match recipe language")
        if self.spokenContent and self.spokenContent.required and not self.spokenContent.dialogue.strip():
            raise ValueError("Required speech needs dialogue")
        if sum(scene.duration for scene in self.scenes) != self.duration:
            raise ValueError("Scene timings must match video duration")
        return self


class RecipeAnswer(StrictModel):
    assistantMessage: Text
    needsMoreInformation: bool
    clarificationQuestion: Text | None
    recipe: VideoRecipe | None

    @model_validator(mode="after")
    def consistent_answer(self):
        if self.needsMoreInformation:
            if not self.clarificationQuestion or self.recipe is not None:
                raise ValueError("Clarification must have a question and no applicable recipe")
        elif self.recipe is None or self.clarificationQuestion is not None:
            raise ValueError("A ready answer must contain a recipe and no clarification")
        return self


def compile_recipe(recipe: VideoRecipe, context: dict | None = None) -> str:
    lines = [f"Create a {recipe.duration}-second {recipe.aspectRatio} video."]
    for key in ("intent", "concept", "subject", "product", "visualStyle", "camera", "performance", "audio"):
        lines.append(f"{key}: {getattr(recipe, key)}")
    lines.extend(f"Scene {i + 1} ({s.duration}s): {s.description}" for i, s in enumerate(recipe.scenes))
    if recipe.spokenContent:
        lines += [
            f"Spoken language: {recipe.language}. Do not switch languages.",
            f"Exact dialogue: {recipe.spokenContent.dialogue}",
            "Generate synchronized video and native audio in the same output MP4. No separate speech or dubbing.",
        ]
        if not recipe.spokenContent.required:
            lines.append("No spoken dialogue requested; native ambient audio only.")
    if context:
        lines.append("Reference instructions: " + str(context))
    lines.extend(f"Constraint: {v}" for v in recipe.constraints)
    lines.extend(f"Avoid: {v}" for v in recipe.negativeRules)
    lines.append("Preserve supplied product identity and the approved creative direction.")
    # The generator will otherwise restyle a product it recognises — adding or enlarging
    # brand text it "knows" should be there. Stated unconditionally rather than relying on
    # the director to write a fidelity rule every time.
    if "productImageId" in str((context or {}).get("references", "")):
        lines.append(
            "The product must match the supplied product image exactly: identical shape, "
            "proportions, colour, material and finish. Reproduce any logo, brand name or "
            "marking only as it appears there — same size, position and prominence. Never "
            "add, enlarge, restyle, translate or invent branding, text, hardware or "
            "decoration that is not visible in that image."
        )
    text = "\n".join(lines)
    if len(text) > 16000:
        raise ValueError("Recipe exceeds production prompt limit")
    return text
