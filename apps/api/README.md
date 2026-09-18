# UGC API

FastAPI + SQLAlchemy/PostgreSQL, private S3/R2 (or development filesystem), Supabase JWT, Stripe hosted billing, and a database-leased generation worker. Local runtime is authorized; deployment and paid provider calls are not.

From this directory, using Python 3.12+:

```sh
uv venv --python 3.12
uv pip install --python .venv/bin/python -e '.[test]'
cp ../../.env.example ../../.env
# Start the root Compose PostgreSQL/Redis services first.
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000 --no-access-log
# Separate terminal, same environment:
.venv/bin/python -m app.worker
.venv/bin/pytest -q
.venv/bin/ruff check app tests
```

Video validation uses an external LGPL-only ffprobe, configured with FFPROBE_PATH (default: ffprobe). When it is absent, FFMPEG_PATH selects an external FFmpeg that actually decodes one frame and supplies bounded format/duration/dimension metadata; undecodable files are rejected. The Dockerfile builds FFmpeg 7.1.1 from the official release with GPL/nonfree/autodetected third-party codecs disabled and a pinned SHA-256. No PyAV/imageio-ffmpeg bundled codec wheel is distributed. Mock output uses nine committed, original test-pattern fixtures with exact duration and ratio. Mock completion serves an actual H.264 test-pattern video of the requested duration/ratio, named `development-simulation.mp4`; it is simulation output, not AI-generated advertising.

Configuration defaults are explicit development mock auth, development private filesystem storage and mock video. Nondevelopment configuration rejects these modes. Live provider selection requires `VIDEO_PROVIDER=muapi`, `MUAPI_ENABLED=true`, `MUAPI_API_KEY`, and a positive `VIDEO_CREDITS_PER_SECOND`. Development mock credits are nonmonetary. `AUTH_MODE=supabase` verifies asymmetric Supabase tokens against its issuer/JWKS/audience. `.env` is loaded from the repository root when commands run from this directory.

Stripe catalog example (configured server-side; never expose Stripe price IDs to presentation):

```json
{"starter":{"label":"Starter","stripePriceId":"price_CONFIGURED","credits":1000,"mode":"payment"}}
```

Set this JSON in `STRIPE_CATALOG_JSON`; configure `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`. Checkout/Portal remain unavailable without configuration. Credits are granted from signed paid events, line items are checked against server catalog, and operation keys deduplicate both repeated events and different events for the same checkout/invoice. Subscription invoices with ambiguous multiple lines or proration do not automatically grant credits; policy needs business configuration.

The DB owns jobs; no Redis message is needed for recovery. Worker leases expire after 120 seconds. The worker commits submission intent before calling a provider and stores the accepted remote ID before polling. If submission outcome is unknown for a provider without idempotency, the job enters internal `reconciliation`, remains active, retains its reservation and is not blindly resubmitted. Operators must verify the remote outcome before repairing that record; there is no unsafe automatic refund/retry. Poll/download failures retry with bounds and then require reconciliation.

Cancellation currently succeeds only before submission intent is committed. Later cancellation returns truthful `409 CANCELLATION_UNAVAILABLE`. Generation/quote/asset/prompt ownership is server-enforced. Quotes bind the full estimate and prompt provenance, expire after ten minutes, and can be accepted once. Per-user idempotency keys bind the exact submitted body. Credits reserve with job admission and settle/release atomically under locks; a PostgreSQL trigger makes the ledger append-only.

`GET /health/live` checks the process; `/health/ready` checks DB connectivity. All API errors use the shared safe envelope and request ID. Product fetching validates each redirect and pins DNS-resolved public IPs with original TLS SNI to prevent rebinding. Upload bodies are bounded in application code; production ingress must also enforce request-size limits before multipart buffering.

MVP catalog/registry definitions are versioned application data in `services/prompts.py` and `providers/registry.py`, mirrored by seeded templates/models/providers tables for audited catalog versions. Runtime provider availability remains fail-closed environment configuration; database seed rows never enable paid calls. A minimal projects ownership table exists without a project-management UI. The database also stores users, accounts, ledger, assets, prompts, quotes, generations, jobs, outputs, subscriptions and webhook events. Schema changes run through Alembic, never API startup.

Unit tests use SQLite for fast domain checks; PostgreSQL migration/concurrency verification must be recorded separately because SQLite does not prove row-lock semantics. No credentialed live provider or Stripe transaction is part of the test suite.

The bundled original MP4 fixtures are media outputs, not FFmpeg application code. For redistribution of Docker images, preserve LGPL notices and provide the matching FFmpeg source archive/build instructions (official source https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz, SHA-256 733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1). Docker build is not verified when no Docker daemon is available.

Prompt generation uses `TEXT_PROVIDER=deterministic` in development. Credential-ready live text generation requires `TEXT_PROVIDER=openai`, `TEXT_PROVIDER_ENABLED=true`, `OPENAI_API_KEY`, and `PROMPT_MODEL`. The adapter calls the official Responses API with a fixed server instruction and puts all campaign/page content in user-input data, disables tools and response storage, bounds output, and never silently retries or falls back after an uncertain paid request. No real text-provider call was made during verification.
