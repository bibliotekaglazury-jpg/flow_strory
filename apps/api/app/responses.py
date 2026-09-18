from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool
    fieldErrors: dict[str, list[str]] | None = None


class ErrorResponse(BaseModel):
    error: ApiError
    requestId: str


class AssetView(BaseModel):
    id: str
    role: Literal[
        "product", "person", "source_video", "output_video", "thumbnail", "tryon_photo"
    ]
    kind: Literal["image", "video"]
    mimeType: str
    fileName: str
    sizeBytes: int = Field(ge=0)
    url: str
    urlExpiresAt: datetime | None
    width: int | None
    height: int | None
    durationSeconds: float | None
    createdAt: datetime


class AssetResponse(BaseModel):
    asset: AssetView


class AssetsResponse(BaseModel):
    assets: list[AssetView]


class CatalogImportError(BaseModel):
    row: int
    message: str


class CatalogImportResponse(BaseModel):
    created: list[AssetView]
    errors: list[CatalogImportError]


class TryOnResponse(BaseModel):
    asset: AssetView
    creditsCharged: int = Field(ge=0)


LookScene = Literal["studio", "lifestyle", "outdoor", "custom"]
PhotoRatio = Literal["9:16", "1:1", "16:9", "4:5"]


class LookPhotoView(BaseModel):
    asset: AssetView
    label: str


class LookProjectSummary(BaseModel):
    id: str
    scene: LookScene
    aspectRatio: PhotoRatio
    photoCount: int = Field(ge=0)
    coverUrl: str | None
    createdAt: datetime
    updatedAt: datetime


class LookProjectDetail(BaseModel):
    id: str
    scene: LookScene
    aspectRatio: PhotoRatio
    inputAssets: dict
    model: AssetView | None
    products: list[AssetView]
    photos: list[LookPhotoView]
    createdAt: datetime
    updatedAt: datetime


class LookProjectsResponse(BaseModel):
    projects: list[LookProjectSummary]


class LookProjectResponse(BaseModel):
    project: LookProjectDetail


class Product(BaseModel):
    url: str
    title: str
    description: str
    imageUrl: str | None


class ProductResponse(BaseModel):
    product: Product
    asset: AssetView | None = None


class PromptResponse(BaseModel):
    promptId: str
    prompt: str
    inputFingerprint: str
    createdAt: datetime


class Template(BaseModel):
    slug: str | None = None
    version: str | None = None
    category: str | None = None
    templateType: str | None = None
    thumbnail: str | None = None
    previewVideo: str | None = None
    enabled: bool | None = None
    featured: bool | None = None
    tags: list[str] = []
    supportedAspectRatios: list[str] = []
    supportedDurations: list[int] = []
    inputSchema: dict | None = None
    useCases: list[str] = []
    id: str
    name: str
    description: str
    thumbnailUrl: str | None
    available: bool
    unavailableReason: str | None


class TemplatesResponse(BaseModel):
    templates: list[Template]


class Configuration(BaseModel):
    duration: Literal[15, 20, 30]
    aspectRatio: Literal["9:16", "1:1", "16:9"]
    quality: str | None
    resolution: str | None
    supportsPersonImage: bool
    supportsSourceVideo: bool


class Choice(BaseModel):
    id: str
    label: str


class Model(BaseModel):
    id: str
    label: str
    available: bool
    unavailableReason: str | None
    configurations: list[Configuration]
    voices: list[Choice]


class ModelsResponse(BaseModel):
    models: list[Model]


class GenerationView(BaseModel):
    id: str
    userId: str
    templateId: str
    model: str
    provider: str | None
    status: Literal["queued", "generating", "completed", "failed", "cancelled"]
    progress: int | None = Field(ge=0, le=100)
    prompt: str | None
    normalizedInputs: dict | None = None
    creativeMechanism: str | None = None
    duration: Literal[15, 20, 30]
    aspectRatio: Literal["9:16", "1:1", "16:9"]
    inputAssets: list[AssetView]
    outputAssets: list[AssetView]
    creditsEstimated: int = Field(ge=0)
    creditsCharged: int = Field(ge=0)
    error: ApiError | None
    createdAt: datetime
    updatedAt: datetime

    @model_validator(mode="after")
    def state_invariants(self):
        if self.status == "completed" and not any(a.role == "output_video" for a in self.outputAssets):
            raise ValueError("Completed generation requires output")
        if self.status == "failed" and self.error is None:
            raise ValueError("Failed generation requires error")
        if self.status != "failed" and self.error is not None:
            raise ValueError("Only failed generation carries error")
        if self.status == "cancelled" and (self.outputAssets or self.creditsCharged):
            raise ValueError("Cancelled generation has no output/charge")
        return self


class GenerationResponse(BaseModel):
    generation: GenerationView


class PollResponse(GenerationResponse):
    pollAfterMs: int | None


class HistoryResponse(BaseModel):
    generations: list[GenerationView]
    nextCursor: str | None


class CreditQuote(BaseModel):
    id: str
    creditsEstimated: int = Field(ge=0)
    expiresAt: datetime


class CreditsResponse(BaseModel):
    balance: int = Field(ge=0)
    quote: CreditQuote | None
    updatedAt: datetime


class ProfileCredits(BaseModel):
    available: int = Field(ge=0)
    reserved: int = Field(ge=0)


class ProfileAssets(BaseModel):
    total: int = Field(ge=0)
    byRole: dict[str, int]


class ProfileGenerations(BaseModel):
    total: int = Field(ge=0)
    byStatus: dict[str, int]


class ProfileLookProjects(BaseModel):
    total: int = Field(ge=0)


class ProfileSubtitleProjects(BaseModel):
    total: int = Field(ge=0)


class ProfileTransaction(BaseModel):
    id: str
    kind: str
    availableDelta: int
    reservedDelta: int
    generationId: str | None
    createdAt: datetime


class ProfileResponse(BaseModel):
    userId: str
    credits: ProfileCredits
    assets: ProfileAssets
    generations: ProfileGenerations
    lookProjects: ProfileLookProjects
    subtitleProjects: ProfileSubtitleProjects
    recentTransactions: list[ProfileTransaction]


class CheckoutResponse(BaseModel):
    sessionId: str
    checkoutUrl: str
    expiresAt: datetime


class PortalResponse(BaseModel):
    portalUrl: str
    expiresAt: datetime


class BillingSummary(BaseModel):
    plan: str
    status: str
    renewalDate: datetime | None
    prices: list[Choice]
    available: bool


class WebhookResponse(BaseModel):
    received: bool


SubtitleAspectRatio = Literal["9:16", "16:9"]
SubtitleProjectStatus = Literal["transcribing", "ready", "failed"]
SubtitleExportStatus = Literal["queued", "rendering", "completed", "failed"]
SubtitlePreset = Literal["modern", "classic", "impact", "editorial"]


class SubtitleWordView(BaseModel):
    id: str
    text: str
    startMs: int = Field(ge=0)
    endMs: int = Field(ge=0)


class SubtitleCueView(BaseModel):
    id: str
    startMs: int = Field(ge=0)
    endMs: int = Field(ge=0)
    text: str
    words: list[SubtitleWordView]


class SubtitleStyleView(BaseModel):
    preset: SubtitlePreset
    position: Literal["top", "center", "bottom"]
    size: Literal["small", "medium", "large"]
    safeArea: bool
    textColor: str
    highlightColor: str


class SubtitleExportView(BaseModel):
    id: str
    status: SubtitleExportStatus
    progress: int | None
    outputAsset: AssetView | None
    error: ApiError | None
    shareToken: str | None
    createdAt: datetime
    updatedAt: datetime


class SubtitleSharedExportView(BaseModel):
    id: str
    outputAsset: AssetView | None
    aspectRatio: SubtitleAspectRatio


class SubtitleProjectView(BaseModel):
    id: str
    sourceAsset: AssetView
    status: SubtitleProjectStatus
    aspectRatio: SubtitleAspectRatio
    language: str | None
    durationMs: int = Field(ge=0)
    revision: int = Field(ge=0)
    cues: list[SubtitleCueView]
    style: SubtitleStyleView
    latestExport: SubtitleExportView | None
    error: ApiError | None
    createdAt: datetime
    updatedAt: datetime


class SubtitleProjectSummaryView(BaseModel):
    id: str
    sourceAsset: AssetView
    status: SubtitleProjectStatus
    aspectRatio: SubtitleAspectRatio
    durationMs: int = Field(ge=0)
    latestExport: SubtitleExportView | None
    createdAt: datetime
    updatedAt: datetime


class SubtitleProjectResponse(BaseModel):
    project: SubtitleProjectView


class SubtitleProjectsResponse(BaseModel):
    projects: list[SubtitleProjectSummaryView]
    nextCursor: str | None


class SubtitleExportResponse(BaseModel):
    export: SubtitleExportView


class SubtitleExportPollResponse(BaseModel):
    export: SubtitleExportView
    pollAfterMs: int | None


class SubtitleExportSrtResponse(BaseModel):
    content: str
    fileName: str


class SubtitleSharedExportResponse(BaseModel):
    export: SubtitleSharedExportView
