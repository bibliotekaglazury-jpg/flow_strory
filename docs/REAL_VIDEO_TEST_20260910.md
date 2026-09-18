# One authorized real-video attempt — 2026-09-10

Result: **failed before provider job acceptance — HTTP 402**. No generated MP4 exists; no substitute or mock video was saved as a real result. No second paid submission was made.

- Storyflow generation: `e06364b0-4fc1-4903-878e-3ce493c7985b`.
- Provider: existing OpenRouter adapter, `bytedance/seedance-2.0-mini`.
- Request: 15 seconds, 9:16, Polish (pl-PL), native audio, two owned reference images.
- Creative plan: real Codex validation session `9e0e03ac-5af2-44b5-961a-28cad2cac495`, applied through existing Prompt/quote/job/worker boundaries.
- Provider request ID: none returned.
- API error: VIDEO_SERVICE_BALANCE_LOW (adapter maps HTTP 402 to this code).
- Attempt elapsed time: 6.08 seconds.
- Storyflow estimated credits: 45; reserved 45; refunded 45; charged 0. Ledger entries verified directly in the database.
- Generation record persisted as failed, with accepted planning/recipe evidence in its snapshot. No output asset exists.
- MP4 video/audio streams, duration and creative quality: not assessable without an output file.
- Provider monetary price for this request: unavailable; account totals are not per-generation cost.

## Read-only account check after the rejection

GET /api/v1/credits and GET /api/v1/key both returned 200 using the project's configured key, without printing or storing the key.

- Total credits: USD 10.
- Total usage: USD 10.047505731.
- Difference: approximately USD -0.04751.
- Key spending limit: null (no separately configured key cap reported).

The configured account is exhausted at the time of this check. These totals do not establish which historical operations spent the balance.

## HTTPS relay verification and closure

User explicitly approved a temporary relay limited to two test photos. Each file was retrieved through HTTPS and its SHA-256 matched the local owned source. Other asset keys and /api/credits returned 404. No browser/API/auth routes were exposed.

The local resolver had stale/absent DNS results; public DNS-over-HTTPS resolved the tunnel, while TLS hostname/certificate verification stayed enabled. An existing global Cloudflare config returned an empty 404; the successful test used an isolated empty config and minimal environment. Existing Cloudflare configuration was not modified.

Relay and tunnel terminated after the failed attempt. Port 8011 has no listening service. No persistent public asset origin was configured in the app.

Private attempt state and one-attempt guard: `.local/single-video-smoke-funded-20260910.json`. `submitAttempted=true` prevents another paid submission. Review plans remain in the DB and `.local/creative-director-validation.json`.

Next requirement: available OpenRouter balance and explicit authorization for a new generation attempt; permanent HTTPS storage is still needed for general frontend usage. This test's authorization has been consumed by the single attempted submission.
