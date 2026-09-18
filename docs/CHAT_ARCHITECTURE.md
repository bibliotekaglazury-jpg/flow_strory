# Current chat architecture — Claude Messages, 2026-09-11

The local chat runtime uses the server-side Anthropic Messages API through `ClaudeCreativeDirectorAdapter`. `CHAT_PROVIDER=claude` is the default and explicit `mock` remains available. Storyflow owns visible history in PostgreSQL and sends the last 12 visible messages with each bounded turn. The adapter returns no provider thread ID and does not invoke Codex or a shell. Older Codex/Responses verification reports are historical; they do not describe current runtime readiness.

## Planning flow

Existing assistant-ui chat → owned FastAPI chat service → existing source/asset enrichment → `ContextBundle` → Claude preparation → optional research → final `DirectorEnvelope` → deterministic validation → existing plan/compiler/Apply flow.

Preparation selects at most two reviewed skill IDs and assesses whether context is adequate. The application permits at most one optional research round, either public search or public fetch, subject to refusal, offer/context assessment, page status and remaining budget. Search/fetch tools have bounded use counts; fetch is restricted to the supplied public domain. Final planning and at most one repair fit within four total model rounds. The SDK has automatic retries disabled. The model deadline, cumulative input budget, per-request output limit and session cost reservation bound the same work; repair is not free or outside those limits.

Research outputs are reduced to source-linked records. The adapter discards ungrounded free-text research synthesis and thinking blocks. The final prompt version is `creative-director-v3`. It requests three different narrative mechanisms, eight bounded quality scores, one selected candidate and separate script/visual/camera/performance/native-audio fields. No iterative multi-agent service, autonomous tool loop or independent critic is implemented.

## Context and sources

`services/chat_context.py` reads owned images, checks media, applies orientation/size normalization and emits PNG image attachments. Up to three attachments travel in native Anthropic image blocks. Product/person identity remains subject to existing ownership checks. Source video contributes metadata; the adapter does not claim to inspect video frames.

The existing public downloader rejects unsafe URLs, addresses and redirects. Page extraction includes bounded visible text, title, JSON-LD and available main photography. An ordinary retrieval failure can be represented as missing evidence for bounded Claude research; unsafe URLs still fail closed. User messages, images, pages and skills are untrusted evidence, not system authority.

The six allowlisted references are customer research, product marketing, offers, ad creative, copywriting and hook methodology. Only enabled, reviewed, hash-pinned manifest entries can load. Absolute paths, traversal, symlinks, unknown IDs and oversized files are rejected. The prompt initially sees compact summaries; relevant content is loaded progressively. Licenses and transformation evidence are in [THIRD_PARTY.md](THIRD_PARTY.md).

## Contracts, quality and change requests

`DirectorEnvelope` is server-only: a public `DirectorAnswer` plus a bounded candidate audit, or a clarification answer with `audit=null`. Ready Claude answers require `CreativePlan.creativeMechanism`. Historical saved plans may omit that optional public field. Exactly three candidates need unique IDs and mechanism slugs; the selected slug must match the plan.

Eight scores use 0–5: stopping power, relevance, creative idea, visual story, product integration, payoff, distinctiveness and feasibility. The selected candidate must meet 3 in each dimension and a 3.5 average. Constants in `creative_audit.py` are versioned with the rubric. These are model self-scores checked mechanically, not an independent critic, measured quality or a guarantee of truthfulness.

`SendMessage.intent` defaults to `message`; the existing Change concept button sets `change_concept` for the next send. The server reconstructs up to 24 prior accepted plans in the same creative-context fingerprint (format, URL, brief and owned input IDs). Their mechanisms are excluded only for an explicit change request. Ordinary refinements can retain a mechanism. Exact normalized slug comparison rejects known repetitions; it cannot guarantee semantic novelty when the model renames the same idea. Older plans without mechanisms cannot supply a hard exclusion. Rejected alternatives are not currently reconstructed into prior history.

Quality failures use `CREATIVE_QUALITY_LOW` or `CREATIVE_MECHANISM_REPEATED`. A repeated mechanism after the one permitted repair yields `CONCEPT_SPACE_EXHAUSTED`; malformed output uses `CHAT_INVALID_RESPONSE`. Budget/provider failures retain their own errors. The previous valid answer remains stored after a failed turn, and the submitted user message is retained. A stale revision cannot be applied until a current valid version exists.

## Persistence and privacy

- `chat_sessions`: owned visible messages, current validated answer, revision/status, provider identity and `planning_usage`.
- `chat_sessions.planning_usage`: estimated `spentCents` and outstanding reservations. Each request reserves in a committed short transaction before external I/O. Successful usage reconciles it; uncertainty survives timeout, failure and restart. Migration `0005_chat_planning_usage` adds this column.
- `chat_recipe_versions.recipe.planning`: context fingerprint, ContextBundle, CreativePlan, VideoPlan, server-only `creativeAudit` and `usage`. The planning container version remains `2`; audit prompt version is `creative-director-v3`.
- Apply copies accepted planning evidence into the existing Prompt snapshot, and existing generation snapshots retain the accepted recipe/planning evidence.

Session responses omit candidate scores, skills, source domains, usage, reservations, provider thread details and credentials. No thinking/scratchpad or raw provider events are stored. Budget values are application monetary estimates using configured implementation assumptions, not video credits or a provider invoice. Reset deletes this session's state; no account-wide planning budget is implemented.

## UI, Apply and video

The existing workspace displays Concept, Hook, Story, Script and Look. Use this concept calls the existing Apply endpoint, updates prompt/format/ratio/language and refreshes the quote through the established frontend flow. Change concept keeps the composer and session; no extra score/research panels appear. Manual keeps chat hidden. Result status/video remains below the prompt/chat section.

Generate Video alone uses the existing quote → reserve → job → worker → `OpenRouterVideoProvider` → `alibaba/wan-3.0` → output storage/history/ledger route. Real video remains 15 seconds, 480p, native audio, with 9:16 / 1:1 / 16:9. Wan 3.0 replaced Seedance 2.0 Mini because BytePlus documents that Seedance 2.x rejects ordinary real-person reference images unless they pass through its separately allowlisted LAS asset library, which OpenRouter does not expose. No TTS, provider fallback or premium route is introduced. Supplied references must meet the existing reachable HTTPS boundary.

## Operational status

See [LOCAL_CHAT.md](LOCAL_CHAT.md) for configuration and migrations. Current implementation is restricted to local development; production deployment is not authorized. Credential presence/model access, real planning quality and real video success are not inferred from mocked tests. The real creative-quality matrix remains pending. Historical account balances, worker state and relay approvals must not be treated as current facts.
