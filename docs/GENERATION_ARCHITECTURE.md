# Current creative-director phase — 2026-09-10

See [CREATIVE_DIRECTOR.md](CREATIVE_DIRECTOR.md) for the current ContextBundle → CreativePlan → VideoPlan → canonical recipe flow. Auto is the default creative format; text-only offers are supported. New plans contain one 15-second clip and native audio. The existing Codex subscription transport is retained pending clarification of the conflicting Responses instruction. No OpenAI API switch or deployment has occurred. Earlier phase notes below are historical where they conflict.

# Current authority — restored Codex chat (2026-09-10)

**Chat: current ChatGPT/Codex subscription through CodexLocalAdapter and codex exec/resume. Video only: OpenRouter → Seedance 2.0 Mini, 15s native audio.** The user explicitly reversed the OpenAI Responses chat change. No OpenAI API key transfer or Responses integration is required for chat. The experimental adapter/test launcher were removed; previous experiment notes below are historical and superseded. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md).

# Current single-model MVP amendment — 2026-09-10

Still look previews (`POST /api/try-on`, `app/services/try_on.py`) are a separate bounded
path added 2026-09-13: one synchronous OpenRouter Images call, no quote, job or worker,
credits debited directly on success. They do not touch the video route below. See
`docs/DECISIONS.md`.

Canonical recipe → compile_recipe → existing quote/job/worker → OpenRouter Seedance 2.0 Mini 15s native audiovisual output. Unknown acceptance is reconciled without blind resubmission. Technical audio/duration validation precedes completion/storage. No TTS or other real route.

This amendment supersedes conflicting older phase notes below. Details: [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md).

# Generation architecture

## Domain contract

VideoProvider: generate(request, idempotency_key), get_status(provider_job_id), cancel(provider_job_id), normalize_result(payload), estimate_cost(request). ImageProvider additionally exposes edit; no image-generation product surface is added. Adapter errors normalize to application errors. Provider job IDs are server-only.

Registry models have application ID, provider key, vendor model ID, media type, supported duration/ratio/resolution combinations, audio/image/video/reference/first/last-frame flags, enabled state, priority, and configured cost rules. Public projections omit vendor IDs. Auto filters enabled/available candidates by exact inputs and settings, then sorts suitable capabilities, priority and configured price. Templates recommend capabilities but never specify provider IDs. Unsupported combinations are rejected, not silently shortened or stretched.

## Lifecycle

1. Validate session, asset ownership/readiness, template, prompt freshness and exact capabilities.
2. Estimate server-configured credits; return expiring quote. Zero/free mock costs must never leak into live mode.
3. Submit with idempotency key; lock account, validate quote, reserve, create generation and durable generation_job atomically.
4. Worker acquires expiring lease. Persist a submission intent before remote call; store remote ID immediately after acceptance. Recover unknown submit outcomes safely instead of automatically creating another charge.
5. Poll with bounded backoff or use authenticated provider webhook. Persist progress only when real; null is indeterminate. Retry transport reads, not paid creation calls.
6. Validate output URL/media and copy to private owned storage with bounded downloads. Mark completed and settle actual credits at or below accepted quote in one transaction.
7. Failure/cancellation releases reservation once. Terminal records are immutable except asset URL refresh. Duplicate webhook and worker retries cannot double settle.

## Provider launch limits

Mock provider must complete a real playable test fixture through queued → generating → completed; fixture is explicitly labeled a simulation. Real provider adapter is selected after official API research; no guessed capability claims. 20/30 second support is a launch constraint if the selected real model cannot provide it. Do not add hidden multi-scene stitching merely to mask that mismatch. Remote cancellation may be unsupported: app cancellation semantics must explain this and not imply remote billing is undone.

## Future scenes

Templates may store ordered beats with relative durations and first/last-frame capability preferences. Generation request snapshots can add a versioned scene plan later. Current MVP is a single generation request/result with no canvas, timeline, or manual storyboard editor.
