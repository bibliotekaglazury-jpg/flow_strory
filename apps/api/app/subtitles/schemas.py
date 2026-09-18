"""Request bodies for the Subtitle Studio API; response shapes live in app/responses.py."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MIN_CUE_MS = 250


class SubtitleWordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=200)
    startMs: int = Field(ge=0)
    endMs: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.endMs <= self.startMs:
            raise ValueError("A word's endMs must be after its startMs")
        return self


class SubtitleCueIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    startMs: int = Field(ge=0)
    endMs: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=2000)
    words: list[SubtitleWordIn] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def bounded(self):
        if self.endMs - self.startMs < MIN_CUE_MS:
            raise ValueError(f"A cue must be at least {MIN_CUE_MS}ms long")
        return self


class SubtitleStyleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preset: Literal["modern", "classic", "impact", "editorial"]
    position: Literal["top", "center", "bottom"]
    size: Literal["small", "medium", "large"]
    safeArea: bool
    textColor: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    highlightColor: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class SubtitleProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sourceAssetId: str
    aspectRatio: Literal["9:16", "16:9"]


class SubtitleProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    aspectRatio: Literal["9:16", "16:9"]
    # An hour of speech is roughly a thousand short captions; leave generous headroom.
    cues: list[SubtitleCueIn] = Field(max_length=5000)
    style: SubtitleStyleIn

    @model_validator(mode="after")
    def cues_ordered_and_disjoint(self):
        previous_end = None
        for cue in self.cues:
            if not cue.text.strip():
                raise ValueError("Cues cannot be empty")
            if previous_end is not None and cue.startMs < previous_end:
                raise ValueError("Cues must be ordered and non-overlapping")
            previous_end = cue.endMs
        return self


class SubtitleExportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
