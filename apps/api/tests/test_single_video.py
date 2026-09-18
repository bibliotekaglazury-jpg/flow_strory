"""Paid integrations use injected transports only; no credentials or network required."""

import json
import httpx
import pytest
from pydantic import ValidationError
from app.providers.openrouter import OpenRouterVideoProvider, MODEL
from app.providers.chat import MockChatProvider
from app.providers.base import GenerationInput, ProviderError
from app.providers.registry import build_registry, route_model
from app.video_recipe import RecipeAnswer, compile_recipe

POLISH = "Zrób naturalne 15-sekundowe UGC dla kremu do twarzy. Dziewczyna mówi po polsku."


def request(**changes):
    return GenerationInput(
        **dict(
            prompt="Polish dialogue: To mój codzienny krem.",
            duration_seconds=15,
            aspect_ratio="9:16",
            **changes,
        )
    )


@pytest.mark.asyncio
async def test_language_override_and_validation():
    _, answer = await MockChatProvider().send_message(
        "s", None, [{"text": "Niech mówi po niemiecku"}], {"duration": 15}
    )
    assert answer.recipe.language == "de"
    value = answer.model_dump()
    value["recipe"]["spokenContent"]["language"] = "pl"
    with pytest.raises(ValidationError):
        RecipeAnswer.model_validate(value)
    assert answer.recipe.spokenContent.dialogue in compile_recipe(answer.recipe)


@pytest.mark.asyncio
async def test_openrouter_submit_poll_native_audio_and_refs():
    seen = []

    def handle(req):
        seen.append(req.method)
        if req.method == "POST":
            body = json.loads(req.content)
            assert body["model"] == MODEL and body["duration"] == 15 and body["generate_audio"] is True
            assert body["resolution"] == "480p"
            assert body["input_references"] == [
                {"type": "image_url", "image_url": {"url": "https://assets.example/owned.png"}}
            ]
            assert "fallback" not in body
            return httpx.Response(
                202, json={"id": "job-123", "status": "pending", "polling_url": "https://evil.example/steal"}
            )
        assert str(req.url) == "https://openrouter.ai/api/v1/videos/job-123"
        return httpx.Response(
            200,
            json={"id": "job-123", "status": "completed", "unsigned_urls": ["https://cdn.example/out.mp4"]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = OpenRouterVideoProvider("fake", 3, client=client)
        submitted = await provider.generate(
            request(reference_image_urls=("https://assets.example/owned.png",)), "app-id"
        )
        assert submitted.state == "queued"
        assert (await provider.get_status(submitted.job_id)).state == "completed"
    assert seen == ["POST", "GET"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response", [httpx.Response(503), httpx.Response(202, json=[]), httpx.Response(202, text="invalid")]
)
async def test_no_repeated_paid_submission_after_unknown_result(response):
    calls = []

    def handle(req):
        calls.append(req)
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError) as error:
            await OpenRouterVideoProvider("fake", 3, client=client).generate(request(), "same")
        assert error.value.submission_unknown and not error.value.retryable
        assert len(calls) == 1


@pytest.mark.parametrize("duration", [20, 30])
def test_only_one_real_model_and_duration(duration):
    models = build_registry(
        {
            "VIDEO_PROVIDER": "openrouter",
            "OPENROUTER_VIDEO_ENABLED": "true",
            "OPENROUTER_API_KEY": "fake",
            "VIDEO_CREDITS_PER_SECOND": "3",
        }
    )
    assert len(models) == 1 and models[0].vendor_model_id == MODEL
    assert models[0].provider.requires_native_audio
    assert {x["duration"] for x in models[0].public_option()["configurations"]} == {15}
    assert {x["resolution"] for x in models[0].public_option()["configurations"]} == {"480p"}
    req = GenerationInput(prompt="Video", duration_seconds=duration, aspect_ratio="9:16")
    with pytest.raises(ProviderError):
        route_model(models, req)
    with pytest.raises(ProviderError):
        models[0].provider.payload(req)
    for old in ["higgsfield", "muapi", "fal", "wavespeed"]:
        assert build_registry({"VIDEO_PROVIDER": old}) == ()


def test_native_media_validation_rejects_silent_or_wrong_duration(monkeypatch):
    from types import SimpleNamespace
    from app.services.video_validation import validate_native_video

    data = {
        "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "15.0"},
    }
    monkeypatch.setattr(
        "app.services.video_validation.subprocess.run",
        lambda *a, **kw: SimpleNamespace(returncode=0, stdout=json.dumps(data)),
    )
    assert validate_native_video(b"fixture", 15)
    data["streams"].pop()
    assert not validate_native_video(b"fixture", 15)
    data["streams"].append({"codec_type": "audio"})
    data["format"]["duration"] = "8"
    assert not validate_native_video(b"fixture", 15)


@pytest.mark.asyncio
async def test_gateway_balance_rejection_is_known_not_retried(caplog):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(402, json={"error": {"message": "private diagnostics"}})
        )
    ) as client:
        with pytest.raises(ProviderError) as error:
            await OpenRouterVideoProvider("fake-secret", 3, client=client).generate(request(), "key")
        assert error.value.code == "VIDEO_SERVICE_BALANCE_LOW"
        assert not error.value.submission_unknown and not error.value.retryable
        assert "private" not in str(error.value) and "fake-secret" not in caplog.text
        assert any(getattr(r, "http_status", None) == 402 for r in caplog.records)


@pytest.mark.asyncio
async def test_gateway_reference_rejection_returns_safe_actionable_error(caplog):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                400,
                json={
                    "error": {
                        "code": "invalid_reference",
                        "message": "Could not fetch input_references[0] from https://secret.example/image",
                    }
                },
            )
        )
    ) as client:
        with pytest.raises(ProviderError) as error:
            await OpenRouterVideoProvider("fake-secret", 3, client=client).generate(request(), "key")

    assert error.value.code == "VIDEO_REFERENCE_REJECTED"
    assert error.value.message == "The video service could not read one or more reference images."
    assert "secret.example" not in str(error.value)
    assert "secret.example" not in caplog.text
    assert "[url]" in caplog.text
    assert any(getattr(r, "provider_error_code", None) == "invalid_reference" for r in caplog.records)
