"""Gemini transcription normalization + durable transcribe job leasing/retry."""

import json

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Asset, Base, SubtitleJob, SubtitleProject
from app.providers.base import ProviderError
from app.subtitles import jobs, service
from app.subtitles.providers import GeminiTranscriptionProvider, normalize_transcript
from app.subtitles.schemas import SubtitleProjectCreate


# --- normalize_transcript: pure validation, no network involved ---------------------


def valid_raw():
    return {
        "language": "en",
        "cues": [
            {
                "text": "Hello there",
                "words": [
                    {"text": "Hello", "startMs": 0, "endMs": 400},
                    {"text": "there", "startMs": 420, "endMs": 800},
                ],
            },
            {
                "text": "Welcome",
                "words": [{"text": "Welcome", "startMs": 1000, "endMs": 1400}],
            },
        ],
    }


def test_normalize_accepts_valid_word_timestamps():
    transcript = normalize_transcript(valid_raw())
    assert transcript.language == "en"
    assert len(transcript.cues) == 2
    assert transcript.cues[0]["text"] == "Hello there"
    assert transcript.cues[0]["startMs"] == 0
    assert transcript.cues[0]["endMs"] == 800
    assert transcript.cues[0]["words"][0]["text"] == "Hello"


def test_normalize_rejects_missing_cues_but_accepts_a_silent_video():
    with pytest.raises(ProviderError) as exc:
        normalize_transcript({"language": "en"})
    assert exc.value.retryable is True
    assert normalize_transcript({"language": "en", "cues": []}).cues == []


def test_normalize_rejects_missing_word_timing():
    raw = valid_raw()
    del raw["cues"][0]["words"][0]["endMs"]
    with pytest.raises(ProviderError):
        normalize_transcript(raw)


def test_normalize_rejects_out_of_order_word_timing():
    raw = valid_raw()
    raw["cues"][0]["words"][1]["startMs"] = 100  # before the first word's startMs
    with pytest.raises(ProviderError):
        normalize_transcript(raw)


def test_normalize_rejects_a_cue_below_the_minimum_length():
    raw = valid_raw()
    raw["cues"][0]["words"] = [{"text": "Hi", "startMs": 0, "endMs": 100}]
    with pytest.raises(ProviderError):
        normalize_transcript(raw)


def test_normalize_rejects_negative_or_reversed_timing():
    raw = valid_raw()
    raw["cues"][0]["words"][0]["startMs"] = -5
    with pytest.raises(ProviderError):
        normalize_transcript(raw)


# --- GeminiTranscriptionProvider: HTTP transport and malformed responses ------------


def gemini_body(raw):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(raw)}]}}]}


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def post(self, url, json, params, timeout):
        self.calls.append({"url": url, "json": json, "params": params})
        reply = next(self.responses)
        if isinstance(reply, Exception):
            raise reply
        status, body = reply
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))


@pytest.mark.asyncio
async def test_provider_normalizes_a_valid_response():
    client = Client([(200, gemini_body(valid_raw()))])
    provider = GeminiTranscriptionProvider("key", "gemini-2.5-flash", 20_000_000, client=client)
    transcript = await provider.transcribe(b"audio-bytes", "audio/aac")
    assert transcript.cues[0]["text"] == "Hello there"
    assert client.calls[0]["params"] == {"key": "key"}


@pytest.mark.asyncio
async def test_provider_rejects_malformed_json_as_retryable():
    body = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
    client = Client([(200, body)])
    provider = GeminiTranscriptionProvider("key", "gemini-2.5-flash", 20_000_000, client=client)
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"audio", "audio/aac")
    assert exc.value.retryable is True


@pytest.mark.asyncio
async def test_provider_maps_timeout_to_a_retryable_transport_error():
    client = Client([httpx.TimeoutException("timed out")])
    provider = GeminiTranscriptionProvider("key", "gemini-2.5-flash", 20_000_000, client=client)
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"audio", "audio/aac")
    assert exc.value.retryable is True
    assert exc.value.code == "TRANSCRIPTION_TRANSPORT_ERROR"


@pytest.mark.asyncio
async def test_provider_retries_a_5xx_but_not_a_4xx():
    client = Client([(503, {}), (400, {})])
    provider = GeminiTranscriptionProvider("key", "gemini-2.5-flash", 20_000_000, client=client)
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"audio", "audio/aac")
    assert exc.value.retryable is True
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"audio", "audio/aac")
    assert exc.value.retryable is False


@pytest.mark.asyncio
async def test_provider_rejects_oversized_audio_without_a_network_call():
    client = Client([])
    provider = GeminiTranscriptionProvider("key", "gemini-2.5-flash", 10, client=client)
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"way more than ten bytes of audio", "audio/aac")
    assert exc.value.retryable is False
    assert client.calls == []


# --- Durable transcribe job: leasing, retry, terminal failure, restart recovery -----


class FakeProvider:
    """Deterministic stand-in; counts calls so a test can assert Gemini is invoked once."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    async def transcribe(self, audio, mime_type):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def ready_transcript():
    return normalize_transcript(valid_raw())


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            Asset(
                id="clip",
                user_id="alice",
                role="source_video",
                mime_type="video/mp4",
                file_name="clip.mp4",
                size_bytes=1,
                storage_key="alice/clip",
                duration_seconds=10.0,
            )
        )
        session.commit()
        yield session


@pytest.mark.asyncio
async def test_successful_transcription_marks_the_project_ready(db, monkeypatch):
    project = service.create(
        db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16"), "key"
    )
    job = db.scalar(select(SubtitleJob).where(SubtitleJob.project_id == project.id))
    monkeypatch.setattr(jobs, "_source_audio", lambda db, asset_id, **kwargs: _async_result((b"audio", "audio/aac")))

    provider = FakeProvider([ready_transcript()])
    claimed = jobs.claim(db, "worker-1")
    assert claimed.id == job.id
    await jobs.run_transcribe(db, claimed, provider)

    refreshed = service.owned(db, "alice", project.id)
    assert refreshed.status == "ready"
    assert refreshed.language == "en"
    assert refreshed.cues[0]["text"] == "Hello there"
    assert claimed.submission_state == "done"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_retryable_failure_releases_the_lease_for_another_attempt(db, monkeypatch):
    project = service.create(
        db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16"), "key"
    )
    monkeypatch.setattr(jobs, "_source_audio", lambda db, asset_id, **kwargs: _async_result((b"audio", "audio/aac")))
    provider = FakeProvider(
        [ProviderError("TRANSCRIPTION_INVALID", "bad", retryable=True), ready_transcript()]
    )

    job = jobs.claim(db, "worker-1")
    await jobs.run_transcribe(db, job, provider)
    assert job.submission_state == "pending"  # released, not terminal
    assert job.lease_owner is None
    assert service.owned(db, "alice", project.id).status == "transcribing"

    # A restart (or the same worker after the backoff) can claim and finish it.
    job.next_run_at = job.next_run_at.replace(year=2000)
    job = jobs.claim(db, "worker-2")
    await jobs.run_transcribe(db, job, provider)
    assert service.owned(db, "alice", project.id).status == "ready"
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_exhausted_retries_mark_the_project_failed_not_stuck(db, monkeypatch):
    project = service.create(
        db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16"), "key"
    )
    monkeypatch.setattr(jobs, "_source_audio", lambda db, asset_id, **kwargs: _async_result((b"audio", "audio/aac")))
    error = ProviderError("TRANSCRIPTION_INVALID", "always bad", retryable=True)
    provider = FakeProvider([error] * jobs.MAX_ATTEMPTS)

    job = db.scalar(select(SubtitleJob).where(SubtitleJob.project_id == project.id))
    for _ in range(jobs.MAX_ATTEMPTS):
        job.next_run_at = job.next_run_at.replace(year=2000)
        claimed = jobs.claim(db, "worker")
        await jobs.run_transcribe(db, claimed, provider)

    refreshed = service.owned(db, "alice", project.id)
    assert refreshed.status == "failed"
    assert refreshed.error["code"] == "TRANSCRIPTION_INVALID"
    assert job.submission_state == "done"


@pytest.mark.asyncio
async def test_a_repeated_idempotency_key_never_invokes_the_provider_twice(db, monkeypatch):
    body = SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16")
    service.create(db, "alice", body, "same-key")
    service.create(db, "alice", body, "same-key")
    # One project, one job row, regardless of how many times create() is retried.
    assert db.scalar(select(SubtitleJob)).id is not None
    from sqlalchemy import func

    assert db.scalar(select(func.count()).select_from(SubtitleProject)) == 1
    assert db.scalar(select(func.count()).select_from(SubtitleJob)) == 1


@pytest.mark.asyncio
async def test_a_project_no_longer_transcribing_is_left_untouched(db, monkeypatch):
    """Restart recovery: a job racing a prior attempt that already finished is a no-op."""
    project = service.create(
        db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16"), "key"
    )
    project.status = "ready"
    db.flush()
    monkeypatch.setattr(jobs, "_source_audio", lambda db, asset_id, **kwargs: _async_result((b"audio", "audio/aac")))
    provider = FakeProvider([ready_transcript()])
    job = jobs.claim(db, "worker")
    await jobs.run_transcribe(db, job, provider)
    assert provider.calls == 0
    assert job.submission_state == "done"


async def _async_result(value):
    return value


# --- Gemini through OpenRouter -----------------------------------------------------


class OpenRouterClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def post(self, url, json, headers, timeout):
        self.calls.append({"url": url, "json": json, "headers": headers})
        reply = next(self.responses)
        if isinstance(reply, Exception):
            raise reply
        status, body = reply
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))


def openrouter_body(raw, finish="stop"):
    return {
        "choices": [{"message": {"content": json.dumps(raw)}, "finish_reason": finish}],
        "usage": {"cost": 0.0004},
    }


def openrouter_provider(responses, **overrides):
    from app.subtitles.providers import OpenRouterGeminiTranscriptionProvider

    client = OpenRouterClient(responses)
    options = {"api_key": "key", "model": "google/gemini-2.5-flash", "max_audio_bytes": 20_000_000, **overrides}
    return OpenRouterGeminiTranscriptionProvider(client=client, **options), client


@pytest.mark.asyncio
async def test_openrouter_sends_audio_inline_with_a_strict_schema_and_normalizes():
    provider, client = openrouter_provider([(200, openrouter_body(valid_raw()))])
    transcript = await provider.transcribe(b"aac-bytes", "audio/aac")
    assert transcript.cues[0]["text"] == "Hello there"
    call = client.calls[0]
    assert call["url"].endswith("/chat/completions")
    assert call["headers"]["Authorization"] == "Bearer key"
    audio = call["json"]["messages"][0]["content"][1]
    assert audio["type"] == "input_audio" and audio["input_audio"]["format"] == "aac"
    assert call["json"]["response_format"]["json_schema"]["strict"] is True


@pytest.mark.asyncio
async def test_openrouter_rejects_truncated_output_and_invalid_timing_as_retryable():
    provider, _ = openrouter_provider([(200, openrouter_body(valid_raw(), finish="length"))])
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"aac", "audio/aac")
    assert exc.value.retryable is True

    raw = valid_raw()
    raw["cues"][0]["words"][1]["startMs"] = 100
    provider, _ = openrouter_provider([(200, openrouter_body(raw))])
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"aac", "audio/aac")
    assert exc.value.code == "TRANSCRIPTION_INVALID"


@pytest.mark.asyncio
async def test_openrouter_low_balance_is_not_retried_and_missing_key_makes_no_call():
    provider, _ = openrouter_provider([(402, {"error": {"message": "credits"}})])
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"aac", "audio/aac")
    assert exc.value.code == "TRANSCRIPTION_BALANCE_LOW" and exc.value.retryable is False

    provider, client = openrouter_provider([], api_key="")
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"aac", "audio/aac")
    assert exc.value.code == "TRANSCRIPTION_UNCONFIGURED" and client.calls == []


def test_factory_selects_openrouter_with_the_shared_key():
    from app.config import Settings
    from app.subtitles.providers import OpenRouterGeminiTranscriptionProvider, transcription_provider

    cfg = Settings(_env_file=None, subtitle_transcription_provider="openrouter", openrouter_api_key="k")
    provider = transcription_provider(cfg)
    assert isinstance(provider, OpenRouterGeminiTranscriptionProvider)
    assert provider.model == "google/gemini-2.5-flash" and provider.api_key == "k"



@pytest.mark.asyncio
async def test_a_long_video_is_transcribed_in_parts_on_one_timeline(db, monkeypatch):
    from app.subtitles.providers import NormalizedTranscript

    project = service.create(db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="16:9"), "long")
    project.duration_ms = 12 * 60 * 1000  # three 5-minute parts: 0-5, 5-10, 10-12
    db.flush()
    requested = []

    async def audio(db, asset_id, start_ms=0, length_ms=None, cache=None):
        requested.append((start_ms, length_ms))
        return b"audio", "audio/aac"

    monkeypatch.setattr(jobs, "_source_audio", audio)

    class PartProvider:
        async def transcribe(self, audio, mime_type):
            words = [{"id": "w", "text": "Hi", "startMs": 1000, "endMs": 1600}]
            return NormalizedTranscript("pl", [{"id": "c", "startMs": 1000, "endMs": 1600, "text": "Hi", "words": words}])

    job = jobs.claim(db, "worker")
    await jobs.run_transcribe(db, job, PartProvider())
    assert requested == [(0, 300000), (300000, 300000), (600000, 120000)]
    assert project.status == "ready" and project.language == "pl"
    assert [c["startMs"] for c in project.cues] == [1000, 301000, 601000]
    assert project.cues[2]["words"][0]["endMs"] == 601600


@pytest.mark.asyncio
async def test_parts_whose_timing_overlaps_are_rejected_not_repaired(db, monkeypatch):
    from app.subtitles.providers import NormalizedTranscript

    project = service.create(db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="16:9"), "overlap")
    project.duration_ms = 6 * 60 * 1000
    db.flush()
    monkeypatch.setattr(jobs, "_source_audio", lambda db, asset_id, **kwargs: _async_result((b"a", "audio/aac")))
    replies = iter([
        # The first part claims speech past its own 5-minute end, into the next part.
        NormalizedTranscript("pl", [{"id": "a", "startMs": 299000, "endMs": 302000, "text": "x", "words": []}]),
        NormalizedTranscript("pl", [{"id": "b", "startMs": 500, "endMs": 1200, "text": "y", "words": []}]),
    ])

    class Provider:
        async def transcribe(self, audio, mime_type):
            return next(replies)

    job = jobs.claim(db, "worker")
    job.attempts = jobs.MAX_ATTEMPTS
    await jobs.run_transcribe(db, job, Provider())
    assert project.status == "failed" and project.error["code"] == "TRANSCRIPTION_INVALID"


# --- Whisper through OpenRouter ----------------------------------------------------


def whisper_word(text, start, end):
    return {"word": " " + text, "start": start, "end": end}


def test_group_words_breaks_at_sentences_and_pauses_and_keeps_whisper_timing():
    from app.subtitles.providers import group_words

    cues = group_words([
        whisper_word("Nazywam", 4.16, 4.74),
        whisper_word("się", 4.74, 4.84),
        whisper_word("Stanisław.", 4.84, 5.58),
        whisper_word("Od", 5.58, 5.72),
        whisper_word("e", 8.42, 8.60),
        whisper_word("-commerce", 8.60, 9.12),
        whisper_word("Twój", 9.80, 10.0),
    ])
    assert [cue["text"] for cue in cues] == ["Nazywam się Stanisław.", "Od e-commerce", "Twój"]
    assert cues[0]["words"][0] == {"text": "Nazywam", "startMs": 4160, "endMs": 4740}
    assert cues[1]["words"][-1] == {"text": "e-commerce", "startMs": 8420, "endMs": 9120}
    assert cues[2]["words"][0]["startMs"] == 9800


def test_group_words_caps_long_phrases_and_never_emits_an_invalid_cue():
    from app.subtitles.providers import group_words

    words = [whisper_word(f"słowo{i}", i * 0.3, i * 0.3 + 0.25) for i in range(30)]
    words.append(whisper_word("koniec", 9.0, 9.0))  # zero-length word from the API
    transcript = normalize_transcript({"language": "pl", "cues": group_words(words)})
    assert len(transcript.cues) > 1
    assert all(len(cue["text"]) <= 70 for cue in transcript.cues)
    assert all(cue["endMs"] - cue["startMs"] <= 6000 for cue in transcript.cues)
    assert transcript.cues[-1]["words"][-1]["endMs"] > transcript.cues[-1]["words"][-1]["startMs"]


class MultipartClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def post(self, url, data, files, headers, timeout):
        self.calls.append({"url": url, "data": data, "files": files, "headers": headers})
        status, body = next(self.responses)
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))


def whisper_provider(responses, **overrides):
    from app.subtitles.providers import OpenRouterWhisperTranscriptionProvider

    client = MultipartClient(responses)
    options = {"api_key": "key", "model": "openai/whisper-large-v3-turbo", "max_audio_bytes": 20_000_000, **overrides}
    return OpenRouterWhisperTranscriptionProvider(client=client, **options), client


@pytest.mark.asyncio
async def test_whisper_uploads_mp3_asks_for_word_timing_and_builds_cues():
    body = {
        "text": "Hello there.",
        "language": "en",
        "words": [whisper_word("Hello", 0.0, 0.4), whisper_word("there.", 0.42, 0.8)],
        "usage": {"cost": 0.00005},
    }
    provider, client = whisper_provider([(200, body)])
    transcript = await provider.transcribe(b"mp3-bytes", "audio/mpeg")
    assert transcript.language == "en"
    assert [(c["text"], c["startMs"], c["endMs"]) for c in transcript.cues] == [("Hello there.", 0, 800)]
    call = client.calls[0]
    assert call["url"].endswith("/audio/transcriptions")
    assert call["data"]["response_format"] == "verbose_json"
    assert "word" in call["data"]["timestamp_granularities[]"]
    assert call["files"]["file"][0] == "audio.mp3"


@pytest.mark.asyncio
async def test_whisper_speech_without_word_timing_is_retried_and_silence_is_empty():
    provider, _ = whisper_provider([(200, {"text": "Hello there."})])
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"mp3", "audio/mpeg")
    assert exc.value.code == "TRANSCRIPTION_INVALID" and exc.value.retryable is True

    provider, _ = whisper_provider([(200, {"text": "", "words": []})])
    assert (await provider.transcribe(b"mp3", "audio/mpeg")).cues == []


@pytest.mark.asyncio
async def test_whisper_low_balance_is_final_and_missing_key_or_aac_makes_no_call():
    provider, _ = whisper_provider([(402, {})])
    with pytest.raises(ProviderError) as exc:
        await provider.transcribe(b"mp3", "audio/mpeg")
    assert exc.value.code == "TRANSCRIPTION_BALANCE_LOW" and exc.value.retryable is False

    provider, client = whisper_provider([], api_key="")
    with pytest.raises(ProviderError):
        await provider.transcribe(b"mp3", "audio/mpeg")
    provider, client = whisper_provider([])
    with pytest.raises(ProviderError):
        await provider.transcribe(b"aac", "audio/aac")
    assert client.calls == []


def test_factory_selects_whisper_with_the_shared_key():
    from app.config import Settings
    from app.subtitles.providers import OpenRouterWhisperTranscriptionProvider, transcription_provider

    cfg = Settings(_env_file=None, subtitle_transcription_provider="whisper", openrouter_api_key="k")
    provider = transcription_provider(cfg)
    assert isinstance(provider, OpenRouterWhisperTranscriptionProvider)
    assert provider.model == "openai/whisper-large-v3-turbo" and provider.api_key == "k"


def test_claim_can_be_limited_to_one_job_kind(db):
    service.create(db, "alice", SubtitleProjectCreate(sourceAssetId="clip", aspectRatio="9:16"), "k")
    assert jobs.claim(db, "renderer", kinds=("render",)) is None
    assert jobs.claim(db, "transcriber", kinds=("transcribe",)).kind == "transcribe"
