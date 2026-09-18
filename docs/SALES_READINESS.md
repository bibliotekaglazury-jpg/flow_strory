# Sales readiness — current evidence

2026-09-10. Product is not yet verified for paid public launch. Local implementation
is authorized; deployment is not. Keep existing auth/billing/ledger/job boundaries.

| Area | Verified | Remaining before sales |
| --- | --- | --- |
| Conversation | Local ChatGPT-authenticated Codex, strict recipe, clarification, continuation, HTTP persistence | Approve a production inference/account model; current personal CLI adapter intentionally development-only |
| Video | Existing jobs/storage/history, mock lifecycle tests | Complete Higgsfield OAuth, inspect actual capabilities/submission/status/costs, finish adapter, validate real MP4 through worker and owned storage |
| Pricing | Existing quote/reservation/settlement contracts and PostgreSQL tests | Configure approved sell prices and provider costs; no invented commercial rates |
| Accounts/payments | Existing Supabase/Stripe boundaries | Configure real project/catalog/webhook and verify two-user ownership and real payment lifecycle in provider test environments |
| Storage/runtime | Local PostgreSQL, local storage and working loopback app | Approved target, private production storage, deployment configuration and operational verification |
| Commercial components | THIRD_PARTY inventory | Resolve recorded renderer/native dependency licensing before distribution/commercial renderer use |

No OPENAI_API_KEY is authorized. Do not silently replace the Codex subscription
with paid Platform inference or rebrand local single-account access as production
multi-tenant auth. Frontend and VideoRecipe interfaces remain replaceable.

Immediate user-side dependency: complete official Higgsfield browser login. Then
read workspace/model/cost metadata before any charged generation. No arbitrary
endpoint, price, duration capability, cancellation or idempotency may be guessed.
