# Subtitle Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved Gemini-powered Subtitle Studio with persistent projects, editable timed captions, identical Remotion preview/export, and `9:16` plus `16:9` output.

**Architecture:** Claude adds the provider-neutral subtitle API, Gemini adapter, durable jobs, persistence, and server export. Codex builds the frontend against the shared contracts and mock adapter, then connects the HTTP adapter. One shared Remotion composition is used by browser Player and server Renderer.

**Tech Stack:** Next.js/React, TypeScript, `@remotion/player` 4.0.523, `@remotion/captions` 4.0.523, FastAPI, SQLAlchemy/Alembic, PostgreSQL, Gemini paid API, existing object storage and Remotion renderer.

**Spec:** `docs/superpowers/specs/2026-09-14-subtitle-studio-design.md`

## Global Constraints

- Codex owns frontend files; Claude owns backend, migrations, API tests, and `packages/contracts/subtitles.ts`.
- Only Gemini is implemented as the transcription provider.
- Output ratios are exactly `9:16` and `16:9`; media is contained and never stretched.
- Preview and export use one shared serializable caption composition.
- Automated tests use a fake transcription provider; no paid call is part of routine verification.
- Production deployment is outside this plan.
- Billing/credit pricing is outside this experiment and must not be invented in UI or API.

---

### Task 1 — Shared subtitle contracts (Claude)

**Files:**
- Create: `packages/contracts/subtitles.ts`
- Modify: `packages/contracts/index.ts`
- Test: `apps/web/services/contracts.test.ts`

**Produces:** The exact types and service methods defined in the spec.

- [ ] Add the subtitle enums/interfaces and export them from the package root.
- [ ] Extend `Services` with `subtitleProjects.create`, `list`, `get`, `update`, `export`, and `getExport`.
- [ ] Add a compile-time adapter fixture covering every method and response shape.
- [ ] Run `pnpm typecheck`; expected result: exit 0.
- [ ] Publish a bus `handoff` naming the final exported types and methods.

### Task 2 — Persistence and ownership (Claude)

**Files:**
- Create: `apps/api/alembic/versions/0007_subtitle_studio.py`
- Modify: `apps/api/app/db.py`
- Create: `apps/api/app/subtitles/__init__.py`
- Create: `apps/api/app/subtitles/schemas.py`
- Create: `apps/api/app/subtitles/service.py`
- Test: `apps/api/tests/test_subtitle_projects.py`

**Produces:** `SubtitleProject`, `SubtitleExport`, and `SubtitleJob` persistence plus owned lookup functions.

- [ ] Write tests proving Alice cannot access Bob's project/export and project creation is idempotent before provider work.
- [ ] Run the focused tests and confirm they fail on missing models/services.
- [ ] Add the three tables and indexes described in the spec, including per-user idempotency uniqueness and immutable export snapshots.
- [ ] Implement owned create/get/list/update functions with optimistic `revision` comparison.
- [ ] Run `pytest apps/api/tests/test_subtitle_projects.py -q`; expected result: all tests pass.
- [ ] Publish schema and ownership decisions to the bus with every affected file.

### Task 3 — Gemini transcription adapter and durable transcription job (Claude)

**Files:**
- Create: `apps/api/app/subtitles/providers.py`
- Create: `apps/api/app/subtitles/jobs.py`
- Modify: `apps/api/app/config.py`
- Test: `apps/api/tests/test_subtitle_transcription.py`

**Produces:** `TranscriptionProvider.transcribe(asset) -> NormalizedTranscript` and a Gemini implementation selected through server configuration.

- [ ] Test valid word timestamps, malformed JSON, missing timing, out-of-order timing, timeout, and provider retry behavior using a fake adapter.
- [ ] Test that a repeated project idempotency key never invokes the provider twice.
- [ ] Implement audio extraction through the existing ffmpeg environment and the Gemini structured response request.
- [ ] Normalize only validated provider timings into stable word/cue ids; return a retryable error for invalid timing.
- [ ] Add durable `transcribe` leasing, retry, terminal failure, and restart recovery.
- [ ] Run `pytest apps/api/tests/test_subtitle_transcription.py -q`; expected result: all tests pass.
- [ ] Publish provider model configuration names without publishing secrets.

### Task 4 — Subtitle API routes (Claude)

**Files:**
- Create: `apps/api/app/subtitles/routes.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/responses.py`
- Test: `apps/api/tests/test_subtitle_routes.py`

**Produces:** All create/list/get/update/export/poll endpoints in the spec.

- [ ] Write request/response, validation, ownership, cursor, idempotency, and `409 REVISION_CONFLICT` tests.
- [ ] Register the subtitle router under `/api/subtitle-projects`.
- [ ] Return camelCase public responses consistent with existing API views.
- [ ] Verify an expired signed URL refreshes through a new project/export read.
- [ ] Run `pytest apps/api/tests/test_subtitle_routes.py -q`; expected result: all tests pass.
- [ ] Publish an API-ready `handoff` to Codex.

### Task 5 — Shared Remotion caption composition (Codex frontend; Claude verifies server invocation)

**Files:**
- Create: `packages/video-templates/src/subtitles/types.ts`
- Create: `packages/video-templates/src/subtitles/caption-pages.ts`
- Create: `packages/video-templates/src/subtitles/subtitle-composition.tsx`
- Modify: `packages/video-templates/src/root.tsx`
- Test: `packages/video-templates/src/subtitles/subtitle-composition.test.tsx`

**Produces:** `SubtitleCompositionProps` and a registered composition that accepts source URL, cues, style, duration, and aspect ratio.

- [ ] Write deterministic tests for active-word selection, safe-area placement, four presets, and dimensions for both ratios.
- [ ] Implement cue conversion/pagination with `@remotion/captions` and frame-derived animation only.
- [ ] Render source video with contain behavior on a near-black canvas.
- [ ] Register the composition without exposing provider details.
- [ ] Run the focused test and a local still render at one fixed timestamp for both ratios.

### Task 6 — Mock service and editor state controller (Codex)

**Files:**
- Modify: `apps/web/services/mock.ts`
- Modify: `apps/web/services/http.ts`
- Create: `apps/web/features/subtitles/use-subtitle-project.ts`
- Create: `apps/web/features/subtitles/editor-state.ts`
- Test: `apps/web/features/subtitles/editor-state.test.ts`

**Produces:** A single controller for selection, seek, autosave, undo/redo, polling, export, and recovery.

- [ ] Test split/merge rules, cue boundary validation, undo/redo, 700 ms autosave, polling termination, and revision conflict recovery.
- [ ] Implement a realistic in-memory project in the mock adapter with deterministic async state changes.
- [ ] Implement the HTTP methods exactly from the shared contract.
- [ ] Keep all components provider-blind.
- [ ] Run the focused frontend tests; expected result: all tests pass.

### Task 7 — Subtitle Studio entry and approved editor UI (Codex)

**Files:**
- Create: `apps/web/app/subtitles/page.tsx`
- Create: `apps/web/app/subtitles/[id]/page.tsx`
- Create: `apps/web/features/subtitles/subtitle-entry.tsx`
- Create: `apps/web/features/subtitles/subtitle-editor.tsx`
- Create: `apps/web/features/subtitles/editor-header.tsx`
- Create: `apps/web/features/subtitles/video-preview.tsx`
- Create: `apps/web/features/subtitles/transcript-editor.tsx`
- Create: `apps/web/features/subtitles/style-inspector.tsx`
- Create: `apps/web/features/subtitles/caption-timeline.tsx`
- Modify: `apps/web/components/shell.tsx`
- Modify: `apps/web/app/globals.css`
- Test: `apps/web/features/subtitles/subtitle-editor.test.tsx`

**Produces:** The selected mockup's complete empty, progress, editing, exporting, completed, and error states.

- [ ] Add accessible tests for entry, row/cue synchronization, keyboard focus, disabled controls, ratio switching, export, and retry states.
- [ ] Add the Subtitles sidebar destination and upload/Library entry screen.
- [ ] Build the approved desktop hierarchy with focused reusable components and existing Forma tokens.
- [ ] Mount `@remotion/player` with the shared composition; render `9:16` and `16:9` through props.
- [ ] Implement responsive stacking below 1100 px and the compact control drawer below 720 px.
- [ ] Run focused tests and `pnpm typecheck`; expected result: exit 0.

### Task 8 — Server export and storage (Claude)

**Files:**
- Create: `scripts/subtitles/render-subtitle.ts`
- Modify: `apps/api/app/subtitles/jobs.py`
- Modify: `apps/api/app/services/assets.py`
- Test: `apps/api/tests/test_subtitle_export.py`
- Test: `apps/api/tests/test_postgres_integration.py`

**Produces:** Durable export jobs that render the immutable revision snapshot and persist MP4/thumbnail assets.

- [ ] Test export idempotency, immutable source revision, restart recovery, failed render retry, ownership, and output storage keys.
- [ ] Invoke the registered composition with an argument-safe subprocess payload; never interpolate user text into shell command text.
- [ ] Store output under `users/{userId}/subtitle-projects/{projectId}/exports/{exportId}/` through the existing asset service.
- [ ] Set progress only from real renderer events and terminal state only after the asset transaction succeeds.
- [ ] Run focused API tests and one mock-media PostgreSQL integration render.
- [ ] Publish export readiness and exact output response to the bus.

### Task 9 — Library integration (Codex)

**Files:**
- Modify: `apps/web/app/library/page.tsx`
- Create: `apps/web/features/subtitles/subtitle-project-card.tsx`
- Test: `apps/web/app/library/page.test.tsx`

**Produces:** Newest-first subtitle projects and completed exports that reopen or download correctly.

- [ ] Test empty, transcribing, failed, ready, exporting, and completed project cards.
- [ ] Add a `Subtitles` filter without changing current video and look-project behavior.
- [ ] Reopen the editor at `/subtitles/{id}` and download through refreshed asset URLs.
- [ ] Run the focused Library tests; expected result: all tests pass.

### Task 10 — Cross-layer verification and handoff (Codex and Claude)

**Files:**
- Modify: `docs/VERIFICATION.md`
- Modify: `docs/DECISIONS.md`

**Produces:** Reviewable evidence for the accepted design and API invariants.

- [ ] Claude runs focused backend tests plus lint for changed backend files and publishes results to the bus.
- [ ] Codex runs focused frontend tests, typecheck, and production frontend build.
- [ ] Capture `1440x1024` editing screens for both ratios and `390x844` responsive screens.
- [ ] Compare `9:16` against `docs/references/subtitle-studio/approved-editor-9x16.png`, fix material hierarchy/spacing differences, and record remaining deviations.
- [ ] Verify reload during transcription/export and Alice/Bob isolation with mock providers.
- [ ] Record that no paid Gemini call and no production deployment occurred.
