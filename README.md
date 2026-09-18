# Storyflow — Claude creative planning and OpenRouter video

The local creative director uses the server-side Anthropic Messages API (`CHAT_PROVIDER=claude`, `creative-director-v3`). Storyflow stores conversation history and validated plans; no Codex login or subprocess is required. Configure a server-only `ANTHROPIC_API_KEY` to enable real planning. Missing credentials fail closed; there is no silent fallback to simulation.

Planning uses bounded preparation, optional research, a final structured answer and at most one repair within four total rounds. Candidate self-scores pass a deterministic gate; they do not establish measured creative quality. The real evaluation matrix has not been run. Video uses one OpenRouter route, Alibaba Wan 3.0: 15 seconds, 480p, native audio and supplied visual references. Apply and Generate Video remain separate actions.

Start instructions and limits: [local chat](docs/LOCAL_CHAT.md). Architecture: [creative director](docs/CREATIVE_DIRECTOR.md), [chat](docs/CHAT_ARCHITECTURE.md). Historical verification reports describe the implementation at their recorded date, not the current transport or account balance.

# Forma — AI UGC workspace

A standalone Next.js / FastAPI video-creation SaaS scaffold with provider-neutral contracts, private assets, a transaction-safe credit ledger, and recoverable asynchronous generation. The approved reference is `docs/references/dashboard-reference.png`. Implementation scope is `docs/BUILD_BRIEF.md`.

## Local development

Node 22+ and pnpm 10; Python 3.11+ with uv; PostgreSQL and Redis. Local development is explicitly authorized; no production deployment has been performed.

```sh
cp .env.example .env
docker compose up -d
pnpm install --frozen-lockfile
```

Create `apps/web/.env.local`:

```dotenv
NEXT_PUBLIC_USE_MOCK_API=true
API_INTERNAL_URL=http://127.0.0.1:8000
```

```sh
pnpm dev
```

Open http://127.0.0.1:3000. Browser mock mode works independently of FastAPI and uses nonmonetary credits and explicitly labeled test footage. Mock history is browser-local; it is not a real AI generation or payment. The supplied original hero portrait is saved in `docs/references/hero-photo-original.png` and used by the frontend.

## Backend and connected development

From `apps/api`:

```sh
uv venv --python 3.11
uv pip install --python .venv/bin/python -e '.[test]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a separate terminal from the same directory:

```sh
.venv/bin/python -m app.worker
```

To test frontend → real local API → mock provider, change `apps/web/.env.local` to `NEXT_PUBLIC_USE_MOCK_API=false` and add `AUTH_MODE=mock`; restart Next dev. The server-only auth bypass is accepted only by Next development runtime. Configure backend `APP_ENV=development`, `AUTH_MODE=mock`, `CHAT_PROVIDER=mock`, `VIDEO_PROVIDER=mock`. The API still enforces user scoping and uses the database ledger. Never use mock authentication or storage in production.

Docker is a supplied local startup path, not proof that it was run. See `docs/VERIFICATION.md` for the actual machine/runtime checks and any native PostgreSQL fallback used.

## Real integrations

- Creative planning: server-only `ANTHROPIC_API_KEY`, `CHAT_PROVIDER=claude`; see [LOCAL_CHAT.md](docs/LOCAL_CHAT.md) for limits and configuration. Anthropic planning costs are separate from the video credit ledger.

- Supabase: set frontend public URL/anon key and backend `SUPABASE_URL`; use `AUTH_MODE=supabase`. Enable email/Google in Supabase and allow `http://127.0.0.1:3000/auth/callback` for local OAuth. Production requires its own HTTPS callback URL. Browser session tokens are validated by FastAPI; no service-role key is public.
- R2/S3: set `STORAGE_MODE=s3`, private bucket, endpoint, region, and access credentials. Provider input assets must be reachable using bounded signed HTTPS URLs.
- Real video: configure OpenRouter as documented in CHAT_ARCHITECTURE.md. Only pre-submission cancellation is supported; no blind resubmission.
- Text prompts: set `TEXT_PROVIDER=openai`, `TEXT_PROVIDER_ENABLED=true`, server-only `OPENAI_API_KEY` and `PROMPT_MODEL` to opt into the Responses adapter. Local default is deterministic; paid text calls were not tested.
- Stripe: set secret key, webhook secret and `STRIPE_CATALOG_JSON` catalog; use hosted Checkout/Portal. Register `/api/webhooks/stripe` with signed events. Never grant credits from a browser redirect. See `apps/api/README.md` for catalog shape and settlement limitations.

`.env.example` enumerates settings. Do not commit `.env`, signed URLs, credentials, or actual customer uploads. Package lockfile is checked in for reproducible installs.

## Checks

```sh
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
```

E2E expects the local web server already running; install Chromium with `pnpm --filter @ugc/web exec playwright install chromium`, or configure `PLAYWRIGHT_CHANNEL=chrome` to use installed Chrome. Backend tests and migration commands are in `apps/api/README.md`. Actual results and limitations are recorded in `docs/VERIFICATION.md`; commands here are instructions, not claims of passing checks.

## Architecture map

- `apps/web`: App Router, small client interaction components, typed mock/HTTP services, auth callback and protected routes.
- `apps/api`: auth, schemas, persistence, ledger, assets, product resolution, prompt generation, billing and durable worker.
- `apps/api/app/providers`: private model registry, Claude planning adapter, mock adapters, and OpenRouter video boundary with normalized results.
- `packages/contracts`: public TypeScript API shapes; `packages/ui`: styled accessible primitives; `packages/config`: shared TypeScript settings.
- `docs`: product/design/API/backend/database decisions, pinned third-party review and visual evidence.

No timeline, node canvas, social publishing, team/campaign management or analytics functionality is implemented. Sidebar placeholders are explicitly marked as outside the current MVP.

## Phase2A — imported render templates

Only `reactvideoeditor/remotion-templates` is imported, at the audited commit in `docs/audits/rve-source.json`. The template code is MIT-declared; Remotion and its native renderer have separate license terms recorded in `docs/THIRD_PARTY.md`.

```sh
pnpm templates:rve:import
pnpm templates:rve:validate
pnpm templates:rve:previews
pnpm templates:rve:stats
pnpm templates:rve:test
```

Import records are disabled until actual validation succeeds. Create shows recommended entries; `/templates` offers URL-persisted filters. Render templates use schema inputs and an estimate directly, without generating an AI prompt. Real deterministic rendering requires connected API mode; the browser simulation does not fabricate imported renders. The API and existing worker must run from the same checkout with root Node dependencies and generated template artifacts accessible. See `docs/RVE_BACKEND_VERIFICATION.md` and `docs/audits/PHASE2A_REPORT.md` for exact execution evidence and limitations.
