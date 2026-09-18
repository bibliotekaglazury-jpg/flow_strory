# Current local planning architecture — 2026-09-11

Chat uses the server-side Anthropic Messages API through `ClaudeCreativeDirectorAdapter`, with prompt version `creative-director-v3`. Storyflow's database owns conversation history; no Codex executable, subscription login, native thread history or OpenAI Responses chat transport is used. `CHAT_PROVIDER=claude` is the default; explicit `mock` remains available for offline development. This supersedes the earlier chat-provider amendments below.

A bounded turn has preparation, optional public research, final structured planning and at most one repair, within four total model rounds and configured token/time/cost limits. Owned images use native image blocks; reviewed allowlisted skills and sourced page facts are untrusted reference data. Internal candidate scores are model self-assessments, not an independent critic or evidence of measured advertising quality. Real matrix evaluation remains pending.

Video is unchanged: the existing quote/job/worker/storage/ledger flow uses OpenRouter Seedance 2.0 Mini, 15 seconds, 480p, native audio. Apply does not submit video or reserve video credits. Local development only; no deployment is authorized. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md) and [LOCAL_CHAT.md](LOCAL_CHAT.md).

# MVP product specification

## Authorized local chat extension

AI Chat is the default within Prompt; Manual retains the original brief/prompt
workflow. Chat plans a video and supports clarification, continuation, reset and an
explicit Apply recipe action. Applied recipe settings/prompt still require an
ordinary quote and the existing Generate Video submission. No automatic generation
or credit spending from conversation. Mock replies are labeled Demo. Recipe scenes
are internal planning data, not a storyboard editor. Existing visual shell, uploads,
template selector, preview and generation architecture remain in place.

## Scope and status

AI UGC / AI video generation SaaS with a simple, Content-Lab-style, one-page creation workflow. The direction and scope below are user-specified. Open behavioral choices are recorded in DECISIONS; proposed defaults are not silently approved. Implementation is authorized by BUILD_BRIEF.md; the implementation decisions below supersede earlier proposed defaults.

## Primary flow

1. **Product input:** product-image upload and product URL. Proposed validation: at least one is required, both may be supplied; confirmation pending. Do not invent URL extraction results or resolve URL-versus-image conflicts silently.
2. **Person input:** optional person-image upload.
3. **Existing video input:** optional video upload for remake/edit. This is an input to generation, not a timeline editor. Precise preservation/edit semantics remain pending.
4. **Template selection:** choose one of UGC Review, Product Unboxing, Problem → Solution, Product Demo, Testimonial, Trending Style, Hook → CTA, Before / After. No template-specific model binding. Proposed default: explicit selection rather than a silent first choice.
5. **Campaign brief:** natural-language textarea. Proposed default: nonempty brief required; length limit pending.
6. **Video settings:** duration 15 / 20 / 30 seconds; aspect ratio 9:16 / 1:1 / 16:9. Initial selection pending. Never silently substitute unsupported settings.
7. **Advanced settings:** collapsed by default. Model Auto; voice Auto; automatically generated but editable prompt; optional quality/resolution only if supported by returned capabilities. Expanding advanced settings must not start a separate workflow.
8. **Generate Prompt:** secondary action combines product, optional person, template, brief, duration, and aspect ratio into an editable production-ready prompt. Include an existing video as context when supplied. Prompt generation has its own loading/error feedback and does not create a video job. Preserve manual edits; upstream input changes invalidate prompt freshness and the credit quote. Proposed behavior: require explicit regeneration/review rather than silently overwriting edits.
9. **Generate Video:** single dominant CTA; show estimated credit cost before submission. Proposed behavior: if no current prompt exists, orchestrate prompt generation through the API, obtain a matching estimate, then require submission against that visible estimate; no hidden cost-changing submission. The exact relationship between the two actions needs approval.
10. **Result:** show actual video in the preview area on completion, with open/download action. Do not replace the one-page flow with an editor.

## Generation states

| State | Meaning and behavior |
| --- | --- |
| idle | Draft before job submission; no job ID required. |
| uploading | Local asset transfers; show real transfer feedback and prevent submission of incomplete assets. |
| queued | Server accepted a generation; show waiting state and retain job ID. |
| generating | Server processing; actual 0–100 progress or indeterminate state when unknown. |
| completed | Playable output available; allow open/download. |
| failed | Actionable normalized error; preserve draft and show explicit retry. No automatic charged resubmission. |

Idle/uploading are creation UI states; queued/generating/completed/failed are persisted job states. Asset or prompt errors occur before job creation and do not fabricate failed history jobs. After refresh, recover a submitted job through its ID/history. Poll status with backoff and stop at terminal states. Retry policy/charging treatment is pending; transport retry must reuse the same idempotency key.

## History and supporting surfaces

Recent generations below the creation flow show status, duration, thumbnail, created time, and open/download action. Pending or failed generations can lack thumbnails/output and must render truthfully. Sort newest first; paginated API, with initial visible count pending reference review. Template gallery below shares selection state with the workspace. Credits and billing are supporting utilities, not an analytics dashboard.

## Required states and acceptance

- Empty uploads, absent optional inputs, empty history, unavailable templates/models, and insufficient credits have clear text.
- Loading, upload failures, prompt failures, job failures, and connectivity errors preserve recoverable user input.
- A submission cannot proceed with incomplete assets, invalid inputs, unsupported settings, or a missing/currently invalid quote.
- Prevent double clicks from producing duplicate paid jobs; server idempotency remains authoritative.
- Mock adapters exercise the same contract and state transitions as the eventual backend; mock balances/results are explicitly test data.
- Accessibility, responsive behavior, and reference comparison are required; see UI_SYSTEM and IMPLEMENTATION_RULES.

## Out of scope for MVP

Timeline editor, node canvas, complex storyboard editor, social publishing, analytics dashboard, team collaboration, campaign management, and advanced project management. Do not add speculative features or provider-specific workflows.

## Implementation decisions (BUILD_BRIEF revision)

- Default ugc_review, 15 seconds, 9:16; brief required, maximum 4,000 characters; at least product image or URL required. Both allowed, image supplies visual identity while URL provides textual context.
- Stable template IDs use underscores per the revised brief. The eight initial templates remain; UI may abbreviate labels but Product Demo is not a ninth Lifestyle template.
- Generate Prompt is an explicit secondary action below the brief; editable preview expands on success. Any creative input change invalidates prompt freshness and quote. Editing prompt text preserves provenance. Generate Video requires current prompt and displayed server quote.
- Quality, model, voice default Auto. Only capability-supported choices appear. Unsupported input combinations fail before credits are reserved.
- Idle/uploading remain draft states; jobs add cancelled to queued/generating/completed/failed. Cancellation requests are idempotent; completion/cancellation races settle once under lock. No cancelled job may later be charged as complete.
- Development mock credits are explicitly nonmonetary. Real credits use a ledger, reserve before submission, settle once on success or release on failure/cancellation. Real pricing is environment-configured; no chargeable provider enabled by default.
- PNG/JPEG/WebP images up to 10 MB and MP4/MOV/WebM videos up to 500 MB; validate content server-side. These are initial configuration limits, not universal provider capabilities.
- Sidebar destinations from BUILD_BRIEF are authorized, but Brand Kit/Analytics/Settings can be explicit scope placeholders. Library displays generation history; Templates links to the shared gallery; Billing uses external Stripe flows.
- No fabricated hero engagement number: show a metric only if a genuine configured source exists. Omit optional brand row until authorized assets exist.
- Supabase Auth is chosen for email/Google sessions, JWT validation in FastAPI, and replaceable auth boundary. SQLAlchemy/Alembic own PostgreSQL data; R2/S3 stores binaries. Stripe hosted billing is the only payment UI.

## Phase2A — deterministic template library

The explicit Phase2A request adds a filtered /templates catalog and a deterministic render template branch. Existing generative templates remain separate. Create shows6–10recommended entries and View all templates; full search and category/type/format/duration/input/use-case filters live on /templates with URL state. Normalized schema controls replace irrelevant AI prompt/model controls for render templates. Quotes and jobs remain the same domain; render-only cost is configured separately. No editor, canvas, new AI provider, auth/billing redesign or production deployment.

## Manual simplification — user approved 2026-09-10

The user explicitly requested removal of the pictured campaign-brief block from
Manual. Remove its explanatory paragraph, brief textarea/label and Generate Prompt
action. AI Chat remains only in AI Chat mode; existing production-prompt editing
and generation settings remain. This supersedes the earlier Manual brief guidance.


## User-approved result placement — 2026-09-10
Generation status, errors and the playable result belong directly below the chat in the white workspace. Before submission show a compact explanatory empty state. The right-side reference/example video remains separate. Result dimensions follow the generation aspectRatio (9:16,1:1,16:9); never crop output to fake a format. This supersedes the original right-column placement of actual job output.
# Product understanding amendment — 2026-09-10

Existing AI Chat analyzes owned product/person images and supplied product/service URL content when Send is pressed. The user does not fill a category form. The director identifies the object/service, adapts the selected presentation style, optionally researches public product names, and asks one concise question only when essential information is unclear. URL resolution imports available photography into owned assets; Apply reuses accepted references and applies the recipe without another external page fetch or a paid video job. Claude Messages is the current chat provider. No extra frontend panels or separate product-analysis application.
