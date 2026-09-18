# Claude Creative Director Design

**Status:** Approved direction for implementation planning  
**Date:** 2026-09-11  
**Scope:** Local Storyflow development; no deployment and no paid video generation

## Problem

Storyflow already has a working provider-neutral chat boundary, strict creative contracts, asset ownership checks, prompt compilation, durable generation jobs, storage, history, and ledger handling. Its current live chat adapter uses the local Codex CLI with tools, skills, and web search disabled. That adapter can produce schema-valid plans, but it cannot independently research an offer or progressively load marketing methods. The current `Change concept` action also preserves visible chat text without preserving a structured record of rejected creative mechanisms.

## Decision
рь 
Use the Anthropic Messages API directly through a new `ClaudeCreativeDirectorAdapter`. The adapter implements the existing `ChatProvider` boundary and remains server-side. Storyflow continues to own sessions, visible messages, validated plans, prompt compilation, and persistence.

The director is one bounded Claude Sonnet 5 agent. It can:

- inspect owned product and person images passed as native image content;
- use the already-resolved `ContextBundle`;
- load allowlisted, vendored marketing skills progressively;
- use Anthropic web search and web fetch when source context is absent or incomplete;
- generate at least three materially different concepts internally;
- score the candidates against explicit quality criteria and return the strongest one;
- avoid mechanisms rejected in earlier `Change concept` turns;
- return only a strict `DirectorAnswer` for the product UI.

There are no permanent subagents, no second agent backend, and no model call from the browser. OpenRouter remains the only video gateway, and Seedance 2.0 Mini remains the only real video model.

Claude Sonnet 5 uses adaptive thinking by default. Storyflow uses adaptive thinking with `effort=medium` for the Creative Director because the task combines research, candidate generation, scoring, and tool selection. Manual extended thinking with `budget_tokens` is not used. Thinking blocks are provider-ephemeral: the adapter discards them before parsing, logging, auditing, persistence, or HTTP serialization. Only schema-bound candidate summaries and the final answer may leave the provider boundary.

## Runtime flow

```text
Create UI
  -> existing Storyflow chat API
  -> existing ChatService ownership/session checks
  -> existing URL resolver and owned asset loading
  -> ContextBundle + prior concept history
  -> ClaudeCreativeDirectorAdapter
       -> optional allowlisted skill loads
       -> optional Anthropic web search/fetch
       -> candidate generation, scoring, selection
       -> strict DirectorAnswer
  -> existing Pydantic validation
  -> existing compile_plan / VideoRecipe
  -> existing Apply flow and Prompt record
  -> explicit Generate Video click
  -> existing quote/job/worker/ledger
  -> existing OpenRouterVideoProvider / Seedance
  -> existing storage, preview, and history
```

## Tool boundary

The agent receives only these capabilities:

1. `load_creative_skill(skill_id)` reads an allowlisted vendored skill file. The model first sees a short catalog and loads full instructions only when useful.
2. Anthropic server-side web search, with a per-turn quota.
3. Anthropic server-side web fetch, with a per-turn quota and domain restriction derived from the supplied URL or search results.

The agent receives no shell, arbitrary filesystem, MCP, database, storage, billing, generation, or deployment tool. It cannot submit a video job. Source pages and image text are treated as untrusted evidence rather than instructions.

Initial skills cover offer analysis, customer/audience research, ad creative, product marketing, and copywriting. Each vendored source is pinned and licensed in `docs/THIRD_PARTY.md`.

Vendoring uses a reviewable transformation manifest. Each source file records its upstream hash and vendored hash, every removal is listed by rule, and a reviewer compares the final text with the pinned original before it can enter the catalog. Tests reject executable/tool directives and instruction-boundary escape phrases, but this automated check does not replace the recorded diff review.

## Structured outputs and audit data

`DirectorAnswer`, `CreativePlan`, and `VideoPlan` remain the public planning contracts. Add a short `creativeMechanism` identifier to `CreativePlan` so a rejected mechanism can be excluded on the next turn.

The provider also returns a server-only audit envelope containing:

- candidate name and mechanism;
- compact quality scores;
- selected candidate identifier;
- skill identifiers loaded;
- URLs/domains used;
- token and cost usage.

This audit contains no chain of thought. It is persisted with the recipe version and is not returned by normal frontend session responses. Prior selected/rejected mechanisms are reconstructed from recipe versions and included in the next director context.

A low-scoring but schema-valid response is a distinct domain outcome, `CREATIVE_QUALITY_LOW`. The adapter may make one bounded repair request if round, token, timeout, and cost budgets permit. A repeated mechanism uses `CREATIVE_MECHANISM_REPEATED` and the same single-repair policy. The repair is an ordinary billed round and counts toward every limit. If repair fails or cannot be afforded, Storyflow preserves the previous valid plan and tells the user it could not produce a sufficiently strong or different concept.

Quality thresholds are versioned domain constants beside the v3 scoring schema, not environment tuning knobs. Changing them requires updating the prompt/schema tests and validation rubric together.

When repeated `Change concept` turns exhaust plausible mechanisms, the system does not fabricate novelty. It returns `CONCEPT_SPACE_EXHAUSTED` with a concise suggestion to change the objective, audience, format, or source material, or reset the conversation. This is not converted into an irrelevant clarification or a weak accepted plan.

## Resource and cost limits

All limits are server configuration, with safe defaults:

- maximum four Claude API round trips per user turn;
- maximum two web searches per turn;
- maximum two web fetches per turn;
- maximum input and output tokens per round;
- overall request timeout;
- maximum session budget in cents;
- a separate aggregate budget for the complete real validation run;
- cancellation propagated from the existing session reset path.

The adapter checks accumulated usage before each additional model call and fails closed when another call could exceed configured limits. Usage and estimated cost are logged without prompts, image bytes, credentials, or private reasoning.

`max_tokens` reserves enough headroom for adaptive thinking, tool calls, and the structured answer while remaining inside the cost cap. A `stop_reason=max_tokens` result is treated as a truncated invalid response; Storyflow does not silently accept or persist a partial plan. The request does not set non-default `temperature`, `top_p`, or `top_k`, which Sonnet 5 rejects.

Obsolete `CODEX_*` entries may remain in a user's untouched `.env`. Pydantic settings continue to ignore unknown variables, so removing typed Codex configuration does not make those stale entries a startup error.

## Context behavior

The current bounded server-side URL resolver runs first. Resolved source facts remain preferred evidence. If it returns partial or unavailable context, Claude may research the public offer using web fetch/search. If the offer still cannot be understood reliably, the assistant asks one high-value clarification instead of fabricating a plan.

Research permission is decided before the model tool loop using a small evidence policy, not an industry classifier. Search is disabled when the user has already supplied an identifiable offer plus adequate description/objective, or explicitly asks not to research. Fetch is allowed for a supplied public URL when the local resolver is partial/failed. Search is allowed when a named offer lacks facts needed for the requested ad, or the user explicitly requests research. The adapter rejects model search/fetch requests outside that policy. Tests cover both required research and explicit no-search cases.

For this policy, “adequate” means the offer is identifiable, the desired objective is supplied or safely inferable, and the context contains either two useful offer facts or one useful offer fact plus an audience, benefit, or differentiator. A named offer with only a vague adjective and objective, such as “Acme cups, cheap, make a sales ad,” is insufficient and permits bounded search even when the user did not explicitly request it. A complete description with offer, objective, audience, and useful facts denies search. If a sparse or ambiguous name cannot be resolved within the quota, the result is one clarification rather than guessed context.

An uploaded image may be sufficient by itself. An image plus a short user description may be researched when the user names the offer or asks the director to do so. Services, courses, specialists, tourism, SaaS, local businesses, and physical products use the same flexible `ContextBundle`; no category-specific questionnaire is added.

Sonnet 5 follows literal instructions closely, especially at lower effort. The v3 prompt therefore states the scope of every cross-cutting rule explicitly and includes compact positive examples of acceptable concept diversity, concision, tool use, and source handling. Prompt changes are accepted only after the validation matrix confirms the intended behavior.

## Change concept behavior

The existing button continues to place a short instruction in the composer. Before the next provider call, ChatService adds the previous structured mechanisms and summaries from stored recipe versions. Claude must produce candidates that differ in the underlying mechanism, not merely wording, framing, or camera angle. A repeated mechanism fails server validation and returns a retryable planning error rather than becoming the new accepted plan.

One automatic repair is allowed for a repeated mechanism. The repair counter exists only inside one `send_message` turn and is never stored as sticky session state. A later user message receives a fresh single-repair allowance. Prior concepts remain audit history, but hard mechanism exclusion applies only when their creative-context fingerprint matches the current offer, objective, selected format, URL, and owned asset IDs. A meaningful change to those inputs creates a new fingerprint, so old mechanisms inform the director without permanently blocking them. After one failed repair in the current turn, the user receives the stable exhausted/different-concept error; the invalid answer is not persisted as the current plan and all repair usage counts against that turn's budget.

Round allocation is explicit. The adapter reserves capacity for a final structured answer first. If a skill is relevant, loading it precedes external research because it is bounded and foundational. The existing local resolver precedes all model tools. External search/fetch occurs only when `ResearchDecision` permits it. A repair round runs only if round, token, time, and cost capacity remains; otherwise Storyflow returns the quality/repetition error without making another call. Tool invocation quotas and API round limits are counted and reported separately.

## Frontend behavior

The existing compact Creative Director chat remains inside the white Create workspace. No new page or dashboard is created. The user sees one concise concept, hook, story, spoken script, and look, followed by `Use this concept` and `Change concept`. Candidate scores, provider names, model IDs, tools, and research traces remain developer-only.

## Verification gate

Implementation is complete only after mock tests and three real low-cost planning cases pass repeatedly:

1. physical product with product and person images;
2. local massage service with little or no brand information;
3. online course with a short business objective.

Each case runs three times. Review checks context understanding, language, hook strength, mechanism diversity, 15-second feasibility, script/visual separation, and schema stability. These tests do not generate video. A paid Seedance generation requires a later explicit instruction.

The matrix also includes adversarial page text, image OCR text, user content, and skill content attempting to override the system prompt or request tools/secrets. Passing requires those strings to remain evidence only. Any mocked or real injection-policy failure is a hard release blocker regardless of aggregate creative score. The validation script has a hard aggregate budget independent of per-session limits and stops before a request that could exceed it.

## Out of scope

- production deployment;
- Managed Agents or persistent Anthropic memory;
- multiple LLM providers or fallback routing;
- additional video providers or models;
- TTS, stitching, longer durations, timeline editing, or Canvas;
- frontend redesign;
- paid video generation during this implementation.

## Model guidance source

The adapter and v3 prompt must be checked against Anthropic's current [Prompting Claude Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5) guidance before implementation. Relevant constraints are adaptive thinking defaults, effort control, tool-use prompting, literal instruction following, unsupported manual thinking budgets, unsupported non-default sampling parameters, and `max_tokens` headroom.
