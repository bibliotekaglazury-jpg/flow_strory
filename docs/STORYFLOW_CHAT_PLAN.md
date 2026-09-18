# Local Storyflow chat — implementation plan and audit

2026-09-10. Authorized local development only. Extend the existing FastAPI service,
SQLAlchemy/Alembic schema, typed web service boundary and Create workspace.
No deployment, auth replacement, credit-ledger replacement or separate agent backend.

## Read-only audit

CBM CLI fallback: UGC project, 1716 nodes / 3963 edges; query
`prompts generations Workspace provider`; no detected changes at preflight.
Existing integration points: use-creation.ts, workspace.tsx, Services HTTP/mock
adapters, prompts service, provider registry and leased generation worker.
Codex CLI 0.153.4 reports ChatGPT login. Credentials were not read.
Installed CLI exposes JSONL, output-schema, resume, ignore-user-config and feature
switches. Read-only alone does not prohibit tool calls. Local execution must disable
tool features and reject tool events; live enablement requires verified controls.
Native Codex resume persistence versus the no-reasoning-retention requirement is an
open clarification; application storage must never contain reasoning or raw events.

Higgsfield CLI was absent. Official CLI repository audited at
8827135df7601667f66cd36ce84cf72106d690c4; actual MIT LICENSE inspected.
This checkout contains documentation/distribution scripts, not CLI implementation.
JSON submit/status shapes and capabilities must be verified against installed CLI;
README examples alone do not establish a worker response contract.

## Sequence

1. Canonical strict Pydantic recipe and generated JSON Schema/TypeScript contracts.
2. Owned persisted chat sessions/messages, provider-neutral API, mock provider and
   local Codex adapter. Serial turns, timeouts, cancellation, sanitized errors.
3. Apply a stored recipe to a validated creative snapshot and ordinary Prompt record.
   Invalidate old quotes. Chat/apply never create video jobs or spend video credits.
4. assistant-ui primitives using external-store runtime inside Prompt, AI Chat default,
   Manual preserved, compact recipe summary and explicit Apply action.
5. Audited Higgsfield CLI adapter in existing worker; exact capability/cost validation,
   no synchronous paid request in API handlers, no blind retry of unknown submission.
6. Mock contract/lifecycle/UI tests; lint/typecheck/build; desktop/mobile screenshots.
   Real smoke calls require explicit authorization and follow successful mocks.

## Contract decisions

Sessions are user-scoped and store only visible messages, validated recipe and opaque
provider thread metadata. Apply accepts the current creative inputs and a recipe
revision to prevent applying a stale answer. Recipe scenes are planning data, not
an editor or automatic multi-job stitching. Unsupported durations/quality remain
subject to existing quote validation. No product-image visual analysis is claimed
when the conversation provider only receives textual context.

Sources: https://developers.openai.com/codex/config-reference/ ;
https://github.com/higgsfield-ai/cli ;
https://www.assistant-ui.com/docs/runtimes/custom/external-store .
