# Local video chat verification — 2026-09-10

## Delivered and verified

- assistant-ui 0.15.18 external-store runtime inside existing Prompt; AI Chat default,
  Manual preserved, visible messages, composer, recipe summary and explicit Apply.
- Six provider-neutral FastAPI endpoints with owned SQLAlchemy chat sessions and
  Alembic 0003. Apply creates a normal Prompt/fingerprint and refreshes the quote;
  chat never submits or charges for video generation.
- Canonical strict Pydantic recipe, exported JSON Schema and TypeScript contracts.
- MockChatProvider; CodexLocalAdapter subprocess/JSONL transport with isolated
  runtime, read-only/tool-feature configuration, sanitized environment, validation,
  timeout and cancellation. Native-history gate remains closed.
- Higgsfield CLI 1.1.24 installed and OAuth help audited. MockHiggsfieldProvider
  tested through existing worker. Live adapter deliberately unavailable and NOT
  registered; a complete live submit/poll/staging/storage implementation is pending.

## Checks

| Check | Result |
| --- | --- |
| Codex login status | Logged in using ChatGPT; no credential files inspected |
| Backend suite with local PostgreSQL | 99 passed; one existing expensive real Remotion render deselected |
| Existing dependency warnings | Two Starlette/AnyIO deprecations; not test failures |
| Backend Ruff | Passed |
| Alembic upgrade head / check | Passed on verified local UGC cluster at 127.0.0.1:55432; no schema drift |
| Running local HTTP API | Create/send/read/delete mock conversation passed; credit balance unchanged; test conversation deleted |
| Frontend lint | Passed |
| Frontend TypeScript | Passed |
| Frontend Vitest | 38 passed |
| Browser mock E2E | 5 passed: chat/apply/persistence/reset, mobile, error recovery, manual/video/history, keyboard layout |
| Production frontend build | `pnpm --filter @ugc/web exec next build --webpack` passed; no deployment |
| Browser render errors / overflow | None at 1440×1100 and 390×844 |
| Local runtime at handoff | Frontend 127.0.0.1:3000 returned HTTP 200; updated FastAPI listening on 127.0.0.1:8000 in mock mode |
| New server/provider identifiers in browser build | Targeted scan found none of CodexLocalAdapter, HiggsfieldLocalAdapter, OPENAI_API_KEY, CODEX_HOME, S3_SECRET_ACCESS_KEY in `.next/static`; this is not an exhaustive secret audit |
| Real Codex inference | Not run; native history policy and explicit live smoke authorization unresolved |
| Higgsfield OAuth login | Browser flow started but timed out; workspace/catalog read failed |
| Real Higgsfield video | Not run; no external account credits spent by generation tests |

Backend command: from apps/api, existing local DATABASE_URL and FFMPEG_PATH,
`RUN_POSTGRES_TESTS=1 .venv/bin/python -m pytest -q -k 'not remotion_real'`.
Browser command: `pnpm --filter @ugc/web exec playwright test tests/chat.spec.ts tests/create.spec.ts --workers=1`.
Every browser `/api` request is intercepted by per-test mock services; tests cannot
reach a paid provider even if the developer's frontend normally uses HTTP.
The MockHiggsfield worker test stores actual original fixture bytes through a
test storage adapter, then verifies Asset/Output, completion, ledger settlement
and history projection. It is not evidence of a real Higgsfield-generated MP4.

## Visual comparison

Compared with REF-001 in docs/references/dashboard-reference.png and the existing
Create composition. Dark shell, white workspace, lime primary CTA, hero portrait,
uploads, business template imagery, right portrait preview and lower collections
remain. Chat adds content height inside Prompt; the original mockup has no chat,
so pixel equivalence of that new area is not claimed. Mobile stacks the workspace
and preview as the existing responsive interpretation; no mobile mockup supplied.

Evidence: empty-1440.png, recipe-1440.png, empty-390.png, recipe-390.png and
measurements.json. User/assistant messages have semantic author labels and a
restrained user-message background. Mobile composer text remains 16px. Browser
dev indicator/focus overlay may appear in full-page development screenshots; they
are not product decoration. Existing template View-all wrapping was not redesigned.

## Remaining gate

This phase is incomplete as a real Codex + Higgsfield integration. Resolve Codex
native history retention (exec resume persists provider-owned thread history),
verify hard tool isolation and perform the authorized Codex smoke. Complete
Higgsfield OAuth, inspect the intended workspace/model/cost and exact JSON schemas,
then finish worker-only live submission, media staging, polling and private output
ingestion and run the authorized real generation. Do not enable an unverified
provider or substitute API-key access. See docs/LOCAL_CHAT.md.

## Live chat repair — 2026-09-10 (supersedes earlier unresolved history gate)

User explicitly allowed native Codex resume history, with reasoning excluded from
Storyflow storage/logs/browser. Codex CLI 0.153.4 reports ChatGPT authentication.
The local API now runs with CHAT_PROVIDER=codex_local via
scripts/chat/run-local-api.sh; no OpenAI Platform credentials configured.

Root causes beyond mock configuration: CLI emits nonfatal startup notices as error
items; disabled-code-host notice was incorrectly rejected as a tool event. User
skills also remained discoverable. Exact notice allowlisted, all unknown errors and
tool events rejected, skill overrides point to SKILL.md files (folder paths failed).
No model tools executed in successful smoke; this is not a universal sandbox proof.
Cancel-after-failure no longer poisons a subsequent attempt; changed providers cannot
restore old demo sessions as live conversations.

Live verification: one clarification + resume scenario (two model turns), then one
HTTP integration turn through 127.0.0.1:3000. Earlier failed startups aborted before
an assistant answer and are not counted as successful conversations or guaranteed
free calls. Native history is owned by Codex; no attempt to read it was made.
Gibberish produced recipe=null plus a question. Follow-up Russian product brief
produced a schema-valid recipe with four scenes totalling 15 seconds, same thread.
HTTP integration returned 200, simulated=false, persisted two visible messages;
credit balance unchanged, no video generation submitted.

Verification results:
- Backend: 103 passed, 1 deselected (existing costly real Remotion render), 2 existing
  Starlette deprecation warnings, with local PostgreSQL and installed FFmpeg path.
- Earlier PostgreSQL run lacked FFMPEG_PATH and failed a worker-output test; rerun
  with the documented local binary passed. No ledger or worker implementation changed.
- Frontend unit tests: 38 passed.
- Playwright chat/Create: 5 passed, mocked API; sandbox browser-launch failure resolved
  by running authorized local Chrome outside that restriction.
- Frontend lint/typecheck: passed. Changed Python Ruff: passed.
- Production webpack build: passed; build only, no deployment.
- Mock regression screenshots: empty/recipe at 1440 and 390 widths.
- Actual HTTP-persisted chat: live-1440.png, live-390.png; Manual:
  manual-1440.png, manual-390.png. No browser errors or horizontal overflow;
  no demo label in live chat. live-measurements.json records checks.

Visual review against REF-001 and prior chat extension: shell/workspace/preview,
fonts and accent retained. Full-plan details intentionally expand vertically;
summary remains collapsed by default. Manual now explains the brief, and missing
image/URL is shown beside the disabled action. Internal JSON field names replaced
by readable labels. Mobile screenshots include development overlay/focus artifacts;
no claim of pixel identity or production runtime.

Higgsfield workspace query still failed after network escalation and requested
OAuth login. Official browser login was started; interactive approval pending.
No real Higgsfield render, sales readiness, production authentication, billing or
deployment is claimed. See LOCAL_CHAT.md for remaining integration boundaries.

Final regression addition: Manual's hidden chat, explanatory text and disabled
missing-product action passed. The chat suite rerun was 3 passed/1 failed because
Next dev briefly rendered an Unexpected end of JSON input overlay; the unchanged
failed scenario passed on isolated rerun (18.8s). This was a transient local runtime
observation, not a fully diagnosed code defect; do not hide it as a clean single run.
Combined coverage: six distinct chat/Create scenarios passed across runs.

Final OAuth outcome: official `pnpm exec higgsfield auth login` timed out without
browser approval. No Higgsfield tokens or credentials were read, and no generation
was submitted. User must complete an interactive login before the live adapter audit
can proceed. Final frontend HTTP status 200; final lint/typecheck passed.

## Manual block removal — 2026-09-10

At the user's explicit request, removed the pictured campaign brief textarea,
label, helper paragraph and Generate Prompt action from Manual. AI Chat's composer
is hidden in Manual; an existing applied production prompt remains editable.
Updated earlier Manual specifications and adapted E2E generation flow to chat/apply.
Six chat/Create E2E tests passed; frontend lint and typecheck passed.
Visual comparison: manual-removed-1440.png (viewport 1440×1000) and
manual-removed-390.png (390×1000) inspected against the user's requested removal and
REF-001 hierarchy. No brief element, chat not visible, no page errors or overflow.
Existing upload/style/settings controls retain their placement; workspace height
shrinks naturally. Mobile screenshot retains the Next development indicator.

Production webpack build after Manual removal: passed.
