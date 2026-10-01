from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")
    app_env: str = "development"
    auth_mode: str = "mock"
    mock_user_id: str = "development-user"
    database_url: str = "postgresql+psycopg://ugc:ugc@localhost:5432/ugc"
    redis_url: str = "redis://localhost:6379/0"
    public_api_url: str = "http://localhost:8000"
    provider_asset_origin: str = ""
    frontend_origin: str = "http://localhost:3000"
    storage_mode: str = "local"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    storage_path: str = "./var/assets"
    storage_signing_secret: str = "development-only-signing-secret"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "ugc"
    s3_region: str = "auto"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    supabase_url: str = ""
    supabase_jwt_audience: str = "authenticated"
    # Karma -> UGC service credential. Unset = service mode off; X-Karma-Subject is then ignored.
    karma_service_token: SecretStr = Field(default=SecretStr(""), repr=False, exclude=True)
    # Comma-separated browser origins allowed to PUT/GET direct uploads and media (e.g. Karma).
    karma_allowed_origins: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_catalog_json: str = "{}"
    mock_initial_credits: int = 1000
    text_provider: str = "deterministic"
    text_provider_enabled: bool = False
    openai_api_key: str = ""
    prompt_model: str = ""
    video_provider: str = "mock"
    muapi_enabled: bool = False
    muapi_api_key: str = ""
    video_credits_per_second: int = 0
    render_only_credits_per_second: int = Field(default=1, ge=0)
    render_timeout_seconds: int = Field(default=600, ge=1, le=3600)
    render_node_path: str = "node"
    chat_provider: Literal["claude", "deepseek", "mock"] = "claude"
    anthropic_api_key: SecretStr = Field(default=SecretStr(""), repr=False, exclude=True)
    anthropic_workspace_id: str = Field(default="", pattern=r"^(?:wrkspc_[A-Za-z0-9]+)?$")
    claude_model: str = "claude-sonnet-5"
    claude_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    # Preparation only classifies the brief; it does not need the director's thinking depth.
    claude_prep_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"
    # Skip the assessment call when there is no product URL and no explicit research request.
    claude_skip_preparation_without_url: bool = True
    claude_max_rounds: int = Field(default=4, ge=2, le=4)
    claude_max_web_searches: int = Field(default=2, ge=0, le=2)
    claude_max_web_fetches: int = Field(default=2, ge=0, le=2)
    claude_max_input_tokens: int = Field(default=24000, ge=1024, le=48000)
    claude_max_output_tokens: int = Field(default=8192, ge=1024, le=16384)
    claude_session_budget_cents: int = Field(default=100, ge=1, le=1000)
    claude_validation_budget_cents: int = Field(default=100, ge=1, le=1000)
    claude_timeout_seconds: int = Field(default=120, ge=5, le=300)
    openrouter_api_key: str = ""
    openrouter_video_model: str = "alibaba/wan-3.0"
    openrouter_video_enabled: bool = False
    # Fallback text-only director; reuses openrouter_api_key, no separate key needed.
    openrouter_chat_model: str = "deepseek/deepseek-chat"
    # DeepSeek via OpenRouter routinely takes 60-110s per call, well past Claude's
    # 120s default; this bounds the whole turn (director + one repair round).
    deepseek_timeout_seconds: int = Field(default=280, ge=5, le=300)
    # Still-image look preview (virtual try-on). Separate from the video route on
    # purpose: different model, different endpoint, flat per-image price.
    image_provider: Literal["openrouter", "mock"] = "mock"
    openrouter_image_model: str = "google/gemini-3-pro-image"
    image_credits_per_generation: int = Field(default=0, ge=0)
    # Subtitle Studio transcription, server-only. "whisper" (Whisper via the existing OpenRouter
    # key) measures word timing from the audio; "openrouter"/"gemini" ask Gemini, whose
    # timestamps drift on real clips, and stay only as a fallback.
    subtitle_transcription_provider: Literal["whisper", "openrouter", "gemini", "mock"] = "mock"
    openrouter_whisper_model: str = "openai/whisper-large-v3-turbo"
    openrouter_transcription_model: str = "google/gemini-2.5-flash"
    gemini_api_key: str = ""
    gemini_transcription_model: str = "gemini-2.5-flash"
    subtitle_max_audio_bytes: int = Field(default=19 * 1024 * 1024, ge=1)
    # Transcription is sold for real videos, not 15-second clips; parts keep long ones reliable.
    subtitle_max_duration_seconds: int = Field(default=60 * 60, ge=60, le=4 * 60 * 60)
    storyflow_video_duration_seconds: int = Field(default=15, ge=15, le=15)

    @property
    def karma_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.karma_allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def production_guard(self):
        if self.provider_asset_origin and (
            self.app_env != "development" or not self.provider_asset_origin.startswith("https://")
        ):
            raise ValueError("Provider asset origin is HTTPS and local-development only")
        if self.app_env != "development":
            if 0 < len(self.karma_service_token.get_secret_value()) < 32:
                raise ValueError("KARMA_SERVICE_TOKEN must be at least 32 characters")
            if (
                self.auth_mode == "mock"
                or self.storage_mode == "local"
                or self.video_provider == "mock"
                or self.image_provider == "mock"
                or self.subtitle_transcription_provider == "mock"
                or self.text_provider == "deterministic"
            ):
                raise ValueError("Development auth/storage/provider forbidden outside development")
            if (
                not self.supabase_url.startswith("https://")
                or not self.s3_access_key_id
                or not self.s3_secret_access_key
            ):
                raise ValueError("Production auth and private storage configuration required")
        return self


@lru_cache
def settings():
    return Settings()
