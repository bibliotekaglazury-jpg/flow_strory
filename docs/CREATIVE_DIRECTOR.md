# Creative Director — current local 15-second pipeline

Updated 2026-09-12. The conversation provider is direct Anthropic Messages through `ClaudeCreativeDirectorAdapter`, with `creative-director-v3`. Storyflow's database owns history; Codex subscription/native history and the previous Responses experiment are retired runtime paths. Historical reports remain evidence only for their recorded versions. Deployed to VPS and re-verified against the real Anthropic API (`docs/audits/CREATIVE_DIRECTOR_EVAL_20260912.md`); no measured creative-quality improvement beyond that eval is claimed.

## Data flow

Existing uploads/public-page resolver → ContextBundle and native image blocks → bounded preparation → optional research → format/structure retrieval (`app/creative_direction_playbooks.py`) → final CreativePlan + VideoPlan and server-only audit → deterministic post-generation gates → `compile_plan` → existing VideoRecipe → `compile_recipe` → existing Prompt → quote → generation/job → existing worker → OpenRouter → existing storage/history/ledger.

There are at most four model rounds, including at most one repair. Preparation chooses up to two reviewed allowlisted skills and assesses missing context. Research, when permitted, is one bounded search or fetch round. No separate language classifier, industry form, agent backend, independent critic or second generation system is introduced. Sources and skills remain untrusted reference material.

### Format playbooks and ad-structure retrieval (`app/creative_direction_playbooks.py`)

`FORMAT_PLAYBOOKS` (one entry per `Format` literal) and `WINNING_AD_STRUCTURES` (40
seed mechanisms, 4–5 per format, tagged by `niche`) are first-party static reference
content — not vendored/hash-pinned like `creative_skills`, since they're authored, not
third-party text, but still framed to the model as "reference data, not instructions"
(`CREATIVE_DIRECTION_REFERENCE` block in `claude.py`), never as directives that
override the response schema. `select_structures()` matches on niche keywords, format
bias, excluded mechanisms and available asset roles (including page-sourced imagery that
never becomes an owned asset) — no vector search or embeddings; see "Scoring" below for
how candidates are ranked. An explicit `selectedFormat` gets its full playbook plus 6 matching
structures; `auto` gets the compact format index plus 10 cross-format structures and
resolves the format itself. Retrieved structure ids (not necessarily the one used —
`CreativeAudit`'s schema doesn't record that) go into `audit.referenceStructureIds`
alongside `audit.playbookFormat`; both are logged (`creative_director_audit`) and
persist in `ChatRecipeVersion.recipe.planning.creativeAudit` when a turn produces a
recipe, no migration involved.

Each structure's `ctaStyle` field states the felt outcome the CTA should land on, never
a pointer to specs the viewer can see elsewhere (e.g. "the description", "the page") —
this is deliberate, not incidental: an earlier version had ~half the seed CTAs modeling
exactly the generic "learn more"-class weak-CTA register that `hook-method.md` (an
already-vendored, already-reviewed skill) explicitly names, and since this reference is
injected on every turn, it was measurably steering dialogue toward spec-recitation
instead of outcome/benefit language (`CREATIVE_DIRECTOR_EVAL_20260912.md`, "Root cause
2"). There is deliberately no regex gate for this — the distinction between a
referral-with-no-substance line and a referral-after-stating-the-outcome line is
semantic, not lexical, and a hard gate risked false-positiving on legitimate CTAs.

### Offer understanding before mechanism selection (Phase 1.5)

Format no longer decides strategy. Before retrieval, three things are established:

- **`consumptionModels`** — how the buyer actually receives the value (`narrative_immersion`,
  `physical_use`, `gifting`, `recurring_discovery`, …; closed vocabulary in
  `CONSUMPTION_MODELS`). Determined by the Preparation call: one primary, plus a second
  only for a genuine hybrid (an illustrated collector's edition is read *and* displayed).
  Unknown values are dropped in code, not trusted.
- **`categoryOverlay`** — the single best keyword-matched niche's `requiredPayoff` plus
  2-4 `forbiddenReductions` (`CATEGORY_OVERLAYS`). Only the matched category is ever
  injected — never the catalogue — so the director's instruction load stays flat as
  categories are added. This is the load-bearing constraint of the design: measured
  cost of Phase 1.5 was +3 constraint sentences and +255 prompt tokens, against 28
  overlay rules that exist but stay unsent.
- **`evidenceAvailable`** — computed deterministically in code before any model call
  (`evidence_available()`): product/person imagery including page-sourced photos,
  an uploaded source video, source facts, page state, written brief. A mechanism that
  can't be shot with that material is the wrong mechanism.

### Uploaded video: the director sees frames, not the file

The Messages API has no video content block — `ContentBlockParam` is text, image,
document and tool results only — so a director cannot watch an uploaded clip directly.
Until 2026-09-12 `enrich()` skipped every non-image reference outright, so a source
video reached generation as a real reference (`reference_video_urls` in
`services/generations.py`) while the director only ever saw its metadata row: it knew a
video existed and how long it ran, never what was in it.

`video_frames()` now samples `VIDEO_FRAMES` (3) evenly spaced stills via ffmpeg — already
installed in the runtime image and already used by `video_validation.py` — at
`(i+1)/(count+1)` of the duration, which skips the black frames and title cards that sit
at the very start and end. Duration comes from ffprobe, falling back to parsing ffmpeg's
own stderr, because ffprobe is not guaranteed to sit beside ffmpeg outside the container.
Frames go through the same `image_attachment()` path as any still (downscaled to
`VISION_MAX_EDGE`) and carry the role `source video frame`, which `v3.py` explains to the
director as samples — not proof of motion, audio, or anything happening between them.

Extraction never fails a turn: a missing, unreadable or corrupt file yields no frames and
the director plans without having seen the clip, exactly as before. Ordering is
deliberate — uploaded stills, then sampled frames, then page imagery — because the
provider call caps attachments at three, so the most informative material survives the
cap. Cost is roughly 0.28¢ per frame per call (~1400 vision tokens at 1024px), so about
1.7¢ per turn for three frames across the preparation and director calls.

Retrieval count adapts: 6 cards for a precise single-model, single-niche match; 10 for
a hybrid or ambiguous offer (`retrieval_limit()`).

**Scoring (fixed 2026-09-12 for tie collapse).** Naive "count how many of my niche tags
matched" gave almost no resolution: `ecommerce_physical` sits on 22 of 45 cards and 40 of
45 cards carry exactly 4 tags, so any brief containing "produkt" scored 22 cards
identically and the offered set was decided purely by position in the list — measured, and
the same failure shape that once pushed all five core `demo_*` cards out of the top 6.
`_fit_score()` now combines three deterministic signals, still with no embeddings or
vector search:

- **Tag rarity** (`_niche_weights()`, log-scaled inverse frequency over the library): a
  `narrative_media` match (5 cards) outweighs an `ecommerce_physical` match (22 cards).
- **Keyword frequency**: distinct matched keywords per niche, capped, instead of a single
  boolean per niche.
- **Specificity**: the share of a card's own tags that matched, so a one-tag specialist
  beats a four-tag generalist that matched one tag.

Ties that remain are broken by `_tiebreak()` — a hash of structure id plus the offer text
— not by authoring order. The same brief is still perfectly reproducible (tests depend on
it), but different offers reach different cards, so no card is permanently unreachable
because of where it was written. Measured effect on a typical product brief: cards tied
at the top score dropped from 22 to 1. A brief with no matching keywords at all still
ties everything (no signal exists to invent), but the offered set then varies by offer
instead of always returning the earliest-authored cards.

For `auto`, `_diversified()` keeps the strongest matches and fills the rest across format
families not yet represented, so one family cannot monopolise the set — this also
addresses the observation that all four narrative eval cases had picked `hook_cta`. With
an explicit format the set is one family by definition and the format bonus stays
decisive.

Niche keyword matching is word-start anchored (`_keyword_hit`), which keeps Polish
inflection tolerance while preventing short tokens from matching inside unrelated words
— `gra` must not fire inside `program`, `fotografia` or `integracja`.

The structures are supports, not a closed menu: the three candidates are the best-fitting
library mechanism, one from a different family, and a hybrid or original concept where
that serves `consumptionModels` better. An original mechanism is allowed and frequently
chosen — in the 2026-09-12 narrative eval the director selected its own hybrid over a
library card in 3 of 4 cases — but it must serve `requiredPayoff`, stay inside
`evidenceAvailable`, and invent no facts.

Why this exists: a live case ("promote this book in a new colourful edition") produced a
technically well-crafted ad whose entire payoff was admiring the illustration — it sold
the artefact, not the reading. Nothing in the format library or prompt required the
payoff to match how the offer is actually consumed. The full layered pyramid (buyer role,
campaign objective, evidence model as separate decision layers) remains deferred: of 15
live cases only one failed on offer understanding, so the minimal version ships first and
the eval decides whether the rest is warranted.

### Deterministic post-generation gates (`app/creative_audit.py`)

Four gates run after `parse_director_envelope`, before a turn is accepted; none
soft-accept on final failure (unlike the quality-score gate below) — they exhaust to a
hard error through the same repair loop:

- `validate_quality` — the existing 0–5 self-score gate (see "Creative behavior" below).
- `validate_requested_ratio` — the plan's `aspectRatio` must equal the one supplied in
  the ContextBundle, because the user picked that frame in the UI. `selectedFormat` has
  been enforced in `compile_plan` since the start; `aspectRatio` reached the director as
  evidence only, so nothing stopped a plan from coming back in a frame nobody chose. The
  check lives in the provider (not only in `compile_plan`) deliberately: `compile_plan`
  runs at `services/chat.py:215`, outside the repair loop, where a `ValueError` becomes a
  generic `CHAT_FAILED` and the turn is simply lost. In the gate, the director gets one
  repair round and recomposes the shot for the requested frame instead. `compile_plan`
  keeps the same assertion as a last-resort guard for non-provider paths.
- `validate_requested_language` — the plan's `spokenLanguage` must start with
  `contextBundle.requestedLanguage` when the user set one, raising
  `CREATIVE_LANGUAGE_MISMATCH`. Exists because the director otherwise infers language
  purely from brief text — which fails for Auto mode's filler message ("Plan this video
  from the selected style...", always English) regardless of what language the user
  actually wants. `Creative.language` already existed in `schemas.py` but was dead: only
  ever written from a completed recipe, never read as an input. The frontend now exposes
  it as an explicit per-video language picker next to Duration/Aspect Ratio — not a
  site-wide UI language switcher, since building real site i18n was a separate,
  much larger, unrequested task.
- `validate_preferred_mechanism` — when `contextBundle.preferredMechanism` is set,
  `creativePlan.creativeMechanism` must equal that exact slug, raising
  `CREATIVE_MECHANISM_MISMATCH`. This is the Recreate path: a user picks a finished video
  from their own history and reuses the structure that already worked on a completely
  different offer. Only the mechanism carries over — the frontend clears `inputAssets`,
  URL and brief so the user supplies their own material, and the v3.py rule requires every
  fact, spoken line and CTA to be derived from the new request's own evidence. It is the
  mirror image of `excludedMechanisms` (which forbids repeats) and reuses the same
  bounded-repair shape as the ratio/language gates. `GenerationView.creativeMechanism`
  exposes the slug from `snapshot["creativePlanning"]["creativePlan"]`, which is why no
  migration was needed; a generation planned before this field existed simply has no
  Recreate button.
- `validate_offer_role` — regex-based: a buyer/B2B-evaluating audience (`zakup`,
  `kupić`, `własny sprzęt`, `purchas...`, `buying`, ...) paired with a clinic-booking
  CTA (`recepcj...`, `umów... wizyt...`, `book an appointment`, `schedule an exam`, ...)
  raises `CREATIVE_OFFER_ROLE_MISMATCH`. Exists because a device/B2B offer presented by
  a person-image reference (e.g. a doctor demoing a portable ultrasound machine) can
  satisfy every structured role field correctly while the *spoken CTA* still invites
  patients to book at that person's practice — the person/product role rule constrains
  who the subject is, not what the line asks the viewer to do; this gate constrains
  the latter. Requires both signals present; verified against real captured pre-fix
  text plus negative controls from legitimate purchase-CTA and legitimate
  appointment-CTA cases.
- `validate_spoken_register` — regex-based: flags documented AI-tell filler phrasing in
  `spokenScript` (English AI-vocabulary tier-1 words and phrases, Polish "warto
  zauważyć/wspomnieć/podkreślić/to sprawdzić..." hedge-openers), raising
  `CREATIVE_DIALOGUE_AI_TELL`. Pattern source is real, MIT-licensed public tooling
  (`Aboudjem/humanizer-skill`'s vocabulary list), not an invented category — see
  `CREATIVE_DIRECTOR_EVAL_20260912.md` for the citation and the specific line that
  prompted it.

`ValidationError`s caught in the repair loop log field path (`loc`) and error `type`
only (`creative_director_validation_error`) — never the raw value, message, or model
text.

## Contracts

`app/creative_direction.py` owns provider-neutral planning contracts. Public generated schemas are `packages/contracts/{creative-director,context-bundle,chat-answer}.schema.json`; TypeScript uses `packages/contracts/chat.ts`. `scripts/chat/export-schema.py` regenerates these public schemas. Internal audit types live in `app/creative_audit.py` and are not added to browser responses.

- ContextBundle includes user text, brief, source evidence, owned asset metadata, selected format, ratio, bounded visible history and `priorConcepts`. Images travel separately; JSON does not persist binary attachments. Unresolved generic offer/audience/benefit fields can remain empty.
- CreativePlan records objective, audience, offer, tension, angle, selected format, hook strategy, visual mode, language, characters, product/audio direction and confidence. `creativeMechanism` is optional for old saved plans but required on ready Claude output.
- VideoPlan is exactly one 15-second clip with spokenScript, visualDirection, camera, performance and native audio separated. Zero to five ordered non-overlapping beats can describe the action without a fixed timing template. `duration` is `Literal[15]` in the schema and `compile_plan` writes 15 unconditionally; the creative path never reads a requested duration, and `ContextBundle` has no duration field at all. The UI's duration control is therefore not a director input — it is filtered from the real provider capability (`registry.py` declares `durations=(15,)`), which is why only 15s is offered for generated video; the 20s/30s options only appear for client-rendered remotion templates, which do not go through the director.
- `aspectRatio` is the one frame setting the director does receive and must honour; see the ratio gate above.
- DirectorAnswer is either `enough_to_plan` with both plans or `clarification_needed` with one question and no applicable plan. Unknown fields and inconsistent languages/timing/audio are rejected.
- The server-only DirectorEnvelope adds three compact candidate records and one selected candidate. Candidate mechanisms/IDs must be distinct and the selected mechanism must match the plan. No private reasoning is accepted.
- PlannedAnswer extends the existing public RecipeAnswer with optional plans. CanonicalVideoRecipe remains the existing VideoRecipe; historical stored answers are backward compatible.

## Creative behavior and its limits

Auto resolves to one of the eight existing business formats. Manually selected formats must survive compilation. `FORMAT_BIASES` describes presentation intent without tying a template to a model. The director should preserve requested spoken language, distinguish sourced facts from proposals and avoid fabricated specifications, medical results, discounts or customer experiences.

Three candidate mechanisms receive eight 0–5 self-scores. The selected candidate must score at least 3 in each dimension and average at least 3.5. This is a deterministic gate on model self-assessment, not an independent quality measurement. Offline tests do not establish that the concept is compelling, semantically different, factually correct or better than the previous transport. The separately bounded real evaluation matrix remains pending.

An explicit `change_concept` intent excludes prior accepted mechanism slugs from the same creative-context fingerprint. Normal refinements may keep the mechanism. Exact slug checks cannot detect every semantic paraphrase. Old records without slugs and rejected candidate history are not treated as proven exclusions. At most one repair may address schema/quality/repetition failures; every request counts toward token, time, round and monetary budgets. Failed turns preserve the previous valid answer.

## UI and Apply

The approved dark shell, white workspace, hero, imagery and lime controls remain. The existing summary exposes Concept, Hook, Story, Script and Look; no candidate scores, tools, model names or raw planning keys are displayed. Use this concept applies the existing prompt/settings flow. Change concept prefills the existing composer and carries explicit intent through retries. Generated result/status remains below chat.

A text-only service offer can be planned without a mandatory category or photograph. Existing product/person/video ownership rules remain. Apply checks the accepted revision and references, sets prompt/format/ratio/language, and performs no provider call or video-credit reservation. Generate Video remains the only submission action.

### Auto mode (`hooks/use-creation.ts` `autoPlan()`)

The chat-mode toggle's second option, renamed from Manual to Auto 2026-09-12: it runs
the same Creative Director as the chat, just without a visible conversation. The
backend requires a non-empty message (`SendMessage.text`, `min_length=1`), so `autoPlan`
sends one fixed filler sentence ("Plan this video from the selected style and the
supplied materials.") and relies entirely on the template, uploaded assets and product
URL for real signal — deliberately not routed through the separate, unrelated
`/api/prompts/generate` deterministic-template endpoint, which has no Creative Director,
no gates, and produces the generic ad copy this whole effort was built to avoid.
Requires real material before it will run (`hasMaterial` in `workspace.tsx`) so the turn
is never spent on a clarification question. Planning happens on the first Generate click
(button reads "Plan and estimate"), not on switching the tab, since planning spends
money.

Live-verified 2026-09-12 end to end through a real generation (a glasses product,
`productImageId` supplied): the director correctly read the product image, and the
deterministic product-fidelity rule (see below) held — the generated video matched the
reference photo's actual branding rather than the enlarged logo seen in an earlier,
unfixed run.

## Persistence and cost

Accepted recipe versions retain ContextBundle, plans, context fingerprint, `planning.creativeAudit` and `planning.usage`; public sessions omit audit/usage. The existing Prompt and generation snapshots preserve accepted planning evidence. Manual prompt edits remain the final submitted text without fabricating a new director plan.

`chat_sessions.planning_usage`, added by migration `0005_chat_planning_usage`, stores estimated spend and outstanding reservations. Each model request reserves before inference and reconciles reported usage after it; unknown in-flight cost remains reserved across failures/restarts. This is separate from the video credit ledger. Session reset deletes session budget state and is not an account-wide cap. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md) for exact boundaries.

The Director system prompt (static instructions plus the canonical inner schemas — the
same ~2000-token block on every Director call and repair) carries `cache_control:
ephemeral`; verified live that a repeat call reads it from cache at 10% of input-token
cost instead of paying full price again. The Preparation system prompt is not marked —
at ~450 tokens it's below the minimum cacheable size. Images sent for vision analysis
are downscaled to 1024px (`VISION_MAX_EDGE` in `chat_context.py`), separately from the
stored original upload, which is untouched and remains the actual generation input.

## Video and verification

The existing real route is unchanged: OpenRouter `bytedance/seedance-2.0-mini`, 15 seconds, 480p, 9:16 / 1:1 / 16:9, native audio. No TTS, audio stitching, new provider, fallback or premium route is added. Reference generation still needs reachable HTTPS assets through the established storage/provider boundary.

Mocked frontend evidence: [verification/claude-chat/README.md](verification/claude-chat/README.md). Startup and settings: [LOCAL_CHAT.md](LOCAL_CHAT.md). The earlier [CREATIVE_DIRECTOR_VERIFICATION.md](CREATIVE_DIRECTOR_VERIFICATION.md) and paid video test reports are historical; their provider, account balance, tunnel and worker observations are not current operational guarantees.

A real (paid, planning-only, no video generation) Claude matrix was run 2026-09-12 —
24 live calls, $2.55 total, 15 distinct offer/niche cases — via
`scripts/chat/eval-creative-director.py`, which calls `ClaudeCreativeDirectorAdapter`
directly, bypassing the DB/session/HTTP layers. Full results, every fix it drove, and
the exact before/after dialogue: [CREATIVE_DIRECTOR_EVAL_20260912.md](audits/CREATIVE_DIRECTOR_EVAL_20260912.md).

A real, fully fantastical-CGI shot plan (the narrative_media Alice/Wonderland case, subject placed inside a surreal pink-gold environment for the whole 15s, no realistic anchoring frame) was actually generated through the real product flow and user-verified as excellent. This resolves, for at least this case, the open question of whether `bytedance/seedance-2.0-mini` can credibly render a subject inside an entirely stylized/fantastical world rather than only grounded authentic-UGC settings — it can. Not yet established: whether this holds broadly across fantastical concepts, or only for well-composed source imagery like this one.
