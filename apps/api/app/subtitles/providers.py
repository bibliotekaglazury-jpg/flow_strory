"""Gemini structured-output transcription: word timestamps only, normalized into cues.

Provider identifiers and raw model output never reach a response; only validated,
normalized cues do. A malformed or incomplete response is a retryable failure — the
server never invents timing to paper over a bad provider answer.
"""

import base64
import json
import logging
from typing import Protocol
from uuid import uuid4

import httpx

from app.providers.base import ProviderError

log = logging.getLogger(__name__)

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MIN_CUE_MS = 250

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "language": {"type": "STRING"},
        "cues": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    "words": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "text": {"type": "STRING"},
                                "startMs": {"type": "INTEGER"},
                                "endMs": {"type": "INTEGER"},
                            },
                            "required": ["text", "startMs", "endMs"],
                        },
                    },
                },
                "required": ["text", "words"],
            },
        },
    },
    "required": ["cues"],
}

PROMPT = (
    "Transcribe the spoken words in this audio. Return every cue as a short natural "
    "phrase (roughly one breath group or clause) with its words and each word's exact "
    "start and end time in integer milliseconds from the start of the audio. Only "
    "report words you can actually hear; never estimate or invent timing for words you "
    "are not confident about. If there is no speech, return an empty cues list."
)


class NormalizedTranscript:
    __slots__ = ("language", "cues")

    def __init__(self, language, cues):
        self.language = language
        self.cues = cues


def normalize_transcript(raw: dict) -> NormalizedTranscript:
    """Pure validation/normalization: same rules regardless of which provider answered.

    Raises ProviderError(retryable=True) for anything structurally wrong — missing
    timing, out-of-order words, a cue collapsed below the minimum length — rather than
    silently repairing it, since a repaired timestamp is an invented one.
    """
    cues_in = raw.get("cues") if isinstance(raw, dict) else None
    if not isinstance(cues_in, list):
        raise ProviderError(
            "TRANSCRIPTION_INVALID", "The transcription had no usable cues.", retryable=True
        )
    # An empty list is a real answer: a video with no speech opens with no captions rather
    # than failing after every retry.
    cues = []
    cursor_end = -1
    for cue in cues_in:
        words_in = cue.get("words") if isinstance(cue, dict) else None
        text = cue.get("text") if isinstance(cue, dict) else None
        if not isinstance(words_in, list) or not words_in or not isinstance(text, str) or not text.strip():
            raise ProviderError(
                "TRANSCRIPTION_INVALID", "A cue was missing its text or words.", retryable=True
            )
        words = []
        word_end_cursor = -1
        for word in words_in:
            if not isinstance(word, dict):
                raise ProviderError(
                    "TRANSCRIPTION_INVALID", "A word entry was malformed.", retryable=True
                )
            start, end, word_text = word.get("startMs"), word.get("endMs"), word.get("text")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or not isinstance(word_text, str)
                or not word_text.strip()
                or start < 0
                or end <= start
                or start < word_end_cursor
            ):
                raise ProviderError(
                    "TRANSCRIPTION_INVALID",
                    "A word had missing, out-of-order, or invalid timing.",
                    retryable=True,
                )
            word_end_cursor = end
            words.append({"id": str(uuid4()), "text": word_text, "startMs": start, "endMs": end})
        cue_start, cue_end = words[0]["startMs"], words[-1]["endMs"]
        if cue_end - cue_start < MIN_CUE_MS or cue_start < cursor_end:
            raise ProviderError(
                "TRANSCRIPTION_INVALID",
                "A cue was too short or overlapped the previous one.",
                retryable=True,
            )
        cursor_end = cue_end
        cues.append(
            {"id": str(uuid4()), "startMs": cue_start, "endMs": cue_end, "text": text.strip(), "words": words}
        )
    language = raw.get("language") if isinstance(raw.get("language"), str) else None
    return NormalizedTranscript(language, cues)


class TranscriptionProvider(Protocol):
    async def transcribe(self, audio: bytes, mime_type: str) -> NormalizedTranscript: ...


class GeminiTranscriptionProvider:
    key = "gemini"

    def __init__(self, api_key, model, max_audio_bytes, client=None):
        self.api_key, self.model, self.max_audio_bytes, self.client = (
            api_key,
            model,
            max_audio_bytes,
            client,
        )

    async def transcribe(self, audio: bytes, mime_type: str) -> NormalizedTranscript:
        if not self.api_key:
            raise ProviderError(
                "TRANSCRIPTION_UNCONFIGURED", "Transcription is not configured.", retryable=False
            )
        if len(audio) > self.max_audio_bytes:
            raise ProviderError(
                "TRANSCRIPTION_UNSUPPORTED",
                "This video's audio track is too long for transcription in this phase.",
                retryable=False,
            )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": PROMPT},
                        {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(audio).decode()}},
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }
        url = f"{BASE}/{self.model}:generateContent"

        async def send(client):
            return await client.post(url, json=payload, params={"key": self.api_key}, timeout=170)

        try:
            if self.client:
                response = await send(self.client)
            else:
                async with httpx.AsyncClient() as client:
                    response = await send(client)
        except httpx.HTTPError:
            raise ProviderError(
                "TRANSCRIPTION_TRANSPORT_ERROR", "The transcription service could not be reached.", retryable=True
            ) from None
        if not response.is_success:
            log.warning("gemini_transcription_rejected status=%s", response.status_code)
            retryable = response.status_code in (429, 500, 502, 503, 504)
            raise ProviderError(
                "TRANSCRIPTION_SERVICE_ERROR", "The transcription service could not respond.", retryable=retryable
            )
        try:
            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            raw = json.loads(text)
        except (KeyError, IndexError, ValueError, json.JSONDecodeError):
            raise ProviderError(
                "TRANSCRIPTION_INVALID", "The transcription response could not be read.", retryable=True
            ) from None
        return normalize_transcript(raw)


class MockTranscriptionProvider:
    """Local development only; the config guard forbids it outside development.

    Returns one fixed cue so the editor has something to show without a paid call.
    """

    key = "mock"

    async def transcribe(self, audio: bytes, mime_type: str) -> NormalizedTranscript:
        return normalize_transcript(
            {
                "language": "en",
                "cues": [
                    {
                        "text": "Simulated transcript for local development",
                        "words": [
                            {"text": "Simulated", "startMs": 0, "endMs": 500},
                            {"text": "transcript", "startMs": 550, "endMs": 1100},
                            {"text": "for", "startMs": 1150, "endMs": 1300},
                            {"text": "local", "startMs": 1350, "endMs": 1700},
                            {"text": "development", "startMs": 1750, "endMs": 2500},
                        ],
                    }
                ],
            }
        )


OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
# OpenRouter names the container, not the MIME type.
AUDIO_FORMATS = {"audio/aac": "aac", "audio/mpeg": "mp3", "audio/wav": "wav", "audio/ogg": "ogg", "audio/flac": "flac"}

OPENROUTER_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "cues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "words": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "startMs": {"type": "integer"},
                                "endMs": {"type": "integer"},
                            },
                            "required": ["text", "startMs", "endMs"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["text", "words"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["language", "cues"],
    "additionalProperties": False,
}


class OpenRouterGeminiTranscriptionProvider:
    """The same Gemini transcription through the existing OpenRouter account, so no separate
    Google key is needed. Validation is identical: normalize_transcript never invents timing."""

    key = "openrouter"

    def __init__(self, api_key, model, max_audio_bytes, client=None):
        self.api_key, self.model, self.max_audio_bytes, self.client = api_key, model, max_audio_bytes, client

    async def transcribe(self, audio: bytes, mime_type: str) -> NormalizedTranscript:
        if not self.api_key:
            raise ProviderError(
                "TRANSCRIPTION_UNCONFIGURED", "Transcription is not configured.", retryable=False
            )
        if len(audio) > self.max_audio_bytes:
            raise ProviderError(
                "TRANSCRIPTION_UNSUPPORTED",
                "This video's audio track is too long for transcription in this phase.",
                retryable=False,
            )
        audio_format = AUDIO_FORMATS.get(mime_type)
        if not audio_format:
            raise ProviderError(
                "TRANSCRIPTION_UNSUPPORTED", "This audio format cannot be transcribed.", retryable=False
            )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "input_audio",
                            "input_audio": {"data": base64.b64encode(audio).decode(), "format": audio_format},
                        },
                    ],
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "transcript", "strict": True, "schema": OPENROUTER_SCHEMA},
            },
            "usage": {"include": True},
        }

        async def send(client):
            return await client.post(
                OPENROUTER_BASE,
                json=payload,
                headers={"Authorization": "Bearer " + self.api_key},
                timeout=170,
            )

        try:
            if self.client:
                response = await send(self.client)
            else:
                async with httpx.AsyncClient() as client:
                    response = await send(client)
        except httpx.HTTPError:
            raise ProviderError(
                "TRANSCRIPTION_TRANSPORT_ERROR", "The transcription service could not be reached.", retryable=True
            ) from None
        if not response.is_success:
            log.warning("openrouter_transcription_rejected status=%s", response.status_code)
            if response.status_code == 402:
                raise ProviderError(
                    "TRANSCRIPTION_BALANCE_LOW", "Transcription is temporarily unavailable.", retryable=False
                )
            retryable = response.status_code in (408, 429, 500, 502, 503, 504)
            raise ProviderError(
                "TRANSCRIPTION_SERVICE_ERROR", "The transcription service could not respond.", retryable=retryable
            )
        try:
            body = response.json()
            choice = body["choices"][0]
            if choice.get("finish_reason") not in (None, "stop"):
                raise ValueError("incomplete")
            raw = json.loads(choice["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError(
                "TRANSCRIPTION_INVALID", "The transcription response could not be read.", retryable=True
            ) from None
        cost = (body.get("usage") or {}).get("cost")
        log.warning("subtitle_transcription_usage model=%s cost_usd=%s", self.model, cost)
        return normalize_transcript(raw)


OPENROUTER_TRANSCRIPTIONS = "https://openrouter.ai/api/v1/audio/transcriptions"
AUDIO_EXTENSIONS = {"audio/mpeg": "mp3", "audio/wav": "wav", "audio/ogg": "ogg", "audio/flac": "flac"}
SENTENCE_END = (".", "!", "?", "…")
CUE_PAUSE_MS = 600
CUE_MAX_CHARS = 70
CUE_SOFT_CHARS = 40
CUE_MAX_MS = 6000


def group_words(words_in) -> list[dict]:
    """Whisper word timestamps -> phrase cues: a cue ends at a sentence end, a real pause,
    a comma once the line is long enough, or the hard length/duration cap.

    Whisper's word boundaries are trusted as-is; the only adjustments are the ones that keep
    them valid (a zero-length word gets 10ms, a word never starts before the previous ends)
    and gluing a detached "-suffix" back onto its word ("e" + "-commerce").
    """
    words = []
    for word in words_in if isinstance(words_in, list) else []:
        if not isinstance(word, dict):
            continue
        text = str(word.get("word") or "").strip()
        start, end = word.get("start"), word.get("end")
        if not text or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        start_ms = max(round(start * 1000), words[-1]["endMs"] if words else 0)
        end_ms = max(round(end * 1000), start_ms + 10)
        if words and text.startswith("-") and start_ms - words[-1]["endMs"] < 100:
            words[-1]["text"] += text
            words[-1]["endMs"] = end_ms
            continue
        words.append({"text": text, "startMs": start_ms, "endMs": end_ms})

    cues, current = [], []
    for index, word in enumerate(words):
        current.append(word)
        following = words[index + 1] if index + 1 < len(words) else None
        if following is None:
            break
        chars = len(" ".join(w["text"] for w in current))
        span = word["endMs"] - current[0]["startMs"]
        long_enough = span >= MIN_CUE_MS
        if long_enough and (
            word["text"].endswith(SENTENCE_END)
            or following["startMs"] - word["endMs"] >= CUE_PAUSE_MS
            or (word["text"].endswith((",", ";", ":")) and chars >= CUE_SOFT_CHARS)
            or chars + 1 + len(following["text"]) > CUE_MAX_CHARS
            or following["endMs"] - current[0]["startMs"] > CUE_MAX_MS
        ):
            cues.append(current)
            current = []
    if current:
        short = current[-1]["endMs"] - current[0]["startMs"] < MIN_CUE_MS
        if cues and short and current[0]["startMs"] - cues[-1][-1]["endMs"] < CUE_PAUSE_MS:
            cues[-1].extend(current)
        else:
            cues.append(current)
    if cues and cues[-1][-1]["endMs"] - cues[-1][0]["startMs"] < MIN_CUE_MS:
        cues[-1][-1]["endMs"] = cues[-1][0]["startMs"] + MIN_CUE_MS
    return [{"text": " ".join(w["text"] for w in cue), "words": cue} for cue in cues]


class OpenRouterWhisperTranscriptionProvider:
    """Whisper through the existing OpenRouter key. Unlike an LLM it measures word timing
    from the audio itself, so captions stay on the speech instead of drifting."""

    key = "whisper"

    def __init__(self, api_key, model, max_audio_bytes, client=None):
        self.api_key, self.model, self.max_audio_bytes, self.client = api_key, model, max_audio_bytes, client

    async def transcribe(self, audio: bytes, mime_type: str) -> NormalizedTranscript:
        if not self.api_key:
            raise ProviderError(
                "TRANSCRIPTION_UNCONFIGURED", "Transcription is not configured.", retryable=False
            )
        if len(audio) > self.max_audio_bytes:
            raise ProviderError(
                "TRANSCRIPTION_UNSUPPORTED",
                "This video's audio track is too long for transcription in this phase.",
                retryable=False,
            )
        extension = AUDIO_EXTENSIONS.get(mime_type)
        if not extension:
            raise ProviderError(
                "TRANSCRIPTION_UNSUPPORTED", "This audio format cannot be transcribed.", retryable=False
            )
        data = {
            "model": self.model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": ["word", "segment"],
        }
        files = {"file": (f"audio.{extension}", audio, mime_type)}

        async def send(client):
            return await client.post(
                OPENROUTER_TRANSCRIPTIONS,
                data=data,
                files=files,
                headers={"Authorization": "Bearer " + self.api_key},
                timeout=170,
            )

        try:
            if self.client:
                response = await send(self.client)
            else:
                async with httpx.AsyncClient() as client:
                    response = await send(client)
        except httpx.HTTPError:
            raise ProviderError(
                "TRANSCRIPTION_TRANSPORT_ERROR", "The transcription service could not be reached.", retryable=True
            ) from None
        if not response.is_success:
            log.warning("whisper_transcription_rejected status=%s", response.status_code)
            if response.status_code == 402:
                raise ProviderError(
                    "TRANSCRIPTION_BALANCE_LOW", "Transcription is temporarily unavailable.", retryable=False
                )
            retryable = response.status_code in (408, 429, 500, 502, 503, 504)
            raise ProviderError(
                "TRANSCRIPTION_SERVICE_ERROR", "The transcription service could not respond.", retryable=retryable
            )
        try:
            body = response.json()
            words = body["words"] if "words" in body else None
            if words is None and (body.get("text") or "").strip():
                # Speech without word timing would force us to invent it; retry instead.
                raise ValueError("no word timestamps")
        except (KeyError, TypeError, ValueError):
            raise ProviderError(
                "TRANSCRIPTION_INVALID", "The transcription response could not be read.", retryable=True
            ) from None
        cost = (body.get("usage") or {}).get("cost")
        log.warning("subtitle_transcription_usage model=%s cost_usd=%s", self.model, cost)
        language = body.get("language") if isinstance(body.get("language"), str) else None
        return normalize_transcript({"language": language, "cues": group_words(words or [])})


def transcription_provider(cfg):
    if cfg.subtitle_transcription_provider == "whisper":
        return OpenRouterWhisperTranscriptionProvider(
            cfg.openrouter_api_key, cfg.openrouter_whisper_model, cfg.subtitle_max_audio_bytes
        )
    if cfg.subtitle_transcription_provider == "openrouter":
        return OpenRouterGeminiTranscriptionProvider(
            cfg.openrouter_api_key, cfg.openrouter_transcription_model, cfg.subtitle_max_audio_bytes
        )
    if cfg.subtitle_transcription_provider == "gemini":
        return GeminiTranscriptionProvider(
            cfg.gemini_api_key, cfg.gemini_transcription_model, cfg.subtitle_max_audio_bytes
        )
    return MockTranscriptionProvider()
