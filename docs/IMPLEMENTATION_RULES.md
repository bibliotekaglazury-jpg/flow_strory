# Current local planning architecture — 2026-09-11

Chat uses the server-side Anthropic Messages API through `ClaudeCreativeDirectorAdapter`, with prompt version `creative-director-v3`. Storyflow's database owns conversation history; no Codex executable, subscription login, native thread history or OpenAI Responses chat transport is used. `CHAT_PROVIDER=claude` is the default; explicit `mock` remains available for offline development. This supersedes the earlier chat-provider amendments below.

A bounded turn has preparation, optional public research, final structured planning and at most one repair, within four total model rounds and configured token/time/cost limits. Owned images use native image blocks; reviewed allowlisted skills and sourced page facts are untrusted reference data. Internal candidate scores are model self-assessments, not an independent critic or evidence of measured advertising quality. Real matrix evaluation remains pending.

Video is unchanged: the existing quote/job/worker/storage/ledger flow uses OpenRouter Seedance 2.0 Mini, 15 seconds, 480p, native audio. Apply does not submit video or reserve video credits. Local development only; no deployment is authorized. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md) and [LOCAL_CHAT.md](LOCAL_CHAT.md).

# Implementation rules

## Phase boundary

Implementation authorized by BUILD_BRIEF.md. Use the Next.js/FastAPI monorepo and contract boundaries described below. No production deployment is authorized. Local runtime is explicitly authorized for this UGC build.

## Stack

- Next.js with TypeScript and explicit server/client component boundaries.
- Tailwind CSS backed by semantic UI_SYSTEM design tokens.
- shadcn/ui for accessible primitives only; adapt styles to the reference rather than adopting its default visual identity.
- Shared typed API client following API_CONTRACTS, with interchangeable mock and HTTP adapters.

## Creative director implementation

Keep the Claude Messages client, credentials, skill catalog, research tools and audit envelope server-side. Do not invoke a Codex subprocess or use subscription authentication. The bounded flow is preparation, optional research, final planning and at most one repair, within four total model rounds. Use `creative-director-v3` and versioned quality thresholds together. Scores are self-reported; passing schema or numeric thresholds must never be presented as independently verified creative quality.

Use the existing `SendMessage.intent` for an explicit Change concept action; do not infer that action from ad-copy keywords. Preserve previous valid state on quality, provider or budget failures. Commit session budget reservations before external inference and retain uncertain spend after interruptions. Keep all automated tests mocked and the separately authorized real quality matrix bounded; no video generation is part of planning verification.

## Boundaries and data flow

Presentation → feature orchestration → typed API client → mock adapter or same-origin HTTP API → server generation abstraction → provider.

Use Server Components for noninteractive composition and safe server-owned data where appropriate. Use small Client Component boundaries for uploads, editable fields, selection, playback interaction, and job polling. Browser-only code stays in client modules; server secrets/provider code remain server-only and are never imported through client dependencies. Serialize only necessary public data across the boundary.

No direct provider API calls from presentation components. No browser secrets, including public-prefixed environment variables containing credentials. No hardcoded model names in reusable UI; consume public options/capabilities. No duplicated fetch/auth/error/polling logic across components. Convert raw typed API objects to display-oriented props; opaque provider metadata must not become visible UI or behavior.

Keep templates as provider-independent product/business definitions. Auto selection and actual routing belong to the backend. Auth and billing use established external components/services, chosen later; do not build custom authentication or payment handling.

## Composition and state

Prefer small, focused components for shell/navigation, creation fields, advanced controls, generation submission, preview, and recent items. Exact names and file organization follow existing code once present. No giant page components, generic component framework, or speculative abstraction hierarchy.

Maintain one creation draft and one template selection shared with the gallery. Separate transient form/upload state, prompt freshness, credit quote, and persisted job state. Preserve manual prompt edits and user inputs through recoverable errors. Centralize request cancellation/backoff and stop terminal-job polling. Prevent duplicate submissions through UI state and server idempotency.

## Mock development

Frontend must work against mock adapters until backend endpoints are connected. Mock and HTTP adapters implement the same typed operations. Mock data is deterministic and explicitly test-only, covering empty history, optional assets, prompt failure, upload failure, insufficient credits, queued/generating/completed/failed jobs, and unknown progress. Do not claim a mock result is a real generated video or payment. Swapping adapters must not require presentation-component changes. Keep mocked external billing actions noncharging.

## Accessibility and responsive behavior

Semantic HTML, visible labels, keyboard operation, clear focus, useful alternative text, announced validation/status, contrast verification, reduced-motion support, and accessible media controls are required. Do not rely on placeholders, icons, or color alone for meaning. Required controls remain usable at mobile widths and browser zoom; avoid horizontal clipping. Preserve workflow order and reference hierarchy across approved responsive adaptations.

Loading/error/empty states are required for every asynchronous surface. Show real progress or indeterminate feedback. Provide a clear recovery path without automatically repeating a charged action.

## Verification and completion

After every meaningful UI change:

1. Run the frontend on the verified, authorized runtime target. Use the explicitly authorized local UGC environment on loopback; do not use Cerebro production.
2. Capture desktop and mobile screenshots, including the changed states.
3. Compare against the approved reference and approved responsive interpretation; record deviations.
4. Fix visible differences and recapture affected views.
5. Run repository lint, TypeScript checks, and relevant tests. Once present, record exact commands and results; absence of a test setup is not a passing result.
6. Check that changes preserve the documented scope and provider boundary, then report evidence and limitations.

Use meaningful tests for contract behavior, important transitions, and failure recovery. Do not add tests that merely mirror low-impact styling. Never claim completion or pixel accuracy while required checks or reference comparison remain blocked. Run production frontend build as well as lint, typecheck, tests and visual comparison before completion.
