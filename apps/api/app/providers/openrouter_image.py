"""One OpenRouter image model for look previews; synchronous, no job to poll."""

import base64
import binascii
import logging
from urllib.parse import urlsplit

import httpx

from .base import ProviderError
from .openrouter import _safe_provider_error

BASE = "https://openrouter.ai/api/v1/images"
MODEL = "google/gemini-3-pro-image"
# The model's documented identity-preservation range; a base photo to re-angle counts too.
MAX_REFERENCES = 6
RATIOS = ("9:16", "1:1", "16:9", "4:5")

log = logging.getLogger(__name__)


class OpenRouterImageProvider:
    """Returns the finished image in the same response, unlike the video route."""

    key = "openrouter"

    def __init__(self, api_key, model=MODEL, client=None):
        self.api_key, self.model, self.client = api_key, model, client

    def validate(self, image_urls, aspect_ratio):
        if not image_urls or len(image_urls) > MAX_REFERENCES:
            raise ProviderError("UNSUPPORTED_SETTINGS", "Too many reference images for one look.")
        if aspect_ratio not in RATIOS:
            raise ProviderError("UNSUPPORTED_SETTINGS", "This frame is unavailable for previews.")
        for url in image_urls:
            parts = urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise ProviderError(
                    "REFERENCE_UNAVAILABLE", "Previews require reachable HTTPS storage."
                )

    async def generate(self, image_urls, prompt, aspect_ratio) -> bytes:
        self.validate(image_urls, aspect_ratio)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "n": 1,
            "input_references": [
                {"type": "image_url", "image_url": {"url": url}} for url in image_urls
            ],
        }

        async def send(client):
            return await client.post(
                BASE,
                json=payload,
                headers={"Authorization": "Bearer " + self.api_key},
                timeout=120,
            )

        try:
            if self.client:
                response = await send(self.client)
            else:
                async with httpx.AsyncClient(follow_redirects=False) as client:
                    response = await send(client)
        except httpx.HTTPError:
            raise ProviderError(
                "IMAGE_TRANSPORT_ERROR", "The preview service could not be reached."
            ) from None
        if not response.is_success:
            code, is_reference_error, detail = _safe_provider_error(response)
            log.warning(
                "image_http_rejected status=%s code=%s detail=%s",
                response.status_code,
                code,
                detail,
                extra={"http_status": response.status_code, "provider_error_code": code},
            )
            if response.status_code == 402:
                raise ProviderError(
                    "IMAGE_SERVICE_BALANCE_LOW", "Look previews are temporarily unavailable."
                )
            if response.status_code == 400 and is_reference_error:
                raise ProviderError(
                    "IMAGE_REFERENCE_REJECTED",
                    "The preview service could not read one or more of your photos.",
                )
            raise ProviderError("IMAGE_SERVICE_ERROR", "The preview could not be created.")
        try:
            encoded = response.json()["data"][0]["b64_json"]
            return base64.b64decode(encoded, validate=True)
        except (ValueError, KeyError, IndexError, TypeError, binascii.Error):
            raise ProviderError("IMAGE_SERVICE_ERROR", "The preview could not be created.") from None
