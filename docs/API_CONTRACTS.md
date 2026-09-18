# Current local planning architecture — 2026-09-11

Chat uses the server-side Anthropic Messages API through `ClaudeCreativeDirectorAdapter`, with prompt version `creative-director-v3`. Storyflow's database owns conversation history; no Codex executable, subscription login, native thread history or OpenAI Responses chat transport is used. `CHAT_PROVIDER=claude` is the default; explicit `mock` remains available for offline development. This supersedes the earlier chat-provider amendments below.

A bounded turn has preparation, optional public research, final structured planning and at most one repair, within four total model rounds and configured token/time/cost limits. Owned images use native image blocks; reviewed allowlisted skills and sourced page facts are untrusted reference data. Internal candidate scores are model self-assessments, not an independent critic or evidence of measured advertising quality. Real matrix evaluation remains pending.

Video is unchanged: the existing quote/job/worker/storage/ledger flow uses OpenRouter Seedance 2.0 Mini, 15 seconds, 480p, native audio. Apply does not submit video or reserve video credits. Local development only; no deployment is authorized. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md) and [LOCAL_CHAT.md](LOCAL_CHAT.md).

# Frontend API contracts

## Local video chat extension — 2026-09-10

The canonical schemas are `app/video_recipe.py`, exported
`packages/contracts/video-recipe.schema.json`, and shared TypeScript `chat.ts`.
Unknown fields and invalid recipe timing are rejected. Quality currently permits
only Auto, matching existing capabilities; this does not promise premium quality.

| Endpoint | Request | Response |
| --- | --- | --- |
| POST /api/chat/sessions | Empty object | 201 ChatSession |
| GET /api/chat/sessions/:id | Owned session ID | ChatSession |
| GET /api/chat/sessions/:id/messages | Owned session ID | ChatMessageData[] |
| POST /api/chat/sessions/:id/messages | `{text, intent?: "message" | "change_concept", context: {templateId,inputAssets,duration,aspectRatio,productUrl?,brief?}}` | ChatSession |
| DELETE /api/chat/sessions/:id | Owned session ID | `{deleted:true}`; cancels local turn and removes application conversation |
| POST /api/chat/sessions/:id/apply | `{revision,creative}` | `{creative,prompt:PromptResult}` |

ChatSession contains id, visible messages, answer, revision, idle/responding status,
simulated flag and timestamps. No provider/thread identifiers or authentication data
are public. RecipeAnswer has assistantMessage, needsMoreInformation,
clarificationQuestion and recipe, plus optional creativePlan/videoPlan. CreativePlan
accepts an optional normalized creativeMechanism for backward compatibility. The
Claude response envelope requires it for a ready plan. A clarification cannot be applied. Recipe fields:
intent, concept, duration, aspectRatio, qualityTier, subject, product, visualStyle,
camera, performance, scenes (duration/description), audio, constraints, negativeRules.

Apply checks the stored revision and current asset ownership, stores a normal Prompt
with creative fingerprint, and returns updated draft settings. Frontend drops the old
quote and requests a new one. Neither chat nor apply reserves or spends video credits
or submits a generation. Only the existing Generate Video action can do that.
Maximum 4,000 characters/message and 40 visible messages/session; concurrent turns
return CHAT_BUSY. Failed replies preserve the submitted user message. Raw provider
events, tool outputs and reasoning never enter these contracts. Candidate audits,
loaded skills, source domains, usage and budget reservations are server-only.
`intent` defaults to `message`; `change_concept` explicitly requests exclusion of
previous mechanisms in the same creative context. A quality/budget failure preserves
the previous answer and saves the submitted user message. Stable failures include
CREATIVE_QUALITY_LOW, CREATIVE_MECHANISM_REPEATED, CONCEPT_SPACE_EXHAUSTED,
CHAT_BUDGET_EXCEEDED and CHAT_PROVIDER_CHANGED.

## Contract status and conventions

Proposed v1 frontend contract for review; no backend endpoints or application code are implemented. TypeScript below is documentation only. Product enums are fixed by the brief; envelope, quote, validation, and billing semantics are proposed architecture decisions.

All endpoints are same-origin `/api`, authenticated through the eventual established auth service. Server derives user identity from the session; requests never accept a trusted userId. Return only the current user's assets, jobs, credits, and billing resources. Use JSON except multipart upload. IDs are opaque strings, timestamps UTC ISO 8601, credits nonnegative integers in the product's credit unit, and URLs absolute HTTPS except explicitly configured development fixtures. Nullable values are explicit; no provider SDK types or raw provider errors cross this boundary.

All non-2xx responses use ApiErrorResponse. Common HTTP statuses: 400 invalid input, 401 unauthenticated, 403 forbidden, 404 unavailable resource, 409 conflict/stale quote, 413 upload too large, 415 unsupported media, 422 unsupported settings, 429 rate limited, 503 temporarily unavailable. API client normalizes network errors to the same application error shape. Never expose stack traces, credentials, or provider payloads.

```ts
type Id = string;
type ISODateTime = string;
type Duration = 15 | 20 | 30;
type AspectRatio = "9:16" | "1:1" | "16:9";
type GenerationStatus = "queued" | "generating" | "completed" | "failed";
type CreationState = "idle" | "uploading" | GenerationStatus;
type AssetRole = "product" | "person" | "source_video" | "output_video" | "thumbnail";
type ModelSelection = "auto" | Id; // IDs owned by this API, never vendor model IDs.
type VoiceSelection = "auto" | Id;
interface ApiError {
  code: string; // Stable application code, e.g. INSUFFICIENT_CREDITS.
  message: string; // Safe user-facing text.
  fieldErrors?: Record<string, string[]>;
  retryable: boolean;
}
interface ApiErrorResponse { error: ApiError; requestId: string }
interface Asset {
  id: Id;
  role: AssetRole;
  kind: "image" | "video";
  mimeType: string;
  fileName: string;
  sizeBytes: number;
  url: string;
  urlExpiresAt: ISODateTime | null;
  width: number | null;
  height: number | null;
  durationSeconds: number | null;
  createdAt: ISODateTime;
}
interface InputAssets {
  productImageId?: Id;
  personImageId?: Id;
  sourceVideoId?: Id;
}
interface CreativeInput {
  productUrl?: string;
  inputAssets: InputAssets;
  templateId: Id;
  brief: string;
  duration: Duration;
  aspectRatio: AspectRatio;
}
interface RenderSettings {
  model: ModelSelection;
  voice: VoiceSelection;
  quality?: string; // Only an ID advertised by capabilities.
  resolution?: string; // Only an ID advertised by capabilities.
}
interface Generation {
  id: Id;
  userId: Id;
  templateId: Id;
  model: ModelSelection;
  provider: string | null; // Opaque server metadata, not a UI dependency.
  status: GenerationStatus;
  progress: number | null; // 0–100; null means unknown, not zero.
  prompt: string;
  duration: Duration;
  aspectRatio: AspectRatio;
  inputAssets: Asset[];
  outputAssets: Asset[];
  creditsEstimated: number;
  creditsCharged: number;
  error: ApiError | null;
  createdAt: ISODateTime;
  updatedAt: ISODateTime;
}
```

`model` echoes the requested public selection, including Auto; actual vendor routing stays server-side. `provider` is included to meet the required object shape, but may remain null and is not rendered, branched upon, or forwarded into presentation props. Product view models select only display fields. Job progress is independent of local upload progress. Completed jobs must contain an output_video asset; failed jobs must contain an error. Nonfailed jobs have error null. Output may be empty before completion. creditsCharged is the actual net charge so far; no inferred refund promises.

## POST /api/assets — upload an image/video asset

Authenticated multipart/form-data with `file` and `role`. Response 201 only after an asset is ready for use. No public arbitrary storage keys or provider upload URLs. Server validates ownership, role, actual media type, and size; permitted formats/limits and media retention are pending decisions. Product/person must be images; source_video must be video. URL product input is not an asset upload.

```ts
interface UploadAssetRequest {
  file: File; // Browser multipart field, not JSON.
  role: "product" | "person" | "source_video";
}
interface UploadAssetResponse { asset: Asset }
```

Upload transfer progress belongs to the API adapter. No staged-upload or resumable-upload feature is implied. Recover expired display URLs by refetching their owning generation; staged asset expiration behavior remains to be decided.

## POST /api/prompts/generate — generate an editable production prompt

Response 200. Combines the supplied creative input; if source video is provided, include remake context. URL fetching/extraction happens server-side with public-URL validation and SSRF protection. No browser scraping or fabricated product claims.

```ts
interface GeneratePromptRequest extends CreativeInput {}
interface GeneratePromptResponse {
  promptId: Id;
  prompt: string;
  inputFingerprint: string;
  createdAt: ISODateTime;
}
```

Fingerprint is opaque evidence of the source input, not something presentation components compute. Preserve promptId when editing generated text; generation submission includes final prompt text. Input changes mark the previous prompt stale. Prompt generation pricing is pending; do not assume free or charge silently.

## GET /api/templates — available video templates

No query/body. Response 200. Initial IDs below are stable product IDs; templates contain no provider/model binding.

```ts
type GetTemplatesRequest = Record<string, never>;
interface VideoTemplate {
  id: Id;
  name: string;
  description: string;
  thumbnailUrl: string | null;
  available: boolean;
  unavailableReason: string | null;
}
interface GetTemplatesResponse { templates: VideoTemplate[] }
```

| ID | Name |
| --- | --- |
| ugc-review | UGC Review |
| product-unboxing | Product Unboxing |
| problem-solution | Problem → Solution |
| product-demo | Product Demo |
| testimonial | Testimonial |
| trending-style | Trending Style |
| hook-cta | Hook → CTA |
| before-after | Before / After |

## GET /api/models — advanced model choices and capabilities

No query/body. Response 200. Auto must be provided as the default public choice. Return supported combinations, not independent lists that imply invalid combinations are supported. Voice options are embedded here because no separate voice endpoint is in MVP scope.

```ts
type GetModelsRequest = Record<string, never>;
interface SupportedConfiguration {
  duration: Duration;
  aspectRatio: AspectRatio;
  quality: string | null;
  resolution: string | null;
  supportsPersonImage: boolean;
  supportsSourceVideo: boolean;
}
interface ModelOption {
  id: ModelSelection;
  label: string;
  available: boolean;
  unavailableReason: string | null;
  configurations: SupportedConfiguration[];
  voices: Array<{ id: VoiceSelection; label: string }>;
}
interface GetModelsResponse { models: ModelOption[] }
```

Auto capabilities represent combinations the server can actually route. No vendor identifiers, SDK payloads, or template-to-model maps. Unsupported options must be explained, not silently downgraded. Commercial support for all requested duration/ratio combinations must be confirmed before launch.

## POST /api/generations — create a generation job

Required `Idempotency-Key` header. Response 202 with accepted job; repeat identical key/body returns the same job without another charge. Same key with changed body returns 409. UI prevents duplicate submission but server enforces idempotency.

```ts
interface CreateGenerationRequest extends CreativeInput, RenderSettings {
  promptId: Id;
  prompt: string; // Final text, including user edits.
  quoteId: Id;
}
interface CreateGenerationHeaders { "Idempotency-Key": string }
interface CreateGenerationResponse { generation: Generation }
```

Server validates ready/owned assets, settings, template, prompt provenance, and quote match/expiry, then atomically checks/reserves credits and accepts the job. Insufficient credits or expired/changed price is a pre-submission error, not a fake queued job. A stale quote requires a refreshed displayed estimate and explicit resubmission. Timeout recovery reuses the original key; never silently create a second paid job.

## GET /api/generations/:id — job status

Response 200. Poll with backoff; server provides recommended delay. Terminal states stop polling. Refetch may issue refreshed asset URLs.

```ts
interface GetGenerationRequest { id: Id } // Path parameter.
interface GetGenerationResponse {
  generation: Generation;
  pollAfterMs: number | null; // null for terminal jobs.
}
```

## GET /api/generations — recent generation history

Response 200. Newest createdAt first, with stable ID tie-breaker and opaque cursor. Proposed default limit 20, maximum 100; the UI's visible count is a separate reference decision.

```ts
interface GetGenerationsRequest { cursor?: string; limit?: number }
interface GetGenerationsResponse {
  generations: Generation[];
  nextCursor: string | null;
}
```

History list does not fabricate thumbnails or successful output. Download/open uses authorized output asset URLs and respects expiry.

## GET /api/credits — balance and estimated generation costs

Response 200. Without an estimate query, returns current available balance and quote null. With `estimate`, returns an expiring quote bound to the complete proposed submission. Serialize the EstimateInput object as URL-encoded JSON in the `estimate` query parameter; mark this response private/no-store. Sensitive prompt text is intentionally absent. Proposed pricing depends on render settings/input type, not prompt length; revisit this contract before adding any prompt-based pricing.

```ts
interface EstimateInput extends RenderSettings {
  templateId: Id;
  duration: Duration;
  aspectRatio: AspectRatio;
  inputAssets: InputAssets;
  productUrl?: string;
  promptId: Id;
}
interface GetCreditsRequest { estimate?: EstimateInput }
interface CreditQuote {
  id: Id;
  creditsEstimated: number;
  expiresAt: ISODateTime;
}
interface GetCreditsResponse {
  balance: number; // Spendable credits after reservations.
  quote: CreditQuote | null;
  updatedAt: ISODateTime;
}
```

Never invent prices or calculate authoritative costs in presentation components. Requote after input/settings changes or expiry. Final charge must not exceed the accepted estimate without renewed user agreement. Reservation, debit, refund, prompt pricing, and subscription policy require business approval before billing implementation.

## POST /api/billing/checkout — create a hosted checkout session

Response 201. Server validates an approved catalog ID; never accepts a client-provided price. Redirect URLs are generated from trusted configured origins. Pricing catalog source is pending because no plans endpoint has been requested; do not invent plans or add a pricing dashboard.

```ts
interface CreateCheckoutRequest { priceId: Id } // Public application catalog ID.
interface CreateCheckoutResponse {
  sessionId: Id;
  checkoutUrl: string;
  expiresAt: ISODateTime;
}
```

## POST /api/billing/portal — open hosted customer billing portal

Response 201. Server resolves the authenticated billing customer and configured return location. Checkout/portal pages belong to the established service, not a custom billing implementation. Browser return is not proof of payment; server-confirmed billing events update credits.

```ts
type CreateBillingPortalRequest = Record<string, never>;
interface CreateBillingPortalResponse {
  portalUrl: string;
  expiresAt: ISODateTime;
}
```

## BUILD_BRIEF implementation revision (supersedes earlier proposed choices)

Implementation is now authorized. Template IDs use underscores. GenerationStatus adds `cancelled`; no upstream request ID is exposed. Default model/voice/quality are `auto`. A cancelled generation has no output and zero charge if cancelled before remote submission. If the selected provider cannot cancel an already submitted job, return 409 CANCELLATION_UNAVAILABLE and leave the job active; never pretend cancellation succeeded.

POST /api/product/resolve JSON `{ url: string }` → 200 `{ product: { url: string; title: string; description: string; imageUrl: string | null } }`. Extracted text is untrusted content. Returned image URLs are not automatically uploaded/owned assets.

POST /api/generations/:id/cancel empty JSON → 200 `{ generation: Generation }`; terminal completed/failed jobs return 409; repeated cancellation returns same cancelled job.

POST /api/webhooks/stripe raw signed body + Stripe-Signature → 200 `{ received: true }`. Verify signature before parsing as an event; deduplicate event IDs and transactionally apply configured grants. This endpoint is service-facing, not a frontend operation.

Prompt source fingerprint uses canonical creative input. Quote source matches EstimateInput; quality `auto` means omit provider override. All requests use camelCase JSON. Error envelopes remain `{ error: { code, message, retryable, fieldErrors? }, requestId }`. GET /api/billing/summary may supply current plan/status/renewal and configured checkout choices for the simple Billing surface, without a custom billing editor.

Supabase access token is sent as Bearer authorization from the shared HTTP client. Development mock auth is explicit server configuration, forbidden in production. The frontend's mock adapter is an independent simulation; HTTP mode exercises FastAPI with the same domain shapes. Model capabilities must reflect the configured provider, not just the visual controls.
# Product context amendment — 2026-09-10

Chat Send retains the existing context shape: owned inputAssets, productUrl, templateId, brief, duration, aspectRatio. The backend supplies actual validated image attachments and public-page evidence to the local conversation provider. No provider paths or credentials reach the browser. POST /api/product/resolve returns `{ product, asset }`; asset is an owned product image when retrievable and `null` when page metadata is usable but its preview image is unavailable. The frontend keeps a user-uploaded product image in preference to this automatic asset. Apply performs no external page refetch. Page retrieval errors remain actionable API errors; no invented fallback product is returned. Category detection is model interpretation, not a new required input or API enum.
