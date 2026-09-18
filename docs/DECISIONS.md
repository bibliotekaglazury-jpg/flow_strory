# Current decision — Claude creative director, 2026-09-11

The approved Claude design and implementation plan supersede earlier Codex/Responses chat decisions. Use `ClaudeCreativeDirectorAdapter` through Anthropic Messages, prompt `creative-director-v3`, database-owned visible history, native owned-image blocks, reviewed allowlisted skills and bounded optional public research. No personal Codex login, subprocess or provider-native conversation history remains in the chat runtime.

The flow uses preparation, optional research, a final answer and at most one repair within four total rounds. Candidate summaries and scores are bounded decision records; no chain of thought is persisted. Quality thresholds validate self-scores and cannot substitute for the real evaluation matrix or an independent creative critic. No measured creative-quality improvement is claimed.

`CHAT_PROVIDER=claude` is the default; explicit `mock` remains for tests. Existing sessions from another provider are retained but require a new conversation. The per-session planning cost reservation is stored in `chat_sessions.planning_usage` and survives failures/restarts. The schema migration must run before using the updated backend. Video remains the existing OpenRouter 15-second, 480p native-audio path, with Apply separate from Generate. No deployment, secret-file editing or paid verification was performed as part of implementation.

Earlier ADRs below are historical decisions; this entry governs conflicting chat-provider statements. Current operation and known limits are in [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md).

## ADR — Separate creative planning from provider compilation (2026-09-10)

Accepted scope: ContextBundle, CreativePlan and a single-clip 15-second VideoPlan precede canonical compilation. One structured model response, no duplicate services, generation queue or financial tables. Auto chooses an existing format; formats are biases only. Existing JSON records retain review evidence and old recipes remain readable. Native audio only. Keep Codex subscription while the contradictory OpenAI Responses request awaits clarification; no paid OpenAI configuration or deployment. See [CREATIVE_DIRECTOR.md](CREATIVE_DIRECTOR.md).

# Architecture decision log

## ADR-018 — Local conversation via Codex and replaceable video provider

Accepted by the user's current implementation request: assistant-ui primitives,
custom runtime → existing FastAPI → provider-neutral ChatProvider → official local
Codex CLI authenticated with ChatGPT. No OpenAI Platform credential dependency is
introduced. Codex owns authentication and refresh. Mock mode is the default, tests
must not consume external credits. Local providers are single-account development
integrations, not production tenant authentication.

Application DB/logs retain only visible conversation and validated recipe. Native
Codex resume history may contain model items outside Storyflow's control; whether
that history is permitted is an outstanding user clarification. Local inference
remains gated by `CODEX_NATIVE_HISTORY_ALLOWED=false` until resolved. This flag is
not a substitute for verifying runtime tool controls or running an authorized smoke.

Higgsfield CLI OAuth and MIT package were audited. Authentication has not completed;
live JSON/capability audit and paid worker integration are unfinished. The local
adapter therefore fails closed and is not registered as an available generation
option. Do not confuse its presence with a verified live provider. Existing Mock
and MuAPI routes remain authoritative. Native CLI generations consume standard
Higgsfield account credits, separately from Storyflow's quote/ledger units.

Date: 2026-09-10. “Accepted” means explicitly specified by the user; it does not authorize implementation. “Proposed” means a documented choice awaiting review. No final generation, auth, billing, or hosting vendor is selected.

## ADR-001 — Simple creation workflow

Status: Accepted. Context: users need to create an AI UGC video with low cognitive load. Decision: use a simple Content-Lab-style one-page input → template → brief/settings → prompt → video workflow. Consequence: keep preview, templates, and recent generations in the approved composition; no campaign or project-management layer.

## ADR-002 — No timeline/editor in MVP

Status: Accepted. Context: an existing-video input supports remake/edit requests. Decision: treat it as a generation input; exclude timeline, node canvas, and complex storyboard editing. Consequence: detailed remake semantics still require definition, without expanding editor scope.

## ADR-003 — Dark shell and white creation workspace

Status: Accepted for direction; exact tokens pending. Context: the mockup is the primary visual authority. Decision: dark shell, white central workspace, lime accents, premium sans-serif UI with the reference’s editorial serif hero. Consequence: no generic AI-SaaS redesign; reconcile provisional tokens against the original REF-001 image file before visual implementation.

## ADR-004 — Provider-agnostic backend boundary

Status: Accepted. Context: generation providers can change. Decision: expose application-owned API contracts and normalize vendor responses server-side. Consequence: presentation components never consume vendor SDKs, routing rules, or error formats. Required provider field is opaque nullable metadata, not a display dependency.

## ADR-005 — Auto model routing by default

Status: Accepted. Context: model selection should not complicate the primary flow. Decision: collapsed advanced settings, model Auto and voice Auto; optional public model choices come from capabilities. Consequence: backend owns selection and validates supported settings without silent substitution.

## ADR-006 — Templates are business logic

Status: Accepted. Context: the eight templates express creative intent. Decision: stable product templates independent of model/provider. Consequence: provider changes do not alter template identity or selection UX.

## ADR-007 — Frontend independent of final provider

Status: Accepted. Context: provider selection must not block contract-based frontend work after approval. Decision: Next.js, TypeScript, Tailwind, shadcn primitives, shared typed API client, mock/HTTP adapters. Consequence: consistent data shapes and realistic states without provider imports or duplicated API logic.

## ADR-008 — Established auth and billing services

Status: Accepted; service choices pending. Context: authentication and payments are supporting capabilities. Decision: use established external components/services rather than custom implementations. Consequence: server-authoritative identity and balances, hosted checkout/portal, no bespoke auth/payment system.

## ADR-009 — Quotes and submission safety

Status: Proposed. Context: cost must be visible before generation and duplicate jobs must be prevented. Decision: expiring server quotes, atomic credit validation/reservation, idempotent job submission, explicit resubmission after price changes. Consequence: quote and idempotency fields enter the frontend contract; charging/refund economics still need approval.

## ADR-010 — Distinguish draft and job states

Status: Proposed normalization of required states. Context: uploading occurs before a generation job exists. Decision: idle/uploading are local creation states; queued/generating/completed/failed are persisted jobs. Consequence: preflight upload/prompt failures do not create fictitious history entries.

## ADR-011 — Supplied frontend reference

Status: Accepted as visual reference on 2026-09-10; implementation remains unapproved. Context: the user supplied REF-001 after documentation preparation. Decision: use its desktop composition, icon-and-label sidebar, serif hero, white input workspace, adjacent portrait preview, and lower thumbnail rows. Consequence: earlier 80 px rail and 36 px sans-serif hero proposals are superseded. Original product exclusions remain binding: no copied branding, analytics, fake metrics, or unrequested navigation. The source attachment has been inspected but is not stored as a repository file.

## Initial open decisions (historical; resolved entries superseded below)

| Item | Gap or tension | Required resolution / blocked work |
| --- | --- | --- |
| Reference persistence | REF-001 supplied and visually inspected in conversation; original file is not saved in the repository. | Persist original image and record verified path/dimensions for future agents; do not claim image file was saved. |
| Exact design values | REF-001 establishes composition and serif hero, but exact font family and pixel colors remain unidentified. | Verify original-file measurements; UI_SYSTEM numbers remain approximate/provisional. |
| Hero language | “Large but restrained” versus “no oversized hero.” | Interpret as concise product heading; preserve the observed approximately 342 px top band and avoid extra marketing sections. |
| Responsive navigation | Desktop has approximately 178 px icon-and-text sidebar; mobile view is not supplied. | Approve MVP destinations and mobile adaptation without adding patterns. |
| Product inputs | Image and URL listed without AND/OR validation or precedence. | Proposal: at least one, both allowed; define conflict handling. |
| Brief and defaults | Requiredness, length limits, default duration/ratio/template unspecified. | Confirm before implementing validation/default selection. |
| Remake behavior | Video upload requested, but preservation/edit instructions unspecified. | Define treatment of source content, audio, duration, and user brief. |
| Reference-only controls | Step indicator, quick start, preview thumbnail strip, notification bell, and upsell appear in REF-001 but have no fully specified MVP behavior. | Keep step indicator as in-page guidance; define necessary thumbnail behavior and secondary Generate Prompt placement. Do not add quick-start, notification, or upsell flows without scope approval. |
| Prompt workflow | Secondary Generate Prompt plus single dominant Generate Video; auto-generation wording could imply different sequencing. | Approve prompt freshness/edit preservation and first-generation orchestration before implementing submission. |
| Capabilities | Required durations/ratios may not be available on the eventual provider; voice catalog unspecified. | Validate capabilities and Auto routing; approve handling of unavailable combinations. |
| Uploads | Formats, size/duration limits, retention, expiring staged URLs unspecified. | Define server limits and UI validation before upload integration. |
| Credits and billing | Pricing, plans/catalog source, reservations, final charges, refunds, retries, prompt costs unspecified. | Approve economics and proposed quote contract before paid integration. |
| Provider field | Required Generation.provider versus no provider leakage into presentation. | Keep nullable opaque metadata in transport only, exclude from view props; do not branch on it. |
| Runtime/source | Empty UGC directory is not a git worktree; CBM indexes other projects. Supplied operational rules name Cerebro production and require VPS runtime. | Verify/init authorized UGC source/index and establish a separate authorized runtime target before code/runtime work; never infer UGC belongs on Cerebro production. |
| Service selection | Auth, billing, generation provider, package versions not selected. | Decide when relevant after implementation approval; do not add vendor-specific assumptions now. |

## Preparation evidence

CBM MCP exposed: yes. CLI fallback used: no. Supplied fallback project queried: `Users-stas-Documents-CEREBRO_VPS_SOURCE_MIRROR_CLEAN`, 105,181 nodes / 186,244 edges; no UGC project was listed. Query: `UGC frontend design tokens templates generations`, limit 10. Results: unrelated `_modelish_tokens`, `_model_tokens`, `_finish_tokens` in `apps/api/app/modules/integrations/market_enrichment.py`; `normalized_tokens` in `apps/api/app/modules/visibility/ai_buyer_prompts.py`; Gmail/Shoper integration test symbols and `upgrade`/`downgrade` functions in password-reset/mail-account-token migrations. Search reported 11 total matches and returned 10; no further paging was relevant to UGC. `detect_changes` returned zero changed files or impacted symbols. These results do not establish UGC code knowledge. Only documentation was created; no runtime or production change was attempted.

## ADR-012 — User-supplied hero background

Status: Accepted for the hero only. Context: the user supplied the exact background CSS after approving the reference artwork. Decision: preserve it as HERO-003 in `docs/references/hero-background.css`, with only transport-format cleanup of escapes and the malformed grain SVG URL. Consequence: the supplied gradient/glow/grain layers override the earlier blanket restriction for this hero background only; other surfaces retain the anti-slop rules. No application integration or visual verification has occurred.

## ADR-013 — Implementation authorization and revised MVP

Accepted: BUILD_BRIEF.md authorizes implementation, the Next.js/FastAPI monorepo, cancellation, URL resolution, Stripe webhooks, sidebar placeholder destinations and a durable ledger. Earlier documentation-only statements are historical. Current source is the Git working tree at /Users/stas/Documents/UGC on feat/ugc-mvp. CBM UGC project now exists (16 nodes/14 edges before code); MCP transport later failed and CLI list/search/detect succeeded. Local runtime is authorized by ADR-015; no production runtime is inferred.

## ADR-014 — First real provider and cancellation truthfulness

MuAPI Seedance 2.5 official OpenAPI documents 4–30 second durations and text/image/omni-reference/edit modes, covering required 15/20/30 presets. Implement server-only MuAPI adapter plus mock. Public application model IDs remain stable and provider-independent. No public prediction cancel endpoint is documented: cancellation after actual remote submission returns CANCELLATION_UNAVAILABLE rather than fabricating a refund/cancel. Local queued jobs can cancel and release credits atomically. Real price rules come from environment configuration; no paid requests are made during development.

## ADR-015 — Local runtime authorization

The user explicitly said “делаем пока локально”. Local UGC development, Docker services, tests, and browser verification are authorized. This supersedes the earlier VPS-only runtime restriction for UGC only; no Cerebro or production deployment is authorized.

## ADR-016 — Saved hero portrait and verification status

The user supplied `/Users/stas/Downloads/hero  girl.png`. Preserve its 1222×1287 RGBA PNG unchanged in docs/references and public assets. HERO-001 is now integrated. Desktop and responsive screenshots are recorded in VERIFICATION.md. Earlier missing-reference and documentation-only entries are historical. Product validation/defaults, prompt workflow, upload limits and service choices are resolved by PRODUCT_SPEC's implementation decisions. Remaining open items: final brand/copy, approved photographic template assets, cross-platform SVG lettering, paid provider economics, media retention and credentialed external integration checks. Do not treat local simulation as verified production operation.

## ADR-017 — Phase2A RVE library

Extend existing Template domain to support generative and remotion explicitly; contrary to the prompt's assumption, inspected baseline had only8generative recipes and a small VideoTemplate DTO. Keep existing job/ledger/provider boundaries. Import only audited RVE source; code is MIT-declared by upstream README, remote demo photos excluded. Generate registry and manifests, safe thumbnails, schema-driven inputs and shared filter conformance cases. Enable only validated records; discovery/import is not render validation. Deterministic work uses existing leased worker and private storage, with render_only quote pricing separate from AI. Local Remotion evaluation is authorized; production commercial license is not inferred. /templates is an explicitly requested new catalog, not a redesign of Create.

## ADR-019 — Native Codex history authorized; live chat repair

Accepted 2026-09-10: user approved proceeding after the explicit explanation that
Codex may retain its own resume history. Storyflow still stores only visible
messages, validated recipes and opaque thread IDs; no reasoning or credential data.
This authorizes local connection and its bounded smoke verification, not production
deployment or sharing a personal account as multi-tenant authentication.

Repair scope: distinguish the installed CLI's exact nonfatal disabled-code-host
notice from actual errors; verify clarification and resume with a real conversation;
use an explicit local launch configuration, leave tests mocked. Manual explains its
brief field and missing prerequisites; scenario labels use readable copy, not JSON
keys. Existing reference layout and generation/ledger/auth boundaries are preserved.
Sales readiness requires verified live video generation, production auth/storage and
billing configuration, pricing, deployment target and an appropriate production chat
service. These are not established by a local Codex login.

## Manual simplification — user approved 2026-09-10

The user explicitly requested removal of the pictured campaign-brief block from
Manual. Remove its explanatory paragraph, brief textarea/label and Generate Prompt
action. AI Chat remains only in AI Chat mode; existing production-prompt editing
and generation settings remain. This supersedes the earlier Manual brief guidance.


## ADR — Single real video route and Responses director (2026-09-10)
Accepted by the latest implementation request. Replace active Higgsfield/Codex conversation plan with OpenAI Responses structured VideoRecipe and OpenRouter Seedance 2.0 Mini. Keep mock-only automated tests, one authorized paid test per integration, 15s native audio, and existing architecture. Remove Higgsfield runtime/dependency; leave historical audit records. No other production video models, TTS, premium or deployment. Preserve prior Manual field removal. Recipe contracts remain provider-neutral and historical saved plans remain readable. Secret transfer authorization is scoped independently; OpenRouter transfer is authorized, separate OpenAI production-key transfer remains pending automatic-review clarification.

Operational clarification: an existing OPENAI_API_KEY in the process environment was discovered without transfer and used for the single authorized validation. It was rejected as invalid (read-only model check401). No repeat inference call. A working replacement remains required; adding .env alone will not override a stale process environment.


## ADR — Restore subscription-backed Codex chat (2026-09-10)
Latest explicit user correction supersedes the Responses chat decision. Restore CodexLocalAdapter and ChatGPT login; remove experimental OpenAIChatProvider and its real-test launcher. No OpenAI key copying or API billing for chat. Keep OpenRouter exclusively for Seedance Mini15s native-audio video, with existing jobs/ledger/storage. Retain compatible recipe language fields and prior Manual removal. Codex native session-history permission restored to its prior local setting; Storyflow does not store reasoning. No new paid video calls.


## Result placement (2026-09-10)
User requests actual generated video immediately below chat. Reuse Preview inside workspace, with idle guidance, queued/generating/failed/completed states, controls and download. Right-hand example remains separate. Aspect ratio is passed unchanged from selected form state to chat context, applied recipe, quote/generation and player. UI verification uses mocks, not paid generation. User reports OpenRouter funding; this is not proof of worker/storage readiness.

## ADR — Collapsible desktop sidebar (2026-09-12)

The user explicitly approved a compact desktop sidebar state. The top sidebar
control toggles between the existing labelled navigation and a 64 px icon rail.
Hovering or keyboard-focusing a navigation icon expands the sidebar and leaves it
expanded; only the control collapses it again. Mobile retains the existing
horizontal navigation and does not show the collapse control. This supersedes the
earlier icon-only-rail exclusion for this interaction only.
## ADR — Still look previews alongside the video route (2026-09-13)

The user asked for a dedicated e-commerce try-on step: several products uploaded at
once, shown worn together on their model as a photo, before any video is generated,
with extra catalogue angles afterwards. Video is one use of that look, not the only
one, so this is a second media capability rather than a change to the video route.

It ships as a separate, bounded path: `POST /api/try-on` calls OpenRouter's Images API
(`google/gemini-3-pro-image`, documented for identity preservation across up to five
subjects and up to 14 reference images) and returns the stored image in the same
response. It deliberately does not use the Quote/Generation/Job/worker pipeline: that
machinery exists because a video render takes minutes and must survive restarts, while
a preview answers in one request. Credits are debited directly through the existing
`credits.change()` ledger with a caller-supplied idempotency key, and only after an
image actually comes back.

`alibaba/wan-3.0` and the whole video pipeline are untouched. Dedicated virtual try-on
models (FASHN, Kling Kolors, FLUX VTO) were rejected because each is documented as one
garment per request, which cannot express a multi-piece look in a single shot.

The look cap rises from three product images to five (`LOOK_SIZE`), matching the
compositing model's documented identity-preservation range, and `POST /api/assets/bulk`
uploads a whole look in one request.

# Product understanding in the existing chat — 2026-09-10

Accepted by user: image and URL understanding through the current Codex subscription. Existing owned upload IDs and productUrl feed actual image attachments and bounded public-page evidence to the director. Built-in web research is allowed; shell/MCP and arbitrary filesystem execution remain disabled. No manual category input, separate agent service, keyword-based product routing, or new chat provider. UGC Review adapts presentation to the observed object/service. Compilation no longer injects a blanket advertising-claims prohibition. Source facts and creative proposals remain distinguishable. Analysis occurs on Send using current form inputs. No paid video generation is part of this implementation verification.
