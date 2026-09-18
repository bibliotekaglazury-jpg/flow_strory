"""Server-owned capability routing and configured application credit pricing."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from .base import GenerationInput, ProviderError, VideoProvider
from .mock import MockVideoProvider
from .openrouter import OpenRouterVideoProvider, MODEL

DURATIONS = (15, 20, 30)
RATIOS = ("9:16", "1:1", "16:9")


def validate_input(request: GenerationInput) -> None:
    if (
        type(request.duration_seconds) is not int
        or request.duration_seconds not in DURATIONS
        or request.aspect_ratio not in RATIOS
        or request.quality not in ("auto", None)
        or request.resolution not in (None, "auto", "480p")
        or request.voice != "auto"
        or len(request.reference_image_urls) > 20
        or len(request.reference_video_urls) > 6
    ):
        raise ProviderError("UNSUPPORTED_SETTINGS", "These generation settings are not supported.")
    if not request.prompt.strip():
        raise ProviderError("INVALID_PROMPT", "Enter a production prompt.")


@dataclass(frozen=True)
class RegisteredModel:
    id: str
    label: str
    provider: VideoProvider
    priority: int = 10
    enabled: bool = True
    media_type: str = "video"
    vendor_model_id: str = ""
    supports_image: bool = True
    supports_person: bool = True
    supports_video: bool = True
    supports_audio: bool = False
    durations: tuple[int, ...] = DURATIONS
    supports_first_frame: bool = True
    supports_last_frame: bool = False

    def estimate_cost(self, request: GenerationInput) -> int:
        return self.provider.estimate_cost(request)

    def supports(self, request: GenerationInput) -> bool:
        return (
            self.enabled
            and request.duration_seconds in self.durations
            and (not request.has_person or self.supports_person)
            and (not request.reference_image_urls or self.supports_image)
            and (not request.reference_video_urls or self.supports_video)
        )

    def public_option(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "available": self.enabled,
            "unavailableReason": None if self.enabled else "Currently unavailable",
            "configurations": [
                {
                    "duration": duration,
                    "aspectRatio": ratio,
                    "quality": None,
                    "resolution": "480p",
                    "supportsPersonImage": self.supports_person,
                    "supportsSourceVideo": self.supports_video,
                }
                for duration in self.durations
                for ratio in RATIOS
            ],
            "voices": [{"id": "auto", "label": "Auto"}],
        }


def build_registry(env: Mapping[str, str] | None = None) -> tuple[RegisteredModel, ...]:
    env = os.environ if env is None else env
    mode = env.get("VIDEO_PROVIDER", "disabled")
    environment = env.get("APP_ENV", "production").lower()
    if mode == "mock":
        if environment not in {"development", "test", "local"}:
            return ()
        return (RegisteredModel("simulation-video", "Development simulation", MockVideoProvider()),)
    if mode != "openrouter" or env.get("OPENROUTER_VIDEO_ENABLED", "false").lower() != "true":
        return ()
    try:
        credits = int(env.get("VIDEO_CREDITS_PER_SECOND", "0"))
    except ValueError:
        return ()
    key = env.get("OPENROUTER_API_KEY", "")
    if credits <= 0 or not key:
        return ()
    model = env.get("OPENROUTER_VIDEO_MODEL", MODEL)
    if model != MODEL:
        return ()
    return (
        RegisteredModel(
            "ugc-video-v1",
            "Studio video",
            OpenRouterVideoProvider(key, credits, model),
            vendor_model_id=model,
            supports_audio=True,
            durations=(15,),
        ),
    )


def route_model(
    models: tuple[RegisteredModel, ...], request: GenerationInput, selection: str = "auto"
) -> RegisteredModel:
    validate_input(request)
    candidates = [
        model
        for model in models
        if model.supports(request) and (selection == "auto" or model.id == selection)
    ]
    if not candidates:
        raise ProviderError("GENERATION_UNAVAILABLE", "No generation option is available for these settings.")
    return candidates[0]


def public_models(models: tuple[RegisteredModel, ...]) -> list[dict]:
    enabled = [model for model in models if model.enabled]
    configurations = []
    for model in enabled:
        for configuration in model.public_option()["configurations"]:
            if configuration not in configurations:
                configurations.append(configuration)
    return [
        {
            "id": "auto",
            "label": "Auto",
            "available": bool(enabled),
            "unavailableReason": None if enabled else "Generation is not configured",
            "configurations": configurations,
            "voices": [{"id": "auto", "label": "Auto"}],
        }
    ] + [model.public_option() for model in enabled]
