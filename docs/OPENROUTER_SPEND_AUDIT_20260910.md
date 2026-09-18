# OpenRouter spending audit — 2026-09-10

Read-only investigation; no new generation requests were submitted during this audit.

## Verified evidence

- Current account API: total credits USD 10; total usage USD 10.047505731.
- Current key API: lifetime usage USD 10.047505731; daily, weekly, and monthly usage each reported 0. These aggregates do not identify a charged request, and their apparent discrepancy needs account Activity data.
- Local PostgreSQL contains two real `ugc-video-v1` jobs: `fa16d901-1ec6-4d38-8f4c-10c1ddd6ed61` and `e06364b0-4fc1-4903-878e-3ce493c7985b`. Both failed; both lack a provider request ID; both have zero charged Storyflow credits. Latest attempt returned HTTP 402. No successful real video is recorded in this local database.
- Local ledger credits are not USD provider billing and cannot establish actual account charges.
- GET /api/v1/activity returned HTTP 403: only management keys can fetch account activity. No management key was sought or created. GET /api/v1/videos returned 404 and supplied no history.
- Model catalog confirms `bytedance/seedance-2.0-mini`, 720p and 15 seconds supported, native audio supported. Live pricing_skus: video_tokens 0.0000035; video_tokens_without_audio 0.0000035; video_tokens_with_video_input 0.0000021 USD per token. This alone does not prove a per-video amount; no authoritative token count or charge for an accepted job was obtained.

## Conclusion and remaining evidence

The USD 10.047505731 is cumulative account/key usage, NOT verified cost of the latest test or a single 15-second video. Attribution to Storyflow, another application, or a particular model remains unverified. A USD 0.50 maximum is also unverified.

Need account owner Activity export (request time, model, request ID, cost) from https://openrouter.ai/activity to reconcile actual charges. Do not request secrets. Do not top up or retry paid generation as a substitute for resolving this discrepancy.

CBM preflight: MCP exposed and used; CLI fallback not used; project Users-stas-Documents-UGC, 2357 nodes / 5967 edges. Query: OpenRouterVideoProvider generate normalize_result Job Generation. Returned provider generate/normalize_result and protocol/mock symbols. detect_changes reported no tracked changes (untracked baseline).
