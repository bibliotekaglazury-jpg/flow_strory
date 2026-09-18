import asyncio
import json

import httpx
import pytest

from app.providers import (
    GenerationInput,
    MockVideoProvider,
    MuAPIProvider,
    ProviderError,
    build_registry,
    route_model,
)


def request(**changes):
    return GenerationInput(
        **{"prompt": "Show the product", "duration_seconds": 20, "aspect_ratio": "9:16", **changes}
    )


def test_router_requires_explicit_live_pricing_and_never_falls_back_to_mock():
    assert build_registry({"APP_ENV": "production", "VIDEO_PROVIDER": "mock"}) == ()
    assert build_registry({"VIDEO_PROVIDER": "muapi", "MUAPI_API_KEY": "secret"}) == ()
    with pytest.raises(ProviderError) as error:
        route_model((), request())
    assert error.value.code == "GENERATION_UNAVAILABLE"


def test_router_rejects_unsupported_settings_and_exposes_no_vendor_metadata():
    models = build_registry(
        {
            "VIDEO_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "secret",
            "OPENROUTER_VIDEO_ENABLED": "true",
            "VIDEO_CREDITS_PER_SECOND": "3",
        }
    )
    model = route_model(models, request(duration_seconds=15))
    assert model.estimate_cost(request(duration_seconds=15)) == 45
    public = json.dumps(model.public_option())
    assert "seedance" not in public and "openrouter" not in public and "secret" not in public
    with pytest.raises(ProviderError):
        route_model(models, request(duration_seconds=19))
    with pytest.raises(ProviderError):
        route_model(models, request(voice="specific-voice"))


def test_muapi_maps_multiple_references_without_dropping_person_or_duration():
    async def run():
        def handle(req):
            body = json.loads(req.content)
            assert req.url.path == "/api/v1/seedance-2.5-omni-reference"
            assert body["images_list"] == [
                "https://assets.example/product.jpg",
                "https://assets.example/person.jpg",
            ]
            assert body["videos_list"] == ["https://assets.example/source.mp4"]
            assert body["duration"] == 30
            return httpx.Response(200, json={"request_id": "private-job", "status": "processing"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            provider = MuAPIProvider("secret", 3, client=client)
            result = await provider.generate(
                request(
                    duration_seconds=30,
                    reference_image_urls=(
                        "https://assets.example/product.jpg",
                        "https://assets.example/person.jpg",
                    ),
                    reference_video_urls=("https://assets.example/source.mp4",),
                ),
                "application-key",
            )
            assert result.job_id == "private-job" and result.state == "generating"
            assert not (await provider.cancel(result.job_id)).supported

    asyncio.run(run())


def test_submit_timeout_is_unknown_and_never_retried():
    async def run():
        calls = []

        def handle(req):
            calls.append(req)
            raise httpx.ReadTimeout("secret provider detail", request=req)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(ProviderError) as error:
                await MuAPIProvider("secret", 3, client=client).generate(request(), "key")
            assert error.value.code == "SUBMISSION_OUTCOME_UNKNOWN"
            assert error.value.submission_unknown and not error.value.retryable
            assert "secret" not in str(error.value)
            assert len(calls) == 1

    asyncio.run(run())


@pytest.mark.parametrize(
    "payload, state, code",
    [
        ({"status": "completed", "outputs": ["https://cdn.example/video.mp4"]}, "completed", None),
        ({"status": "failed", "error": "secret diagnostic"}, "failed", "GENERATION_FAILED"),
        ({"status": "pending"}, "queued", None),
        ({"status": "cancelled"}, "cancelled", None),
    ],
)
def test_normalization_enforces_results_and_safe_errors(payload, state, code):
    result = MuAPIProvider("secret", 3).normalize_result(payload)
    assert result.state == state
    assert (result.error.code if result.error else None) == code
    assert "secret diagnostic" not in repr(result)


def test_mock_polling_survives_provider_recreation(monkeypatch):
    async def run():
        monkeypatch.setattr("app.providers.mock.time.time", lambda: 1000)
        submitted = await MockVideoProvider().generate(request(), "key")
        assert (await MockVideoProvider().get_status(submitted.job_id)).state == "queued"
        monkeypatch.setattr("app.providers.mock.time.time", lambda: 1003)
        assert (await MockVideoProvider().get_status(submitted.job_id)).state == "generating"
        monkeypatch.setattr("app.providers.mock.time.time", lambda: 1007)
        result = await MockVideoProvider().get_status(submitted.job_id)
        assert result.state == "completed" and result.simulated
        assert not result.output_urls  # Worker attaches a real playable fixture.

    asyncio.run(run())


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"status": "processing"}),
        httpx.Response(200, text="upstream diagnostic"),
        httpx.Response(503, text="upstream diagnostic"),
    ],
)
def test_unconfirmed_submission_retains_unknown_outcome(response):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: response)) as client:
            with pytest.raises(ProviderError) as error:
                await MuAPIProvider("secret", 3, client=client).generate(request(), "key")
            assert error.value.submission_unknown
            assert not error.value.retryable
            assert "upstream diagnostic" not in error.value.message

    asyncio.run(run())


def test_status_transport_failure_is_retryable_without_recreating_job():
    async def run():
        def handle(req):
            assert req.method == "GET"
            assert req.url.path == "/api/v1/predictions/private-job/result"
            raise httpx.ConnectError("connection diagnostic", request=req)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(ProviderError) as error:
                await MuAPIProvider("secret", 3, client=client).get_status("private-job")
            assert error.value.retryable and not error.value.submission_unknown
            assert "diagnostic" not in error.value.message

    asyncio.run(run())


@pytest.mark.parametrize(
    "payload",
    [
        {},
        None,
        [],
        {"status": "unexpected"},
        {"status": "completed", "outputs": []},
        {"status": "completed", "outputs": ["invalid-url"]},
    ],
)
def test_uncertain_poll_payload_cannot_become_terminal_failure(payload):
    with pytest.raises(ProviderError) as error:
        MuAPIProvider("secret", 3).normalize_result(payload)
    assert error.value.retryable and not error.value.submission_unknown
    assert error.value.code == "GENERATION_STATUS_UNAVAILABLE"


def test_unreadable_poll_response_remains_retryable():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, text="invalid-json"))
        ) as client:
            with pytest.raises(ProviderError) as error:
                await MuAPIProvider("secret", 3, client=client).get_status("job")
            assert error.value.retryable and not error.value.submission_unknown

    asyncio.run(run())
