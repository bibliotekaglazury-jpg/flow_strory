# Current creative-director phase — 2026-09-10

See [CREATIVE_DIRECTOR.md](CREATIVE_DIRECTOR.md) for the current ContextBundle → CreativePlan → VideoPlan → canonical recipe flow. Auto is the default creative format; text-only offers are supported. New plans contain one 15-second clip and native audio. The existing Codex subscription transport is retained pending clarification of the conflicting Responses instruction. No OpenAI API switch or deployment has occurred. Earlier phase notes below are historical where they conflict.

# Current single-model MVP amendment — 2026-09-10

Migration 0004_video_recipe adds nullable prompts.recipe JSON and chat_recipe_versions(id,session_id,revision,recipe,created_at), unique(session_id,revision). Existing chat_sessions.messages remains visible-message persistence; no duplicate message system or reasoning storage. Generation snapshot retains applied videoRecipe.

This amendment supersedes conflicting older phase notes below. Details: [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md).

# Database schema

Local chat migration `0003` adds `chat_sessions`: id, indexed user_id, private provider
and provider_thread_id, visible messages JSON, schema-validated answer JSON, revision,
status and UTC timestamps. Each turn claims the row in a short locked transaction,
runs the provider outside the transaction, then writes only if the revision still
matches. Deletion prevents a late response from recreating a session. No token,
reasoning, raw event or provider payload is stored. Prompt application uses the
existing prompts table and does not change financial tables.

PostgreSQL, SQLAlchemy models, Alembic migrations. IDs are UUID/application-generated opaque identifiers, timestamps UTC, credits integer units. User-owned data always carries user_id and is scoped in repositories.

| Table | Purpose and key constraints |
| --- | --- |
| users | Internal user ID, unique external auth subject, email metadata; no passwords |
| subscriptions | user_id, unique Stripe subscription ID, customer ID, public plan, status, renewal timestamp |
| credit_accounts | One per user; cached ledger projection with available/reserved nonnegative checks; row locked during mutations |
| credit_transactions | Append-only purchase/subscription_grant/generation_reserve/generation_charge/generation_refund/manual_adjustment; signed available/reserved deltas, unique operation key, generation/event linkage |
| projects | Minimal ownership container; no project-management UI |
| assets | user/project, role, MIME, bytes, dimensions/duration, storage key, readiness; no video blobs or permanent public URLs |
| templates | Stable underscore ID, display fields, versioned prompt instructions and scene beats/capabilities |
| models | Application ID, provider key, private model ID, capabilities, enabled/priority/cost rules |
| providers | Provider key, enabled state and nonsecret configuration; credentials from environment |
| prompts | user, source input fingerprint/snapshot, text, creation timestamp |
| credit_quotes | user, request fingerprint, model selection, amount, expiry; accepted atomically |
| generations | user/project, input snapshot, prompt/template/model, status/progress/error, estimated/charged credits, unique (user,idempotency_key), request hash, timestamps |
| generation_jobs | unique generation, provider job ID, lease owner/expiry, attempt count, next run time, submission state; indexed runnable jobs |
| generation_outputs | generation and owned asset relation, output kind, order |
| webhook_events | unique provider/event ID, payload hash, processed timestamp; transactionally linked credit/subscription changes |

Draft UI uses idle/uploading; persisted jobs are queued/generating/completed/failed/cancelled. If draft records are stored later, idle/uploading remain nonbillable. No provider job ID is exposed in API responses.

## Ledger examples

Grant 100: available +100, reserved 0. Reserve 36: available -36, reserved +36. Settle actual 30: available +6, reserved -36, charge 30. Failure/cancel before settlement: available +36, reserved -36. Available and reserved projections must equal ledger sums; unique generation operation keys prevent duplicate reserve/settle/release. Account and generation locks serialize concurrent cancellation/completion. No UPDATE/DELETE of historical transactions in application services.

## Migration and retention

Migrations create schema before API/worker startup. Test upgrade from an empty database and verify indexes/constraints. Signed asset URLs are generated on reads; database stores keys. Retention/deletion policy is a production configuration decision; no automatic deletion of user assets in this build. External-user deletion and financial retention require a dedicated reviewed workflow before launch.
