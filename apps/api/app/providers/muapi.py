"""Original adapter based on https://api.muapi.ai/openapi.json (2026-09-10).

Paid POSTs have no documented idempotency guarantee and are never retried here.
The worker must persist submission intent before calling generate.
"""

from typing import Any, NoReturn
from urllib.parse import quote, urlsplit

import httpx

from .base import CancellationResult, GenerationInput, ProviderError, ProviderResult, ProviderSubmission


class MuAPIProvider:
    key = "muapi"
    supports_idempotency = False
    can_cancel = False
    base_url = "https://api.muapi.ai"

    def __init__(self, api_key: str, credits_per_second: int, *, client: httpx.AsyncClient | None = None):
        if not api_key or type(credits_per_second) is not int or credits_per_second <= 0:
            raise ValueError("Live provider requires credentials and positive configured credits")
        self._api_key = api_key
        self._credits_per_second = credits_per_second
        self._client = client

    def estimate_cost(self, request: GenerationInput) -> int:
        return request.duration_seconds * self._credits_per_second

    async def _request(self, method: str, path: str, payload: dict | None = None) -> Any:
        async def send(client):
            return await client.request(
                method, self.base_url + path, headers={"x-api-key": self._api_key}, json=payload, timeout=60
            )

        try:
            if self._client is None:
                async with httpx.AsyncClient(follow_redirects=False) as client:
                    response = await send(client)
            else:
                response = await send(self._client)
        except httpx.HTTPError:
            if method == "POST":
                raise ProviderError(
                    "SUBMISSION_OUTCOME_UNKNOWN",
                    "Submission could not be confirmed. The job is being reviewed.",
                    submission_unknown=True,
                ) from None
            raise ProviderError(
                "GENERATION_STATUS_UNAVAILABLE",
                "Generation status is temporarily unavailable.",
                retryable=True,
            ) from None
        if response.status_code >= 500 and method == "POST":
            raise ProviderError(
                "SUBMISSION_OUTCOME_UNKNOWN",
                "Submission could not be confirmed. The job is being reviewed.",
                submission_unknown=True,
            )
        if not response.is_success:
            raise ProviderError(
                "GENERATION_SERVICE_UNAVAILABLE",
                "The generation service could not process this request.",
                retryable=method == "GET" and (response.status_code >= 500 or response.status_code == 429),
            )
        try:
            result = response.json()
        except ValueError:
            raise ProviderError(
                "SUBMISSION_OUTCOME_UNKNOWN" if method == "POST" else "GENERATION_STATUS_UNAVAILABLE",
                "The generation service returned an unreadable response.",
                submission_unknown=method == "POST",
                retryable=method == "GET",
            ) from None
        return result

    async def generate(self, request: GenerationInput, idempotency_key: str) -> ProviderSubmission:
        # This key is persisted by the application, not sent as a fictional upstream guarantee.
        if not idempotency_key:
            raise ValueError("An application idempotency key is required")
        from .registry import validate_input

        validate_input(request)
        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "duration": request.duration_seconds,
            "aspect_ratio": request.aspect_ratio,
        }
        if request.reference_video_urls or len(request.reference_image_urls) > 1:
            endpoint = "seedance-2.5-omni-reference"
            payload.update(
                images_list=list(request.reference_image_urls),
                videos_list=list(request.reference_video_urls),
                omni_reference_task_type="reference",
            )
        elif request.reference_image_urls:
            endpoint = "seedance-2.5-image-to-video"
            payload["image_url"] = request.reference_image_urls[0]
        else:
            endpoint = "seedance-2.5-text-to-video"
        data = await self._request("POST", "/api/v1/" + endpoint, payload)
        job_id = data.get("request_id") if isinstance(data, dict) else None
        if not isinstance(job_id, str) or not job_id.strip():
            raise ProviderError(
                "SUBMISSION_OUTCOME_UNKNOWN",
                "Submission could not be confirmed. The job is being reviewed.",
                submission_unknown=True,
            )
        state = "queued" if data.get("status") in ("queued", "pending") else "generating"
        return ProviderSubmission(job_id, state)

    async def get_status(self, provider_job_id: str) -> ProviderResult:
        data = await self._request(
            "GET", "/api/v1/predictions/" + quote(provider_job_id, safe="") + "/result"
        )
        return self.normalize_result(data)

    async def cancel(self, provider_job_id: str) -> CancellationResult:
        # Dashboard cancellation is not a documented API-key authenticated public endpoint.
        return CancellationResult(supported=False)

    def normalize_result(self, payload: Any) -> ProviderResult:
        if not isinstance(payload, dict):
            return self._invalid_result()
        status = payload.get("status")
        if status in ("queued", "pending"):
            return ProviderResult("queued")
        if status == "processing":
            return ProviderResult("generating")
        if status == "cancelled":
            return ProviderResult("cancelled")
        if status == "failed":
            return ProviderResult(
                "failed",
                error=ProviderError(
                    "GENERATION_FAILED", "The video could not be generated. Please review your inputs."
                ),
            )
        if status == "completed":
            outputs = payload.get("outputs")
            if isinstance(outputs, list) and outputs and all(self._valid_url(url) for url in outputs):
                return ProviderResult("completed", output_urls=tuple(outputs))
        return self._invalid_result()

    @staticmethod
    def _valid_url(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            url = urlsplit(value)
            return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
        except ValueError:
            return False

    @staticmethod
    def _invalid_result() -> NoReturn:
        # A malformed read is not proof that remote work failed. Preserve the
        # existing job/reservation while the worker retries or reconciles it.
        raise ProviderError(
            "GENERATION_STATUS_UNAVAILABLE",
            "Generation status could not be confirmed. Please check again shortly.",
            retryable=True,
        )
