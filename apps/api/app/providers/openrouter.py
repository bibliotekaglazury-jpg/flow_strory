"""One verified OpenRouter video model; no fallback and no automatic POST retry."""

import re
import logging
from urllib.parse import urlsplit
import httpx
from .base import ProviderError, ProviderSubmission, ProviderResult, CancellationResult

MODEL = "alibaba/wan-3.0"
BASE = "https://openrouter.ai/api/v1/videos"


def _safe_provider_error(response):
    """Return bounded diagnostics without retaining provider text, prompts, URLs or keys."""
    code = "unknown"
    message = ""
    try:
        error = response.json().get("error", {})
        if isinstance(error, dict):
            candidate = error.get("code")
            if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", candidate):
                code = candidate
            if isinstance(error.get("message"), str):
                message = error["message"].lower()
    except (ValueError, AttributeError):
        pass
    is_reference_error = any(term in message for term in ("reference", "image", "fetch", "url")) or (
        "reference" in code.lower()
    )
    detail = re.sub(r"https?://[^\s\"']+", "[url]", message, flags=re.IGNORECASE)
    detail = re.sub(r"(?:sk-[A-Za-z0-9_-]+|signature=[A-Fa-f0-9]+)", "[redacted]", detail)
    detail = re.sub(r"\s+", " ", detail).strip()[:300]
    return code, is_reference_error, detail


class OpenRouterVideoProvider:
    key = "openrouter"
    supports_idempotency = False  # Not promised by the inspected API contract.
    can_cancel = False
    requires_native_audio = True

    def __init__(self, api_key, credits_per_second, model=MODEL, client=None):
        self.api_key, self.credits_per_second, self.model, self.client = (
            api_key,
            credits_per_second,
            model,
            client,
        )
        if model != MODEL:
            raise ValueError("Only the approved video model is supported")

    def estimate_cost(self, request):
        self.validate(request)
        if self.credits_per_second <= 0:
            raise ProviderError("GENERATION_UNAVAILABLE", "Generation pricing is not configured.")
        return 15 * self.credits_per_second

    def validate(self, request):
        if request.duration_seconds != 15 or request.aspect_ratio not in ("9:16", "1:1", "16:9"):
            raise ProviderError("UNSUPPORTED_SETTINGS", "Only 15-second videos are available.")
        if (
            request.resolution not in (None, "auto", "480p")
            or request.quality not in (None, "auto")
            or request.voice != "auto"
        ):
            raise ProviderError("UNSUPPORTED_SETTINGS", "These video settings are unavailable.")
        if len(request.reference_image_urls) > 9 or len(request.reference_video_urls) > 3:
            raise ProviderError("UNSUPPORTED_SETTINGS", "Too many video references.")
        for url in (*request.reference_image_urls, *request.reference_video_urls):
            parts = urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise ProviderError(
                    "REFERENCE_UNAVAILABLE", "Video references require reachable HTTPS storage."
                )

    def payload(self, request):
        self.validate(request)
        references = [
            {"type": "image_url", "image_url": {"url": url}} for url in request.reference_image_urls
        ]
        references += [
            {"type": "video_url", "video_url": {"url": url}} for url in request.reference_video_urls
        ]
        return {
            "model": self.model,
            "prompt": request.prompt,
            "duration": 15,
            "aspect_ratio": request.aspect_ratio,
            "resolution": "480p",
            "generate_audio": True,
            "input_references": references,
        }

    async def _request(self, method, url, payload=None):
        async def send(client):
            return await client.request(
                method, url, json=payload, headers={"Authorization": "Bearer " + self.api_key}, timeout=60
            )

        try:
            if self.client:
                response = await send(self.client)
            else:
                async with httpx.AsyncClient(follow_redirects=False) as client:
                    response = await send(client)
        except httpx.HTTPError:
            raise ProviderError(
                "VIDEO_TRANSPORT_ERROR",
                "The video service could not be reached.",
                retryable=method == "GET",
                submission_unknown=method == "POST",
            ) from None
        if not response.is_success:
            provider_error_code, is_reference_error, provider_error_detail = _safe_provider_error(response)
            logging.getLogger(__name__).warning(
                "video_http_rejected status=%s code=%s detail=%s",
                response.status_code,
                provider_error_code,
                provider_error_detail,
                extra={
                    "http_status": response.status_code,
                    "method": method,
                    "provider_error_code": provider_error_code,
                },
            )
            if response.status_code == 402:
                raise ProviderError(
                    "VIDEO_SERVICE_BALANCE_LOW", "Video generation is temporarily unavailable."
                )
            if response.status_code == 400 and is_reference_error:
                raise ProviderError(
                    "VIDEO_REFERENCE_REJECTED",
                    "The video service could not read one or more reference images.",
                )
            raise ProviderError(
                "VIDEO_SERVICE_ERROR",
                "The video service did not accept the request.",
                retryable=method == "GET",
                submission_unknown=method == "POST" and response.status_code >= 500,
            )
        try:
            return response.json()
        except ValueError:
            raise ProviderError(
                "INVALID_PROVIDER_RESULT",
                "The video service returned an invalid result.",
                submission_unknown=method == "POST",
            ) from None

    async def generate(self, request, idempotency_key):
        payload = await self._request("POST", BASE, self.payload(request))
        job_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", job_id):
            raise ProviderError(
                "INVALID_PROVIDER_RESULT",
                "The video request could not be confirmed.",
                submission_unknown=True,
            )
        try:
            state = self.normalize_result(payload).state
        except ProviderError:
            # Acceptance is confirmed by ID; poll even when the initial status is unfamiliar.
            state = "queued"
        return ProviderSubmission(job_id, state)

    async def get_status(self, provider_job_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", provider_job_id):
            raise ProviderError("INVALID_PROVIDER_RESULT", "Invalid video reference.")
        return self.normalize_result(await self._request("GET", BASE + "/" + provider_job_id))

    def normalize_result(self, payload):
        mapping = {
            "pending": "queued",
            "in_progress": "generating",
            "completed": "completed",
            "failed": "failed",
            "expired": "failed",
            "cancelled": "cancelled",
        }
        if not isinstance(payload, dict):
            raise ProviderError("INVALID_PROVIDER_RESULT", "Invalid video status.", retryable=True)
        status = payload.get("status")
        if status not in mapping:
            raise ProviderError("INVALID_PROVIDER_RESULT", "Unknown video status.", retryable=True)
        urls = payload.get("unsigned_urls") or []
        if not isinstance(urls, list) or any(
            not isinstance(u, str) or urlsplit(u).scheme != "https" for u in urls
        ):
            raise ProviderError("INVALID_PROVIDER_RESULT", "Invalid video output.", retryable=True)
        error = (
            ProviderError("GENERATION_FAILED", "The video could not be generated.")
            if status in ("failed", "expired")
            else None
        )
        return ProviderResult(mapping[status], tuple(urls), error=error)

    async def cancel(self, provider_job_id):
        return CancellationResult(False)

    async def download_output(self, provider_job_id):
        # Official content endpoint. Never forward Authorization to redirected hosts.
        from app.services.product import download_public

        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", provider_job_id):
            raise ValueError("Invalid job")
        async with httpx.AsyncClient(follow_redirects=False, timeout=120) as client:
            async with client.stream(
                "GET",
                BASE + "/" + provider_job_id + "/content?index=0",
                headers={"Authorization": "Bearer " + self.api_key},
            ) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    data, _, _ = await download_public(
                        response.headers.get("location", ""), 500 * 1024 * 1024, "video/*"
                    )
                    return data
                response.raise_for_status()
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 500 * 1024 * 1024:
                        raise ValueError("Video size limit")
                return bytes(data)
