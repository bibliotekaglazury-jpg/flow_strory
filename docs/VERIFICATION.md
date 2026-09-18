# Current authority — restored Codex chat (2026-09-10)

**Chat: current ChatGPT/Codex subscription through CodexLocalAdapter and codex exec/resume. Video only: OpenRouter → Seedance 2.0 Mini, 15s native audio.** The user explicitly reversed the OpenAI Responses chat change. No OpenAI API key transfer or Responses integration is required for chat. The experimental adapter/test launcher were removed; previous experiment notes below are historical and superseded. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md).

Current single-model results and limitations: [SINGLE_MODEL_VERIFICATION.md](SINGLE_MODEL_VERIFICATION.md). Historical results below are not a live acceptance claim for the new route.

# Local implementation report — 2026-09-10

## Architecture and repository

Next.js App Router + TypeScript + Tailwind, Radix/shadcn-style primitives with custom tokens. Typed public contracts and interchangeable browser mock/HTTP services. FastAPI owns identity, input validation, quotes, ledger and jobs; PostgreSQL persists jobs, a separate leased worker calls private provider adapters. S3/R2 is the configured live binary boundary; local signed storage is development-only. Supabase and Stripe provide external auth and billing.

```text
AGENTS.md
README.md
.env.example
docker-compose.yml
apps/
  web/
    app/                 # creation, auth callback, library, billing, placeholders
    components/          # shell, hero, reusable inputs
    features/create/     # workspace, preview, collections
    hooks/               # creation orchestration
    services/            # typed HTTP/mock, estimates, retry and polling
    public/              # original hero, SVG lettering, labeled test media
    tests/               # unit, browser, visual capture
  api/
    app/                 # auth, schemas, routes, SQLAlchemy, worker
      providers/         # registry, Auto routing, mock, MuAPI, optional text
      services/          # assets, products, prompts, generations, ledger, billing
      fixtures/          # original simulation MP4s
    alembic/             # schema migrations
    tests/               # domain, security, providers, PostgreSQL integration
packages/
  contracts/
  ui/
  config/
skills/frontend-design/SKILL.md
docs/
  UI_SYSTEM.md
  PRODUCT_SPEC.md
  API_CONTRACTS.md
  REFERENCES.md
  IMPLEMENTATION_RULES.md
  DECISIONS.md
  BUILD_BRIEF.md
  BACKEND_ARCHITECTURE.md
  GENERATION_ARCHITECTURE.md
  DATABASE_SCHEMA.md
  THIRD_PARTY.md
  BACKEND_VERIFICATION.md
  VERIFICATION.md
  references/            # preserved user sources
  verification/          # rendered screenshots and measurements
```

## Sources, endpoints, database and providers

See [THIRD_PARTY.md](THIRD_PARTY.md) for four pinned repository/license inspections and exact installed direct JavaScript dependency inventory. No source from the reference repositories was copied. No unlicensed nanoart code reused.

API endpoints: POST /api/assets, POST /api/product/resolve, GET /api/templates, GET /api/models, POST /api/prompts/generate, GET/POST /api/generations, GET /api/generations/:id, POST /api/generations/:id/cancel, GET /api/credits, GET /api/billing/summary, POST /api/billing/checkout, POST /api/billing/portal, POST /api/webhooks/stripe; liveness/readiness health routes. Exact request and response shapes: API_CONTRACTS.md and packages/contracts/index.ts.

Database tables: users, projects, assets, templates, providers, models, prompts, generations, generation_jobs, generation_outputs, credit_accounts, credit_transactions, credit_quotes, subscriptions, webhook_events. Relations: DATABASE_SCHEMA.md. Templates remain business concepts, independent of models. Auto routes capability-supported inputs server-side; model/provider identifiers never select presentation behavior. Implemented video adapters: durable mock and MuAPI; text: deterministic local template and explicitly enabled OpenAI Responses adapter. ImageProvider is a future interface, not an implemented extra product feature. Real provider tests use injected transports; no paid calls occurred.

## Startup and configuration

See README.md for browser-only mock mode and connected local startup; BACKEND_VERIFICATION.md records the actual native PostgreSQL commands because Docker was unavailable. Frontend http://127.0.0.1:3000; API http://127.0.0.1:8000. Run API and worker separately. Use .env.example for database, Redis, Supabase, storage, Stripe, video/text and external media-tool settings. No real external keys are included. Mock footage and credits are explicitly nonmonetary simulation.

## Verification evidence

- Frontend production build passed (Next.js 16.3.4); TypeScript build checks passed.
- Final `pnpm lint` and `pnpm typecheck`: passed after portrait integration and dependency version pinning.
- Connected HTTP browser E2E on localhost3000 → FastAPI8000 → PostgreSQL/worker: 2 passed in1.4min; upload, prompt editing, estimated credits, completed video, download link, persistent history and mobile keyboard navigation.
- Frontend unit tests: 11 passed across five files.
- Browser mock production-server E2E: 2 passed, including upload → generated editable prompt → generation → download → persisted history, and keyboard/mobile overflow test.
- Backend: 50 passed including real PostgreSQL integration, migrations and ledger concurrency. Ruff passed. Details and limitations: BACKEND_VERIFICATION.md.
- Visual screenshots captured at 1222, 1440, 1280, 1024, 768 and 390 CSS pixels with device scale 1. No page JavaScript exceptions or horizontal document overflow. See verification/visual-measurements.json and create-{width}.png.
- Screenshot set includes browser mock desktop and connected API mobile after the environment transition; both use the supplied portrait. Compare equivalent states before numerical image-diff claims.

## Reference comparison and remaining work

Compared rendered desktop and mobile screenshots with REF-001. At1222, workspace begins x198/y342, width729.625; preview x937.625/width264.359, matching the observed reference layout anchors. Workspace height604 versus reference approximately561 because explicit Generate Prompt and eight templates consume more vertical space. This is not a pixel-accuracy claim.

The original portrait SHA-256 is `3ea0c89f656b7fcd3d8911ca4bf5d07a02c57a9a52beade79c1e71ab6b90e098`; source, docs copy and public copy match. The portrait is integrated unchanged, layered with approved cyan/amber/lime background and SVG lettering. Font choices approximate the supplied serif/UI typography. SVG uses system script fonts and is not outlined. Hero copy and neutral Forma branding differ intentionally from Luma; omitted logos, engagement metrics and fake customer outputs are not implemented features. Preview/history are empty until real local jobs exist. Template photographs are still missing: browser mock uses labeled original SVG test assets; HTTP templates currently have no photographs. Mobile adapts navigation and stacks the workspace/preview because no mobile reference was supplied.

Remaining: approve actual template imagery, final brand/copy and exact lettering; validate credentialed Supabase/S3/Stripe/video/text flows; configure real prices and media retention; build the supplied Docker image and verify Redis delivery; freeze backend deployment dependencies. No production deploy performed. Source remains an uncommitted local Git worktree on feat/ugc-mvp.

## Operational preflight

CBM MCP was exposed; initial UGC graph contained16nodes/14edges. Query: `frontend provider generation templates`; no meaningful existing frontend code was present. Subsequent MCP transport failed; CLI list_projects/search_graph/detect_changes succeeded with the verified UGC root. The four external source inspections are pinned in THIRD_PARTY.md. No Cerebro/VPS path was used as UGC runtime. Local source is a Git worktree; no commit, push or deploy performed.

Initial dev-browser attempts exceeded the short30-second test deadline under compilation load. The deadline was raised, then the same flow passed against the production mock server and connected local development API. Chrome required sandbox escalation after a launch failure. The final screenshot set has no JavaScript page errors or document overflow; visual fidelity limitations above remain explicit.

## Claude Creative Director — 2026-09-11

Local implementation, offline/backend/browser/PostgreSQL tests and screenshots are recorded in
[the Claude verification report](verification/CLAUDE_CREATIVE_DIRECTOR_20260911.md).
Real planning validation remains blocked by the required Anthropic workspace ID; this is not a production or creative-quality sign-off. No paid video generation was run.

## Collapsible desktop sidebar — 2026-09-12

Verified locally against the current Create screen. The desktop sidebar measures
178 px expanded and 64 px collapsed. Hovering a navigation icon restores the
178 px labelled state and it remains open after pointer exit; the toggle is the
only collapse action. At 390×844 the toggle is hidden, the existing horizontal
navigation remains, and document overflow is false.

Screenshots: `verification/sidebar-expanded-1440.png`,
`verification/sidebar-collapsed-1440.png`,
`verification/sidebar-hover-expanded-1440.png`, and
`verification/sidebar-mobile-390.png`. Compared with REF-001 for the existing
expanded composition; collapsed mode is the user-approved extension and has no
separate supplied reference. Targeted Playwright test, frontend lint, typecheck,
and production build passed. No VPS deployment was performed.

Production deployment was subsequently authorized and completed on 2026-09-12.
Only `apps/web/components/shell.tsx` and `apps/web/app/globals.css` were synced
to `/opt/storyflow/app`; only the `web` image was rebuilt and its container
recreated. Runtime verification: internal HTTP 200 and the sidebar Playwright
scenario passed against the running VPS container through an SSH tunnel. The
public hostname returned the configured 401 authentication challenge to an
unauthenticated curl request.
