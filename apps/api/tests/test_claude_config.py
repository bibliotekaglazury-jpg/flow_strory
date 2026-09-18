import pytest
from pydantic import ValidationError
from app.config import Settings


def test_claude_config_keeps_credentials_secret_and_ignores_old_env(tmp_path):
    env = tmp_path / "settings.env"
    env.write_text("CODEX_RETIRED=ignored\nANTHROPIC_API_KEY=test-secret\n")
    cfg = Settings(_env_file=env)
    assert cfg.anthropic_api_key.get_secret_value() == "test-secret"
    assert "test-secret" not in repr(cfg)
    assert cfg.claude_effort == "medium"
    assert cfg.claude_max_rounds == 4


@pytest.mark.parametrize(
    "values",
    [
        {"claude_max_rounds": 0},
        {"claude_max_rounds": 8},
        {"claude_session_budget_cents": 0},
        {"claude_effort": "random"},
        {"claude_max_output_tokens": 0},
        {"claude_validation_budget_cents": 0},
    ],
)
def test_limits_are_validated(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_retired_codex_fields_are_ignored_and_claude_is_default(monkeypatch):
    monkeypatch.delenv("CHAT_PROVIDER", raising=False)
    cfg = Settings(
        _env_file=None,
        codex_path="/obsolete",
        codex_native_history_allowed=True,
        chat_runtime_path="/obsolete",
        chat_timeout_seconds=60,
    )
    assert cfg.chat_provider == "claude"
    assert not any(
        name in cfg.model_dump()
        for name in (
            "codex_path",
            "codex_native_history_allowed",
            "chat_runtime_path",
            "chat_timeout_seconds",
        )
    )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, chat_provider="codex_local")
