# Current local planning architecture — 2026-09-11

Chat uses the server-side Anthropic Messages API through `ClaudeCreativeDirectorAdapter`, with prompt version `creative-director-v3`. Storyflow's database owns conversation history; no Codex executable, subscription login, native thread history or OpenAI Responses chat transport is used. `CHAT_PROVIDER=claude` is the default; explicit `mock` remains available for offline development. This supersedes the earlier chat-provider amendments below.

A bounded turn has preparation, optional public research, final structured planning and at most one repair, within four total model rounds and configured token/time/cost limits. Owned images use native image blocks; reviewed allowlisted skills and sourced page facts are untrusted reference data. Internal candidate scores are model self-assessments, not an independent critic or evidence of measured advertising quality. Real matrix evaluation remains pending.

Video is unchanged: the existing quote/job/worker/storage/ledger flow uses OpenRouter Seedance 2.0 Mini, 15 seconds, 480p, native audio. Apply does not submit video or reserve video credits. Local development only; no deployment is authorized. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md) and [LOCAL_CHAT.md](LOCAL_CHAT.md).

# Backend architecture

Implementation specification: Next.js browser → same-origin API proxy → FastAPI → domain services → PostgreSQL repositories and durable jobs → provider adapters. Redis wakes workers; the database owns recoverable job state so a lost Redis message cannot lose a paid job. No real API credentials are required for mock mode.

## Boundaries

- Auth: Supabase JWT verification against issuer/JWKS/audience. Never trust browser user IDs. Explicit development identity only with APP_ENV=development and AUTH_MODE=mock; startup rejects mock authentication in production.
- Assets: bounded validated uploads to private S3/R2, owned metadata in PostgreSQL, short-lived signed reads. No public bucket requirement. Local filesystem storage may be used only in explicit development mode.
- Product resolution: allow public HTTPS URLs only; prohibit credentials, local/private/link-local addresses and unchecked redirects; timeout/size bounds. Extract title/description, never execute page content or trust it as agent instructions.
- Prompts/templates: application-owned structured template definitions; deterministic mock prompt adapter and configurable server text provider. Retain input fingerprint and user ownership. Template scene beats are internal data, not a scene editor.
- Models/providers: typed application registry; capability filtering before provider submission. No vendor IDs or secrets in public model responses.
- Credits: locked account plus append-only ledger, reservations and settlements in the same database transactions as generation state transitions.
- Generations: idempotent requests, stored quotes and normalized errors. Workers lease DB jobs, persist provider request ID, reconcile polling after restart, ingest video before completion.
- Billing: Stripe Checkout/Portal; signed webhook verification, event ID deduplication, server catalog mapping, atomic grants. Never trust a browser success URL as payment evidence.

## Creative planning

`services/chat.py` locks owned session state for short database transactions and never holds a transaction across model execution. It checks asset ownership, enriches public-page evidence and image attachments, constructs `ContextBundle`, and calls the selected server adapter. `ClaudeCreativeDirectorAdapter` sends preparation, optional research, final planning and at most one repair; SDK automatic retries are disabled. The adapter has no shell or arbitrary filesystem tool.

Before each model request, `usage_charger` commits a conservative monetary reservation to `chat_sessions.planning_usage`. Reported usage settles that reservation; unknown in-flight cost remains reserved on timeout/failure/restart. This budget is separate from the video credit ledger. Migration `0005_chat_planning_usage` adds the JSON column. Estimates use application rate assumptions and are not a provider invoice.

The public session stores only validated planning answers and visible messages. Ready recipe versions hold `planning.creativeAudit`, `planning.usage`, context and plans. Claude does not maintain a provider thread; each turn includes bounded visible history from the database. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md) for limitations and exact data boundaries.

## Runtime and operations

PostgreSQL is the production database; Redis is a queue notification mechanism, S3/R2 is private object storage. Docker Compose must provide PostgreSQL and Redis (optional MinIO). App configuration is environment-based and fails closed for production secrets/modes. Schema changes run through Alembic, not application startup create_all. Structured logs include request and generation IDs, not keys, signed URLs, prompt bodies, or raw provider payloads. Health checks distinguish liveness and database readiness. Production deployment and credentialed paid calls require separate authorization.

## Failure semantics

A request timeout retries with the same idempotency key/body. Conflicting body returns 409. Jobs recover through DB records, not browser state. Reservation release and final charge are mutually exclusive, unique ledger actions. A provider submission with unknown remote outcome must not be blindly resubmitted: persist an idempotency token where the provider supports it, otherwise flag reconciliation and bound retry. Backend must never promise exactly-once external execution without provider support.
