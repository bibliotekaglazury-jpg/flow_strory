# Claude Creative Director Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the disabled-tool local Codex planning adapter with a bounded Claude Sonnet 5 Creative Director that understands owned images and public offer context, uses allowlisted marketing skills and web research when needed, returns materially stronger 15-second concepts, and leaves the existing video pipeline unchanged.

**Architecture:** Keep the existing Next.js chat UI, FastAPI chat endpoints, `ChatService`, Pydantic planning contracts, prompt compiler, job worker, ledger, storage, history, and OpenRouter/Seedance provider. Add one server-side Anthropic adapter behind `ChatProvider`, a progressive skill catalog, a limited tool loop, structured concept audit data, and structured rejection history for `Change concept`. No browser API calls and no second generation system.

**Tech Stack:** Next.js 16, React 19, TypeScript 5.9, FastAPI, Python 3.11+, Pydantic 2, SQLAlchemy 2, Anthropic Python SDK, PostgreSQL/SQLite tests, Vitest, Playwright, pytest, Ruff.

**Spec:** [Claude Creative Director Design](../specs/2026-09-11-claude-creative-director-design.md)

## Global Constraints

- Do not read, print, copy, log, or return `ANTHROPIC_API_KEY`. Tests use fake keys and mocked HTTP transports.
- Do not modify the real `.env`; the user has already configured it. Add only documented names to `.env.example`.
- Do not use git commands or create commits for this work.
- Do not redesign the frontend or create a standalone chat page.
- Do not modify OpenRouter request semantics, Seedance model selection, generation jobs, storage, history, or the credit ledger except for regression tests proving they remain connected.
- Do not run paid video generation. Real Claude planning validation is low-cost and must be an explicit final validation step after all mocks pass.
- Do not persist chain of thought, hidden reasoning, raw image bytes, API credentials, or complete provider request/response bodies.
- Every new model-controlled loop must enforce round, tool, token, timeout, cancellation, and budget limits in application code.
- Use Sonnet 5 adaptive thinking at `effort=medium`; do not use the removed manual `budget_tokens` mode. Thinking blocks are discarded before parsing and must never enter logs, audit records, database rows, or HTTP responses.
- Keep the mock chat provider available for deterministic tests and offline development.

---

## Task 1: Lock configuration and provider selection behind tests

**Files:**
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/services/chat.py`
- Modify: `apps/api/pyproject.toml`
- Modify: `.env.example`
- Test: `apps/api/tests/test_config.py`
- Test: `apps/api/tests/test_chat.py`

- [ ] Add a failing config test proving the API accepts these server-only settings without exposing their values: `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `CLAUDE_EFFORT`, `CLAUDE_MAX_ROUNDS`, `CLAUDE_MAX_WEB_SEARCHES`, `CLAUDE_MAX_WEB_FETCHES`, `CLAUDE_MAX_INPUT_TOKENS`, `CLAUDE_MAX_OUTPUT_TOKENS`, `CLAUDE_SESSION_BUDGET_CENTS`, `CLAUDE_VALIDATION_BUDGET_CENTS`, and `CLAUDE_TIMEOUT_SECONDS`.
- [ ] Add boundary tests for positive ranges and rejection of zero/unsafe values. Keep `claude-sonnet-5` configurable rather than scattering it through code. Default `CLAUDE_EFFORT` to `medium`; accept only Sonnet 5-supported effort values.
- [ ] Run `cd apps/api && pytest tests/test_config.py -q` and confirm the new tests fail because the settings do not exist.
- [ ] Add typed settings with conservative defaults: four rounds, two searches, two fetches, bounded tokens, timeout no greater than the existing request envelope, and a positive cents budget.
- [ ] Add `anthropic` as a bounded production dependency in `apps/api/pyproject.toml`; refresh the project lock/install using the repository's existing Python environment procedure.
- [ ] Add variable names and comments to `.env.example` with empty secrets. Never copy the user's real key.
- [ ] Add a regression test proving obsolete `CODEX_*` variables present in a real-style env mapping are ignored after their typed settings are removed. The current `SettingsConfigDict(extra="ignore")` behavior must remain, so an untouched user `.env` cannot break startup.
- [ ] Add a failing provider-selection test for `CHAT_PROVIDER=claude` and a clear `CHAT_UNAVAILABLE` result when the key is absent.
- [ ] Extend `app.services.chat.provider()` with a lazy `ClaudeCreativeDirectorAdapter` branch. Preserve `mock`; leave `codex_local` temporarily readable for rollback until Task 9 removes the active path.
- [ ] Run `cd apps/api && pytest tests/test_config.py tests/test_chat.py -q` and confirm all targeted tests pass.

## Task 2: Define the provider result, usage, and audit contracts

**Files:**
- Modify: `apps/api/app/providers/chat.py`
- Modify: `apps/api/app/creative_direction.py`
- Modify: `apps/api/app/services/chat.py`
- Modify: `scripts/chat/export-schema.py`
- Modify: `packages/contracts/chat.ts`
- Modify: `packages/contracts/creative-director.schema.json` (generated)
- Modify: `packages/contracts/context-bundle.schema.json` (generated)
- Modify: `packages/contracts/chat-answer.schema.json` (generated)
- Test: `apps/api/tests/test_creative_direction.py`
- Test: `apps/api/tests/test_chat.py`

- [ ] Write failing Pydantic tests for `CreativeCandidateAudit`, `DirectorAudit`, `ChatUsage`, and `ChatProviderResult`. Audit fields are concise decision records only: candidate ID/name/mechanism, numeric quality scores, selected ID, loaded skill IDs, source domains, token counts, and estimated cents.
- [ ] Add `creativeMechanism` to `CreativePlan` as a short normalized identifier and add a validator that rejects empty or oversized identifiers.
- [ ] Add `PriorConcept` and `priorConcepts` to `ContextBundle`, containing only prior version, creative-context fingerprint, mechanism, angle, hook type, and rejected/selected status.
- [ ] Change `ChatProvider.send_message()` from an unstructured tuple to `ChatProviderResult`. Update `MockChatProvider`, `CodexLocalAdapter`, and every existing provider test double to the new return contract before provider selection can use it. Add a compatibility test that selects `codex_local` after this change and receives a valid `ChatProviderResult`; this makes the temporary rollback claim real until Task 9 deletes the adapter.
- [ ] Add tests proving provider audit data is never included in `SessionView` or browser responses.
- [ ] Persist the audit only under `chat_recipe_versions.recipe.planning.directorAudit`; do not add a migration because the existing JSON column is versioned and already owns planning evidence.
- [ ] Update schema export and TypeScript types only for fields the frontend actually receives. Keep `DirectorAudit` server-only.
- [ ] Run `cd apps/api && pytest tests/test_creative_direction.py tests/test_chat.py -q`.
- [ ] Run `python scripts/chat/export-schema.py` from the documented working directory and verify a second run produces no changes.
- [ ] Run `pnpm --filter @ugc/web typecheck` to catch contract drift.

## Task 3: Build the allowlisted progressive skill catalog

**Files:**
- Create: `apps/api/app/creative_skills/__init__.py`
- Create: `apps/api/app/creative_skills/catalog.py`
- Create: `apps/api/app/creative_skills/manifest.json`
- Create: `apps/api/app/creative_skills/vendor/marketingskills/LICENSE`
- Create: `apps/api/app/creative_skills/vendor/marketingskills/customer-research.md`
- Create: `apps/api/app/creative_skills/vendor/marketingskills/product-marketing.md`
- Create: `apps/api/app/creative_skills/vendor/marketingskills/offers.md`
- Create: `apps/api/app/creative_skills/vendor/marketingskills/ad-creative.md`
- Create: `apps/api/app/creative_skills/vendor/marketingskills/copywriting.md`
- Create: `apps/api/app/creative_skills/vendor/creative-ad-agent/LICENSE`
- Create: `apps/api/app/creative_skills/vendor/creative-ad-agent/hook-method.md`
- Modify: `docs/THIRD_PARTY.md`
- Test: `apps/api/tests/test_creative_skills.py`

- [ ] Before copying content, verify the exact upstream commit and license for `coreyhaines31/marketingskills` and `DV0x/creative-ad-agent`; record repository URL, commit SHA, imported files, adaptations, and exclusions in `docs/THIRD_PARTY.md`.
- [ ] Create a transformation manifest that records each original path, upstream SHA-256, vendored SHA-256, and every allowed removal/rewrite rule. Save a human-readable diff artifact under `docs/audits/` and require a recorded reviewer decision before enabling each skill in `manifest.json`.
- [ ] Write failing tests that accept only manifest IDs, reject traversal/absolute paths/symlinks, enforce maximum skill size, and never enumerate arbitrary filesystem content.
- [ ] Create a compact manifest with ID, title, one-sentence use condition, source, commit, license, and vendored relative path.
- [ ] Vendor only the five relevant marketing skill texts and the hook methodology. Remove tool instructions that request shell, arbitrary browsing, file writes, or actions outside creative planning while preserving attribution and license.
- [ ] Review every adapted file against its pinned original for lost meaning, hidden behavioral directives, instruction-boundary escapes, and remaining action/tool requests. Keep a skill disabled until this review passes.
- [ ] Implement `list_skill_summaries()` for the initial prompt and `load_skill(skill_id)` for progressive loading.
- [ ] Make skill text untrusted reference material: wrap it with a fixed instruction boundary and never interpolate it into system authority.
- [ ] Run `cd apps/api && pytest tests/test_creative_skills.py -q`.
- [ ] Run `cd apps/api && ruff check app/creative_skills tests/test_creative_skills.py`.

## Task 4: Version the Claude director prompt and strict response schema

**Files:**
- Create: `apps/api/app/prompts/video_chat/v3.py`
- Modify: `apps/api/app/creative_direction.py`
- Create: `apps/api/tests/test_claude_prompt.py`
- Modify: `apps/api/tests/test_creative_direction.py`

- [ ] Write failing tests proving the v3 prompt requires: offer/audience/objective understanding, at least three candidate mechanisms, explicit scoring, selected-format bias behavior, 15-second feasibility, language preservation, source discipline, separate script/visual/camera/performance/audio fields, and exclusion of prior mechanisms.
- [ ] Define score fields for stopping power, relevance, creative idea, visual story, product integration, payoff, distinctiveness, and feasibility, each with a bounded numeric range.
- [ ] Define the minimum quality thresholds as versioned constants beside the v3 schema. Do not add more environment knobs; any threshold change must update prompt, validator, rubric, and tests together.
- [ ] Add deterministic validation: exactly three or more audit candidates, one selected candidate, unique candidate mechanisms within the turn, selected audit mechanism equal to `CreativePlan.creativeMechanism`, and selected candidate meeting configured minimum score thresholds.
- [ ] Define three non-provider failure outcomes and tests: `CREATIVE_QUALITY_LOW` when all candidates miss the quality gate, `CREATIVE_MECHANISM_REPEATED` when a Change concept result repeats a prior mechanism, and `CONCEPT_SPACE_EXHAUSTED` after the one permitted repair cannot find a valid new mechanism.
- [ ] Add a repeated-mechanism validator against `ContextBundle.priorConcepts` for explicit `Change concept` turns. Do not reject a normal refinement request that asks to keep the concept.
- [ ] Write `creative-director-v3` system instructions for Sonnet 5's literal behavior. State the scope of each rule explicitly and add compact positive examples for concept diversity, concise user output, source handling, and appropriate tool use. Return only concise candidate audit fields and the strict `DirectorAnswer`; no scratchpad, chain of thought, prose prefix, or provider JSON.
- [ ] Include the compact skill catalog in the request context and tell the model to load only useful skills.
- [ ] Keep source facts and fetched pages as quoted untrusted evidence. Require a clarification when reliable context remains insufficient.
- [ ] Run `cd apps/api && pytest tests/test_claude_prompt.py tests/test_creative_direction.py -q`.

## Task 5: Implement the bounded Claude Messages API adapter

**Files:**
- Create: `apps/api/app/providers/claude.py`
- Modify: `apps/api/app/providers/chat.py`
- Modify: `apps/api/app/services/chat.py`
- Create: `apps/api/tests/test_claude_adapter.py`

- [ ] Build mocked SDK fixtures for: direct structured answer, skill request then answer, web search/fetch round then answer, clarification response, invalid schema, repeated tool request, low-quality candidate set, repeated creative mechanism, failed repair, exhausted concept space, provider 429/5xx, timeout, cancellation, budget exhaustion, adaptive thinking blocks, `stop_reason=max_tokens`, and malformed provider content.
- [ ] Write failing tests proving the adapter sends visible conversation history, current `ContextBundle`, prompt version, and owned images as native Anthropic image blocks with correct MIME types.
- [ ] Write a failing test proving the adapter never sends storage keys, signed URLs, raw environment values, provider metadata, or previous private audit data beyond the compact allowed history.
- [ ] Implement `ClaudeCreativeDirectorAdapter` with dependency-injected Anthropic client and clock/cost estimator for deterministic tests.
- [ ] Build one explicit loop that handles only allowlisted `load_creative_skill` client tools and Anthropic server web search/fetch blocks. Reject unknown tool calls.
- [ ] Enforce maximum rounds, per-tool quotas, input/output token ceilings, overall timeout, and cancellation before every call and tool execution.
- [ ] Enforce stage priority in code and tests: reserve one round for the final structured answer; load a relevant foundational skill before external research; use the local URL resolver before model tools; permit research only through `ResearchDecision`; spend a repair round only from remaining capacity. Track API rounds and tool invocation quotas as separate counters.
- [ ] Use Anthropic structured output support for the final `DirectorAnswer` plus `DirectorAudit` envelope with adaptive thinking and `effort=medium`. Validate again with Pydantic after SDK parsing; never accept JSON extracted from prose. Discard thinking blocks before any serialization and fail the response if no valid structured output remains.
- [ ] Do not send manual `thinking: {type: "enabled", budget_tokens: ...}` or non-default `temperature`, `top_p`, or `top_k`; Sonnet 5 rejects these. Add request-shape tests proving their absence.
- [ ] Size `max_tokens` with explicit headroom for adaptive thinking, tool calls, and the final schema while remaining within cost limits. Treat `stop_reason=max_tokens` as a truncated invalid result, allow only the same single budgeted repair, and never persist partial output.
- [ ] Capture usage from provider metadata and calculate an estimated cost using server-side configurable rates or provider-reported cost when available. Do not guess a zero cost.
- [ ] Translate provider failures into stable Storyflow errors: unavailable, rate limited, budget exceeded, invalid response, timeout, and cancelled. Messages must be useful without exposing Anthropic details or secrets.
- [ ] Handle valid-but-weak results separately from provider failures. Permit at most one automatic repair for `CREATIVE_QUALITY_LOW` or `CREATIVE_MECHANISM_REPEATED`; count it as a normal round against round/token/time/cost limits. If repair is unavailable or fails, preserve the previous valid plan and return the matching stable domain error. Never loop until a score passes.
- [ ] Ensure logs contain request/session correlation ID, model alias, round count, tool counts, usage, latency, and result class only. Add redaction tests for keys, prompts, source text, and image data.
- [ ] Run `cd apps/api && pytest tests/test_claude_adapter.py -q`.
- [ ] Run `cd apps/api && ruff check app/providers/claude.py tests/test_claude_adapter.py`.

## Task 6: Preserve prior mechanisms and make Change concept semantic

**Files:**
- Modify: `apps/api/app/services/chat.py`
- Modify: `apps/api/app/services/chat_context.py`
- Modify: `apps/web/features/chat/video-chat.tsx`
- Modify: `apps/web/services/mock-chat.ts`
- Modify: `apps/web/tests/chat.spec.ts`
- Test: `apps/api/tests/test_chat.py`
- Test: `apps/api/tests/test_chat_context.py`

- [ ] Add a failing service test with two turns: the first stores mechanism A; the second asks to change the concept and receives prior mechanism A in `ContextBundle.priorConcepts` before the provider call.
- [ ] Add a failing test proving a second answer with the same mechanism is rejected and does not replace the last valid recipe version.
- [ ] Add tests for the complete retry policy: one repeated mechanism triggers one budgeted repair; a valid repair is stored; a second repeat returns `CONCEPT_SPACE_EXHAUSTED`; no invalid candidate becomes the current answer; no third call occurs.
- [ ] Keep the repair counter local to one `send_message` invocation. Add a test proving a later user turn receives a fresh single-repair allowance and an exhausted turn cannot poison the session.
- [ ] Compute a creative-context fingerprint from normalized offer/objective, selected format, product URL, and owned asset IDs. Hard-exclude prior mechanisms only when this fingerprint matches; after a meaningful context change, retain old concepts as audit guidance without treating them as forbidden. Test changed photo, changed format, and changed offer/objective.
- [ ] Query prior `ChatRecipeVersion` rows for the owned session before clearing the current answer. Convert them to compact `PriorConcept` entries; never pass full compiled prompts or provider payloads.
- [ ] Pass all mechanisms retained by the bounded session history, but hard-exclude only entries with the current creative-context fingerprint and do not force artificial novelty indefinitely. When no valid new mechanism is produced after one repair, return a concise instruction to change objective, audience, format, or assets, or reset the conversation.
- [ ] Preserve the current visible messages and revision locking. On provider failure, keep the user's message and retain the last valid recipe version for audit/retry.
- [ ] Do not irreversibly clear `ChatSession.answer` before the provider result validates. Retain the previous answer while the turn is `responding`, replace it atomically on success, and restore/retain it on provider, quality, repeated-mechanism, cancellation, or budget failure.
- [ ] Change the button seed text from the vague `Change the concept:` to a stable user instruction such as `Create a materially different concept.` while keeping it editable and focused in the existing composer.
- [ ] Update the frontend mock service so Playwright can return two mechanisms that differ in story structure, not camera wording.
- [ ] Add Playwright assertions for preserved conversation, changed mechanism/summary, unchanged form until `Use this concept`, and no generation on concept change.
- [ ] Run `cd apps/api && pytest tests/test_chat.py tests/test_chat_context.py -q`.
- [ ] Run `pnpm --filter @ugc/web test -- --run` and `pnpm --filter @ugc/web test:e2e -- chat.spec.ts`.

## Task 7: Integrate URL research and owned images without duplicating resolution

**Files:**
- Modify: `apps/api/app/services/chat_context.py`
- Modify: `apps/api/app/providers/claude.py`
- Modify: `apps/api/app/prompts/video_chat/v3.py`
- Test: `apps/api/tests/test_chat_context.py`
- Test: `apps/api/tests/test_claude_adapter.py`

- [ ] Add failing tests for five paths: resolved public page, partial/blocked page recovered by Claude web fetch, offer discovered through bounded search from user text, unresolved offer producing one clarification, and a complete user-supplied offer where no search/fetch tool call is permitted.
- [ ] Keep the existing server URL resolver as the first path. Preserve SSRF checks, redirect limits, size limits, HTML parsing, and owned-asset loading.
- [ ] Mark URL evidence with resolution status and source URL/domain in `ContextBundle`; distinguish user text, local resolver facts, image observations, and Claude-researched sources.
- [ ] Permit web fetch only for the supplied public domain or a URL returned by approved web search. Cap fetched/search result text before it re-enters the model context.
- [ ] Implement a provider-neutral `ResearchDecision` before the tool loop. Allow fetch for a supplied public URL whose local resolution is partial/failed. Allow search when the user explicitly asks for research or names an offer but lacks facts needed for the requested creative task. Deny search when the user already supplies an identifiable offer plus adequate description/objective, explicitly declines research, submits gibberish, or provides only a personal image without an offer clue.
- [ ] Encode adequacy without an industry classifier: identifiable offer + supplied/safely inferable objective + either two useful offer facts or one useful fact plus an audience, benefit, or differentiator. Add boundary fixtures where a named offer with only a vague adjective/objective permits bounded search, a complete offer/audience/objective description denies search, and an ambiguous name that remains unresolved returns one clarification.
- [ ] Add adapter tests proving a model-requested search/fetch is rejected when `ResearchDecision` denies it, so the model cannot spend tokens or add latency by redefining “insufficient.”
- [ ] Keep source facts authoritative over model guesses. Require the user-facing plan to omit uncertain specifications rather than adding industry defaults.
- [ ] Ensure product and person images are attached on every relevant turn and are not persisted in chat JSON.
- [ ] Run `cd apps/api && pytest tests/test_chat_context.py tests/test_claude_adapter.py -q`.

## Task 8: Keep the frontend compact and expose useful concept fields

**Files:**
- Modify: `apps/web/features/chat/chat-parts.tsx`
- Modify: `apps/web/features/chat/video-chat.tsx`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/tests/chat.spec.ts`
- Test: `apps/web/tests/create-page.test.tsx` or the nearest existing Create component test

- [ ] Add a failing UI test for the approved compact output: Concept, Hook, Story, Script, Look, `Use this concept`, and `Change concept`.
- [ ] Map these sections from existing validated `CreativePlan` and `VideoPlan`; do not expose candidate scores, skill names, source traces, Claude, model IDs, or provider errors.
- [ ] Keep Manual mode limited to its textarea. Confirm no chat window renders in Manual mode.
- [ ] Keep the generated-video result panel below the prompt/chat section through the existing creation state. Do not add a second preview component.
- [ ] Apply only through the existing `/api/chat/sessions/:id/apply` endpoint. Confirm Apply changes prompt/format/ratio/language but does not create a generation or reserve credits.
- [ ] Use current white workspace, lime tokens, spacing, typography, focus states, and responsive behavior. Avoid new generic cards.
- [ ] Run `pnpm --filter @ugc/web test -- --run`.
- [ ] Run `pnpm --filter @ugc/web typecheck` and `pnpm --filter @ugc/web lint`.
- [ ] Start the local frontend/API, capture desktop and mobile screenshots, compare them with `docs/references`, record only deviations caused by this change, and fix them before proceeding.

## Task 9: Switch the active chat provider and retire the Codex runtime path safely

**Files:**
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/services/chat.py`
- Modify: `.env.example`
- Delete: `apps/api/app/providers/codex_local.py`
- Modify/Delete: Codex-only tests in `apps/api/tests/test_chat.py` and `apps/api/tests/test_chat_context.py`
- Modify: `docs/LOCAL_CHAT.md`
- Modify: `docs/CHAT_ARCHITECTURE.md`

- [ ] Add a failing test proving the default non-mock chat provider is `claude` and old Codex sessions return the existing `CHAT_PROVIDER_CHANGED` response.
- [ ] Change the configuration default to `claude`. Do not edit the user's `.env`; report the exact required `CHAT_PROVIDER=claude` setting if it is absent.
- [ ] Remove Codex executable/runtime/history settings from application config and `.env.example` only after Claude unit/integration tests pass.
- [ ] Delete the Codex adapter and its subprocess-specific tests. Preserve generic provider contract and provider-change behavior.
- [ ] Do not migrate existing local Codex session IDs. The frontend already starts a new conversation when provider identity changes.
- [ ] Update local chat docs to state that Storyflow DB history is authoritative and Anthropic credentials remain server-only.
- [ ] Run the complete backend chat suite.

## Task 10: Prove the video pipeline remains unchanged

**Files:**
- Test: `apps/api/tests/test_single_video.py`
- Test: `apps/api/tests/test_chat.py`
- Test: `apps/api/tests/test_worker.py` if present
- Modify: `docs/CREATIVE_DIRECTOR.md`
- Modify: `docs/GENERATION_ARCHITECTURE.md`

- [ ] Add or retain a regression test that applies a Claude-shaped plan, creates the existing Prompt, obtains the existing quote, creates one generation/job, and completes via `MockProvider` into output/history.
- [ ] Assert Apply alone creates no Generation, Job, Ledger reservation, provider call, or output.
- [ ] Assert the real provider registry still exposes only OpenRouter/`bytedance/seedance-2.0-mini` for production video, fixed at 15 seconds and 480p with native audio.
- [ ] Assert aspect ratios `9:16`, `1:1`, and `16:9` survive chat -> plan -> Apply -> generation snapshot -> provider request.
- [ ] Assert product/person reference assets still require reachable HTTPS URLs only at the existing provider boundary, with no credential or image bytes in browser responses.
- [ ] Run `cd apps/api && pytest tests/test_chat.py tests/test_single_video.py -q`.
- [ ] Do not run a paid OpenRouter generation.

## Task 11: Run the quality validation matrix

**Files:**
- Create: `apps/api/tests/fixtures/creative_validation_cases.json`
- Create: `apps/api/tests/fixtures/creative_injection_cases.json`
- Create: `scripts/chat/validate_claude_director.py`
- Create: `docs/verification/CLAUDE_CREATIVE_DIRECTOR_20260911.md`
- Test: `apps/api/tests/test_claude_quality_harness.py`

- [ ] Create three non-secret cases: physical consumer product with owned test images, local massage service with minimal identity, and online course with a lead objective. Include expected language, required facts, forbidden inventions, and acceptable distinct mechanisms.
- [ ] Create adversarial fixtures for page HTML/JSON-LD, search/fetch content, image/OCR text, user text, and vendored skill text that try to override system instructions, request secrets, enable tools, or force provider JSON. Expected behavior is to treat them as evidence or reject them, never obey them.
- [ ] Write a deterministic unit test for the harness itself using mocked Claude responses. The harness must redact inputs, never invoke video generation, and stop when its configured planning-cost cap is reached.
- [ ] Add a separate `CLAUDE_VALIDATION_BUDGET_CENTS` hard cap for the entire harness run, independent of per-session limits. Before execution, print only the maximum permitted total cost and planned call count; stop before any call that could exceed the aggregate cap.
- [ ] For each real case, run three planning turns in fresh sessions. Then request one `Change concept` turn and verify its mechanism differs from the prior selection. The harness must stop cleanly with a partial report if the aggregate cap is reached.
- [ ] Score outputs against the documented rubric: context comprehension, factual grounding, target relevance, hook, underlying creative mechanism, visual action, 15-second feasibility, spoken-language fidelity, and schema stability.
- [ ] Compare `effort=medium` against a small mocked baseline and the bounded real matrix. Raise it only if measured quality misses the rubric and the aggregate cost cap permits; do not compensate for under-thinking by making the system prompt verbose.
- [ ] Record model ID returned by the API, prompt version, usage, estimated cost, latency, pass/fail, concise concept output, and source domains. Do not record the key, raw image bytes, complete hidden prompts, or reasoning.
- [ ] Require all schema checks, all language checks, all factual checks, and at least the agreed rubric threshold before declaring the director validated.
- [ ] Run the adversarial injection matrix through mocked transports on every test run and through at most one bounded real planning session during the real matrix. Assert that no injected directive, secret request, tool escalation, or provider payload appears in the accepted output/audit.
- [ ] Treat any injection-policy failure in mocked or real validation as an unconditional release blocker. Do not average it into the creative-quality score, retry it into a passing result, or mark the director validated with a warning.
- [ ] If the configured `claude-sonnet-5` identifier is rejected, stop with a configuration finding. Verify the exact current Anthropic model ID before changing config; do not silently fall back to another model.
- [ ] Run the real validation only after mocked tests pass and only once for this matrix. It spends Claude API credits but never video credits.

## Task 12: Full verification and documentation closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/PRODUCT_SPEC.md`
- Modify: `docs/API_CONTRACTS.md`
- Modify: `docs/BACKEND_ARCHITECTURE.md`
- Modify: `docs/CREATIVE_DIRECTOR.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/IMPLEMENTATION_RULES.md`
- Modify: `docs/THIRD_PARTY.md`
- Modify: `docs/VERIFICATION.md`

- [ ] Update documentation from verified implementation only: direct Claude Messages API, one bounded agent, progressive skills, web research policy, structured candidate gate, Change concept semantics, cost limits, and server-only key handling.
- [ ] Remove statements that Codex is the active chat transport. Retain historical audit documents as dated evidence rather than rewriting history.
- [ ] Document that chat planning does not reserve Storyflow video credits and that paid video generation still requires the explicit Generate action.
- [ ] Run backend formatting/lint: `cd apps/api && ruff check app tests`.
- [ ] Run backend tests: `cd apps/api && pytest -q`.
- [ ] Run frontend tests: `pnpm --filter @ugc/web test -- --run`.
- [ ] Run frontend lint: `pnpm --filter @ugc/web lint`.
- [ ] Run frontend typecheck: `pnpm --filter @ugc/web typecheck`.
- [ ] Run production build locally: `pnpm --filter @ugc/web build`.
- [ ] Run database migration verification using the repository's local test database; no production database.
- [ ] Run mock E2E: upload/select assets -> AI Creative Director -> concept -> Change concept -> Use concept -> Generate -> queued -> generating -> completed -> preview -> history.
- [ ] Search the browser build, logs, fixtures, and tracked source for secret values and raw Anthropic payloads without printing any matches containing credentials. Report only file names and redacted finding types.
- [ ] Self-review this plan's acceptance criteria against the implementation. Confirm no placeholder, TODO, disabled assertion, undocumented fallback, second provider, frontend redesign, or paid video call was introduced.
- [ ] Write the final verification report with exact commands/results, real planning output examples, known limitations, and a clear statement that creative video quality was not evaluated without a paid Seedance run.

## Completion Criteria

- Claude is the active non-mock Creative Director and the browser never receives its key or provider internals.
- One bounded agent can inspect owned images, load allowlisted skills, and use limited web research.
- Every ready response contains a valid 15-second `CreativePlan` and `VideoPlan`; at least three distinct candidates were evaluated without persisting chain of thought.
- `Change concept` excludes previously selected/rejected mechanisms using stored structured history.
- Manual mode has no chat window; Apply never generates video or spends video credits.
- The existing OpenRouter/Seedance job, ledger, storage, preview, and history path passes regression and mock E2E tests unchanged.
- Three real planning scenarios pass the quality matrix within the configured Claude budget.
- Zero prompt-injection policy failures occur across page, JSON-LD, search/fetch, image/OCR, user, and skill-content cases; any single failure blocks completion.
- Lint, typecheck, tests, build, schema export, and local migration checks pass.
- No production deployment, paid video generation, additional video provider, TTS, or longer-duration work occurs.

## Implementation rulings — 2026-09-11

These changes resolve issues found during implementation; unchecked original tasks remain acceptance references, not claims of completion.

- Anthropic citations are incompatible with JSON structured outputs. Preparation, optional server research, final structured plan and at most one repair are separate Messages API calls under one four-round budget. Skills load from the validated catalog between calls. This replaces the proposed free-running client-tool loop, preserves progressive loading, and never needs to persist/replay signed private thinking blocks.
- Basic search `web_search_20250305` and fetch `web_fetch_20250910` are the only tools. No code-execution tool or shell is enabled. Research receives only its brief and selected references. Final output receives bounded source-backed citations/documents, not free-form research conclusions or encrypted search blobs. Fetch is restricted to the user-supplied public domain after the existing SSRF validator.
- Research adequacy remains a semantic model assessment, not an industry classifier or fact-count heuristic. Application code enforces explicit refusal patterns, adequate-context denial, allowed fetch status/domain, quotas and final-round reservation. This cannot guarantee perfect natural-language permission interpretation across all languages; adversarial tests verify instruction boundaries and forbidden tool access, not universal injection immunity.
- A small `ChatSession.planning_usage` JSON migration is necessary: recipe versions alone cannot retain cost reservations for failed/cancelled requests without recipes. Unknown costs retain reservations across restarts. This is separate from the video ledger.
- Budget reservations use the published Sonnet 5 standard rates ($2/M input, $10/M output, conservative cache rates) and search price ($0.01/use), checked before each request. Native provider research may consume internal tokens before returning usage: the app can stop subsequent calls but cannot assert an absolute provider-side dollar hard cap. The validation harness is limited to $1 in application reservations and must report any reconciliation overrun.
- Rejection memory currently stores previously accepted concepts within the same form/asset context. The chosen slug is checked on explicit `change_concept`; semantic sameness under a renamed slug is a model/rubric limitation. Failed plans are never persisted as valid answers. After failed turns the prior plan remains visible, but a fresh valid revision is required before Apply.
- No real video call is part of this implementation validation. Runtime and visual proofs use mocks. Real creative quality needs review of actual Claude outputs and is not established by numeric model self-scores.
