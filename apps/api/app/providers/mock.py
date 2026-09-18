"""Explicit development simulation; worker supplies and labels the playable fixture."""

import hashlib
import time

from .base import (
    CancellationResult,
    GenerationInput,
    ProviderError,
    ProviderResult,
    ProviderSubmission,
)


class MockVideoProvider:
    key = "mock"
    supports_idempotency = False
    can_cancel = True

    def __init__(self, credits_per_second: int = 1):
        self._credits_per_second = credits_per_second

    def estimate_cost(self, request: GenerationInput) -> int:
        return request.duration_seconds * self._credits_per_second

    async def generate(self, request: GenerationInput, idempotency_key: str) -> ProviderSubmission:
        # Timestamp travels in the persisted private job ID, so polling survives worker restart.
        digest = hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]
        return ProviderSubmission(f"simulation:{int(time.time())}:{digest}")

    async def get_status(self, provider_job_id: str) -> ProviderResult:
        started_at = int(provider_job_id.split(":")[1])
        elapsed = time.time() - started_at
        state = "queued" if elapsed < 2 else "generating" if elapsed < 6 else "completed"
        return ProviderResult(state, simulated=True)

    async def cancel(self, provider_job_id: str) -> CancellationResult:
        # Durable application state is authoritative; there is no remote task to interrupt.
        return CancellationResult(supported=True, cancelled=True)

    def normalize_result(self, payload: dict) -> ProviderResult:
        state = payload.get("status", "generating")
        if state not in {"queued", "generating", "completed", "cancelled"}:
            state = "generating"
        return ProviderResult(state, simulated=True)


class MockImageProvider:
    """Development look preview: a real decodable PNG, never a network call."""

    key = "mock"

    async def generate(self, image_urls, prompt, aspect_ratio) -> bytes:
        from io import BytesIO

        from PIL import Image

        if not image_urls:
            raise ProviderError("REFERENCE_UNAVAILABLE", "A look preview needs your photos.")
        width, height = {"9:16": (36, 64), "1:1": (64, 64), "16:9": (64, 36)}.get(
            aspect_ratio, (36, 64)
        )
        # Colour derived from the request so different looks are visibly different.
        seed = int(hashlib.sha256("|".join(image_urls).encode()).hexdigest()[:6], 16)
        data = BytesIO()
        Image.new("RGB", (width, height), f"#{seed:06x}").save(data, format="PNG")
        return data.getvalue()
