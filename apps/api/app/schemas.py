from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Product images shown together as one look. Five is the compositing model's documented
# identity-preservation range, not an arbitrary UI number.
LOOK_SIZE = 5


class ItemInput(BaseModel):
    """One piece of a multi-item look; the asset itself is an ordinary product image.

    The label lives only in the request, never on the Asset row: keeping the stored role
    as "product" means no new upload path, no role enum and no migration.
    """

    model_config = ConfigDict(extra="forbid")
    assetId: str
    label: str = Field(min_length=1, max_length=40, pattern=r"\S")


class InputAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    productImageId: str | None = None
    personImageId: str | None = None
    sourceVideoId: str | None = None
    # Additional pieces shown together with productImageId, e.g. glasses plus a scarf.
    items: list[ItemInput] = Field(default_factory=list, max_length=LOOK_SIZE)

    @model_validator(mode="after")
    def distinct_images(self):
        ids = [item.assetId for item in self.items]
        if self.productImageId:
            ids.append(self.productImageId)
        if len(set(ids)) != len(ids):
            raise ValueError("Each look item must be a distinct image")
        # productImageId is the first piece of the look, so the whole set is capped here
        # rather than letting items add one more product image behind it.
        if len(ids) > LOOK_SIZE:
            raise ValueError(f"A look holds at most {LOOK_SIZE} product images")
        return self


class TryOn(BaseModel):
    """A still preview of the supplied look, or the same look from another angle."""

    model_config = ConfigDict(extra="forbid")
    inputAssets: InputAssets
    # A still photo can use 4:5 (Gemini 3 Pro Image supports it); video cannot, so this
    # is intentionally one value wider than Creative/Estimate's aspectRatio.
    aspectRatio: Literal["9:16", "1:1", "16:9", "4:5"] = "9:16"
    angle: Literal["front", "three_quarter", "back", "detail"] | None = None
    # Set to re-shoot an approved preview; the caller supplies it so a retried request
    # cannot be charged twice.
    baseAssetId: str | None = None
    idempotencyKey: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    # The project folder this photo belongs to, so it survives a page reload.
    projectId: str | None = None


class LookProjectCreate(BaseModel):
    """One generation's folder: what was shot and how, before the first photo."""

    model_config = ConfigDict(extra="forbid")
    inputAssets: InputAssets
    scene: Literal["studio", "lifestyle", "outdoor", "custom"]
    aspectRatio: Literal["9:16", "1:1", "16:9", "4:5"]


class Creative(BaseModel):
    language: str | None = Field(default=None, max_length=35)
    model_config = ConfigDict(extra="forbid")
    productUrl: str | None = None
    inputAssets: InputAssets
    templateId: str
    brief: str = Field(default="", max_length=4000)
    normalizedInputs: dict | None = None
    duration: Literal[15, 20, 30]
    aspectRatio: Literal["9:16", "1:1", "16:9"]

    @model_validator(mode="after")
    def required_product(self):
        from app.services.templates import is_remotion

        if self.templateId != "auto" and is_remotion(self.templateId):
            return self
        if not self.brief.strip():
            raise ValueError("Brief required")
        return self


class Estimate(BaseModel):
    normalizedInputs: dict | None = None
    model_config = ConfigDict(extra="forbid")
    templateId: str
    duration: Literal[15, 20, 30]
    aspectRatio: Literal["9:16", "1:1", "16:9"]
    inputAssets: InputAssets
    productUrl: str | None = None
    promptId: str | None = None
    model: str = "auto"
    voice: str = "auto"
    quality: str | None = "auto"
    resolution: str | None = None


class CreateGeneration(Creative):
    model: str = "auto"
    voice: str = "auto"
    quality: str | None = "auto"
    resolution: str | None = None
    promptId: str | None = None
    prompt: str | None = Field(default=None, min_length=1, max_length=16000)

    @model_validator(mode="after")
    def required_prompt(self):
        from app.services.templates import is_remotion

        if not is_remotion(self.templateId) and (not self.promptId or not self.prompt):
            raise ValueError("Current prompt required")
        return self

    quoteId: str


class Resolve(BaseModel):
    url: str


class Checkout(BaseModel):
    priceId: str


class UploadUrl(BaseModel):
    """Asks for a short-lived direct-upload target; the file never passes through the API."""

    model_config = ConfigDict(extra="forbid")
    role: Literal["person", "product", "source_video"]
    contentType: str = Field(min_length=1, max_length=100)
    size: int = Field(ge=1)
    filename: str = Field(default="upload", min_length=1, max_length=255)


class UploadComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uploadId: str = Field(min_length=1, max_length=2048)
    source: Literal["try_on"] | None = None
