"""Private provider contracts. These objects must never be serialized to clients."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

State = Literal["queued", "generating", "completed", "failed", "cancelled"]


class ProviderError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False, submission_unknown: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.submission_unknown = submission_unknown


@dataclass(frozen=True)
class GenerationInput:
    prompt: str
    duration_seconds: int
    aspect_ratio: str
    reference_image_urls: tuple[str, ...] = ()
    reference_video_urls: tuple[str, ...] = ()
    has_person: bool = False
    quality: str = "auto"
    resolution: str | None = None
    voice: str = "auto"


@dataclass(frozen=True)
class ProviderSubmission:
    job_id: str
    state: State = "queued"


@dataclass(frozen=True)
class ProviderResult:
    state: State
    output_urls: tuple[str, ...] = ()
    error: ProviderError | None = None
    progress: int | None = None
    simulated: bool = False


@dataclass(frozen=True)
class CancellationResult:
    supported: bool
    cancelled: bool = False


class VideoProvider(Protocol):
    key: str
    supports_idempotency: bool
    can_cancel: bool

    async def generate(self, request: GenerationInput, idempotency_key: str) -> ProviderSubmission: ...
    async def get_status(self, provider_job_id: str) -> ProviderResult: ...
    async def cancel(self, provider_job_id: str) -> CancellationResult: ...
    def normalize_result(self, payload: Any) -> ProviderResult: ...
    def estimate_cost(self, request: GenerationInput) -> int: ...


class ImageProvider(Protocol):
    """Future server boundary only; no image-generation product surface."""

    async def generate(self, request: dict[str, Any], idempotency_key: str) -> ProviderSubmission: ...
    async def edit(self, request: dict[str, Any], idempotency_key: str) -> ProviderSubmission: ...
    async def get_status(self, provider_job_id: str) -> ProviderResult: ...
    async def cancel(self, provider_job_id: str) -> CancellationResult: ...
    def normalize_result(self, payload: Any) -> ProviderResult: ...
    def estimate_cost(self, request: dict[str, Any]) -> int: ...
