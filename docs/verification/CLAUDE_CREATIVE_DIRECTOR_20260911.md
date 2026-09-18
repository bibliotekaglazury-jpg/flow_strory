# Claude Creative Director implementation verification — 2026-09-11

Status: local implementation and offline integration verified. A real Claude Sonnet 5 planning turn now passes every automated contract/quality check after transport-schema and mechanism normalization fixes. Full multi-scenario creative quality validation remains incomplete and requires human review. No paid video was generated and no deployment/Git operation was performed. Real `.env` was not modified by the implementation.

## Actual implementation

Frontend Send → existing owned FastAPI chat service → existing URL/image resolver → ContextBundle → Claude preparation → allowlisted skill loading → optional bounded search/fetch → strict DirectorEnvelope → optional single repair → normalize/compile → persisted answer and recipe version → existing Apply → existing quote/job/worker/storage/history.

Normal no-research turn makes two inference requests (preparation and final). Research adds one; a repair adds one, with four requests maximum. Token counting precedes each inference request. Native Anthropic images carry the owned product/person references. Skills are reviewed MIT derivatives with hashes and pinned commits. Separate research calls avoid mixing citations with structured JSON and avoid retaining private thinking for tool continuation.

The final envelope includes three candidate summaries with different mechanism slugs, bounded scores, selected ID, CreativePlan and one 15-second VideoPlan. Numeric thresholds validate model self-scores; there is no independent critic, guarantee of semantic diversity, or claimed creative improvement from mock fixtures. Change concept is explicit request intent. Prior selected mechanisms are bounded and scoped to the form/asset fingerprint; failed candidates are not accepted plans. Ordinary refinement is not hard-excluded.

The existing video path remains OpenRouter/Seedance 2.0 Mini, 15 seconds, 480p and native audio. No TTS, extra active video provider, longer duration, timeline or frontend redesign was added. Mock workflows validate 9:16, 1:1 and 16:9 through actual stored MP4 metadata and history.

## Changed areas

- `apps/api/app/providers/claude.py`, `providers/chat.py`, `prompts/video_chat/v3.py`, `creative_audit.py`, `creative_direction.py`.
- `config.py`, `services/chat.py`, `services/chat_context.py`, `chat_api.py`, `db.py`, Alembic `0005_chat_planning_usage.py`, `pyproject.toml`.
- `creative_skills/` reviewed catalog/vendor files and `docs/audits/claude-skill-*`; `docs/THIRD_PARTY.md`.
- `packages/contracts/chat.ts` and generated JSON schemas; existing `apps/web/features/chat/`, `services/mock-chat.ts`, browser tests.
- New Claude config/adapter/audit/prompt/integration/workflow/skill/harness tests and validation fixtures.
- `.env.example`, `scripts/chat/run-local-api.sh`, `scripts/chat/validate_claude_director.py` and operational documentation.
- Removed the Codex subprocess adapter and its adapter-specific tests/settings. Obsolete `CODEX_*` env names are ignored; the launcher explicitly sets Claude without modifying the real env file.

## Verification evidence

| Check | Result |
| --- | --- |
| Full offline backend suite | 214 passed, 12 PostgreSQL-only skipped; completed after the compact structured transport and mechanism normalization fixes |
| Isolated PostgreSQL suite | All 12 passed, including real local Remotion rendering; temporary `ugc_codex_test_b59280174e41` created/migrated/dropped, live UGC database untouched by tests |
| Three-ratio Claude-shaped workflow + migration tests | 4 passed: actual mock MP4/ffprobe, stored output/history, quote/reserve/settle, idempotency; SQLite upgrade/downgrade/reupgrade with existing chat-row backfill |
| Frontend unit tests | 38 passed |
| Browser mock E2E | 15 passed: Polish product/person→chat→Apply→Generate→preview/history; URL product reference; all aspect ratios; failures/Manual/Change concept; desktop/mobile |
| Backend Ruff | Passed for app and tests after the final fixes |
| Frontend ESLint | Passed |
| TypeScript | Passed after build; an initial simultaneous typecheck/build raced on generated `.next/types`, then sequential typecheck passed |
| Production webpack build | Passed locally, no deployment |
| Schema export | Second export byte-stable |
| Browser secret scan | 82 static browser files checked against configured Anthropic/OpenRouter secret values; no matches, no secret values printed |
| Local runtime | Frontend http://127.0.0.1:3000 returns 200; API http://127.0.0.1:8000/health/ready returns ok; migrated local UGC database to head and restarted API using the updated launcher |

Commands: `pytest apps/api/tests -q` with dotenv disabled for offline fixtures; `RUN_POSTGRES_TESTS=1` only against the isolated temporary database; `pnpm --filter @ugc/web test`, `lint`, `typecheck`, `build`; `pnpm exec playwright test chat.spec.ts create.spec.ts product-url-flow.spec.ts result-placement.spec.ts --workers=2`; `ruff check app tests`; `scripts/chat/export-schema.py` twice. Browser and PostgreSQL checks required escalation because sandbox denied Chrome/loopback access. These were environment restrictions, not waived assertions.

Visual evidence and comparison notes: [desktop/mobile report](claude-chat/README.md), [desktop](claude-chat/chat-concept-1222.png), [mobile](claude-chat/chat-concept-390.png). Shell, workspace, tokens and result placement preserved; existing responsive flow verified. No claim of pixel accuracy against an absent mobile mockup.

## Real Anthropic result and remaining validation

The replacement workspace-scoped API key works without an explicit `ANTHROPIC_WORKSPACE_ID` header. Token counting and inference both succeeded; the key value was never printed or copied into browser code.

Anthropic rejected the original full nested strict schema because its compiled grammar was too large. The final adapter uses a small strict outer Structured Output envelope and JSON-encoded inner plans whose exact canonical schemas are supplied to Claude and then fully validated by Pydantic server-side. It also normalizes human-readable creative-mechanism labels into stable slugs before validation. No arbitrary prose/JSON extraction is used.

One real physical-product planning turn then passed all automated checks: schema, candidate quality thresholds, spoken language, required facts, forbidden claims, prior-mechanism exclusion and 15-second duration. Claude selected mechanism `reveal-unwrap` and returned: “Treat the supplied illustration itself as the star: a quiet paper-wrap reveal that frames Luma Soap as an effortless, considered little gift, then invites the viewer to see the full collection.” The spoken script was: “A little lavender, wrapped simply. Luma Soap — handmade, and ready to give. Come visit the collection.” Usage was 9,149 input tokens, 4,680 output tokens, two inference rounds and an application estimate of 6.5098 cents.

An earlier three-turn matrix reached Claude but failed canonical validation before the mechanism-label fix; it recorded an application estimate of 37.3748 cents. Together those two recorded runs account for 43.8846 estimated cents. Small diagnostic/token-count attempts are not included, so this is not asserted as the Anthropic invoice total. [Machine-readable attempt report](CLAUDE_CREATIVE_DIRECTOR_20260911.json) preserves both the failed matrix and the successful control. No video generation ran. The remaining three-case/Change Concept/injection matrix should be run only if more paid planning validation is explicitly desired; aggregate application guard remains ≤100 cents.

## Practical limitations

- Application reserves estimated maximum cost before each request and retains unknown reservations after cancellation/errors. Native server tools may use internal tokens before reporting usage: this is not an Anthropic-side hard spending cap. Use provider workspace limits as an additional ceiling. Resetting a chat creates a new session budget, not a user/account-wide spending limit.
- Input budget is cumulative; output ceiling is per request under the maximum round count. Standard-rate estimates use $2/M input, $10/M output and $0.01/search; billing is not inferred from video credits.
- Injection tests prove quoted-evidence boundaries, tool restrictions, absence of credential/metadata injection, thinking filtering and fail-stop harness behavior. They do not prove universal resistance to arbitrary model prompt injection. The bounded real adversarial check and semantic human review remain necessary.
- Research adequacy is model-assessed. Application gates explicit refusal patterns, sufficient-context flags, domains, quotas and final-round reservation. Refusal detection is not guaranteed for every natural language. Research sources are bounded cited snippets/documents, not model-authored unsourced conclusions.
- After a failed turn, the last valid answer remains visible for reference, but Apply requires a matching successful revision. No stale plan is silently submitted.
- Model ID `claude-sonnet-5` is confirmed by a successful runtime response for this account. No model fallback is configured.
