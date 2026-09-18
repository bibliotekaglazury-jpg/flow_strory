# Storyflow UGC Creative System Audit — competitor-backed playbooks

Generated: 2026-09-11

Status: strategic/product audit. No paid generation was run for this document.

## Executive decision

Storyflow should not compete as “another video model UI”. The strongest market pattern is a product-ad workflow:

```text
product URL / product image / person reference
→ offer understanding
→ multiple creative mechanisms
→ selected concept
→ script + visual plan
→ video model generation
→ captions/headlines/CTA overlay
→ variants/history/export
```

The video model is an execution layer. The product value is the Creative Director, its format playbooks, source-grounded offer understanding, and repeatable generation of strong variants.

## Source-backed competitor table

| Competitor | What they sell as the user promise | Input pattern | Planning/editing pattern | Variant pattern | What matters for Storyflow |
|---|---|---|---|---|---|
| Predis | Product link/image to ready-to-post product videos and ads | Product link, image, Shopify/WooCommerce/Etsy/Wix/store connection | Pulls images, price and description; writes script; adds voiceover, music and captions; opens draft in editor | Several versions/A-B testing; platform resizing; brand kit | Our first major boost is not another model. It is URL/image → script/scenes/captions → editable concept before paid render. Source: https://predis.ai/product-video-maker/ and https://predis.ai/ai-video-generator/ |
| Topview | AI advertising platform built around winning ad structures | Product URL/image, landing page URL, uploaded/reference/winning ad | Analyzes hooks, storytelling patterns, visual triggers and CTA placements; offers templates by platform | Dozens of variants with different hooks, UGC talking heads and lifestyle scenes | We need a mechanism library and Change Concept must change the mechanism, not wording. 3-second hook logic is mandatory. Source: https://www.topview.ai/use-cases/advertising |
| Arcads | AI-powered content/ad creation with actors, products, B-roll, tools and workflows | Product image, actor, script, generated image, existing video | Product detection, product placement in video, talking actors, captions, overlays, translate, B-roll, actor replacement | Workflows can turn one winning ad into many UGC variations with different actors/scripts/languages | We need to separate actor/person reference from promoted product. The person is presenter, not necessarily the offer. Source: https://intercom.help/arcads/en/articles/15503340-everything-you-can-do-on-arcads-complete-platform-guide and https://intercom.help/arcads/en/articles/14531683-getting-started-with-arcads |
| Creatify | URL-to-video and avatar UGC ads at scale | Product link, product image, text/audio/URL, avatar | Pulls product details, generates scripts, avatars, B-roll, music, captions, editor | 5–10 ready-to-run video ads from one product link | Our Creative Director should return several candidate mechanisms internally now, and later user-visible variants. Source: https://creatify.ai/features/ai-influencer-generator and https://creatify.ai/api |

## Most important working insights

| Priority | Insight | Why it gives us a boost | How to implement without breaking the system |
|---:|---|---|---|
| 1 | Formats must be playbooks, not labels | Current labels are too weak; Claude falls back to generic product show-and-tell | Add server-side `FORMAT_PLAYBOOKS` consumed by Claude. Keep existing schemas, add only more guidance in context/system prompt. |
| 2 | Product reference and person reference must be separated | The USG test proved Claude can confuse doctor/person reference with the thing being sold | Add explicit rule: product URL/image defines promoted offer; person image defines presenter/actor unless user states otherwise. Add tests. |
| 3 | Change Concept must change the creative mechanism | Competitors sell variants; variants mean different hooks/stories, not synonyms | Persist selected/rejected mechanism slugs. On Change Concept, exclude prior mechanisms and require new central action/payoff. Current code partially does this; playbooks should provide enough mechanisms. |
| 4 | URL/image context must be converted into offer facts before planning | Generic concepts happen when the offer is not grounded | Keep URL fetch/evidence path, but summarize to compact `OfferFacts`: name, audience, use case, benefits, proof, restrictions, visual identity. |
| 5 | The first 3 seconds need their own planning field | Topview’s “3-second hook” pattern is market-standard for performance video | Add `openingHook` or enforce hook-specific fields inside CreativePlan/VideoPlan. No provider change required. |
| 6 | Captions/headlines/CTA should be deterministic overlay later | AI video models are unreliable for exact Polish text | Keep now as future layer: Wan outputs clean video/audio; OverlayRenderer later burns exact text/CTA/captions. |
| 7 | Variants are a product feature | Predis/Creatify/Topview all push multiple outputs | First stage: internal 3 candidates. Second stage: expose “Generate 3 concepts”. Third stage: batch render only after costs are known. |
| 8 | Market needs “ready to sell”, not cinematic art | Small businesses want ads that can be posted | UI should show Concept, Hook, Story, Script, Look, CTA, then Generate. Keep simple. |

## Current Storyflow runtime facts captured from VPS

| Area | Current value / observation |
|---|---|
| Runtime path | `/opt/storyflow/app` on VPS |
| Git status on VPS | `NO_GIT`; operational risk: runtime is not a verified git worktree |
| Public domain | `https://ugc.cerebroos.io` |
| Chat provider | `claude` |
| Claude model | `claude-sonnet-5` |
| Video provider | `openrouter` |
| Active video model | `alibaba/wan-3.0` |
| Duration | 15 seconds only |
| Aspect ratios | 9:16, 1:1, 16:9 |
| Native audio | enabled in provider payload |
| Storyflow internal video price | `VIDEO_CREDITS_PER_SECOND=3`, so one 15s generation estimates 45 internal credits |
| Completed real generations observed | 2 completed generations, each estimated/charged 45 internal credits |
| Failed reference generations | refunded internally: charged 0 |
| Known production gap | `APP_ENV=development` on public VPS; needs production hardening before sales |
| Storage/reference issue resolved | domain and signed media route now return `video/mp4` with filename `generated-video.mp4` |

## Problems we hit and what was learned

| Problem | What happened | Resolution / lesson |
|---|---|---|
| Product URL was weak or ignored | Claude sometimes relied on image/person more than URL context | Need offer facts and hard product/person separation. |
| Person image hijacked the offer | Doctor image made Claude sell doctor service instead of USG product | Add rule: person reference is presenter only unless user explicitly says sell the person/service. |
| Seedance Polish quality | Generated output had pronunciation/language quality issues for Polish | Reverted active runtime to Wan. Keep Seedance out of current path. |
| Reference images rejected by video service | OpenRouter rejected non-reachable/invalid references | Created public HTTPS subdomain/path and fixed media route. Need robust preflight for references before paid generation. |
| Download from history tried `.json` | Browser downloaded unavailable JSON-looking file | Media route now returns MP4 content type and `generated-video.mp4` filename. |
| Cost confusion | User expected less than external balance impact | Internal Storyflow ledger is not OpenRouter real billing. Need display both estimated internal credits and external provider job id/cost if API provides it. |
| VPS source-of-truth risk | VPS folder is not git | Before serious sales/deploy, establish git-backed deploy or immutable release archive. |

## Format playbooks

These are not fixed scripts. They are creative operating instructions for Claude. Each format should carry:

- format objective
- viewer psychology
- allowed mechanisms
- forbidden generic fallback
- product/person/source rules
- opening hook grammar
- visual grammar
- script grammar
- CTA grammar
- quality checks

### Universal director rules for all formats

1. Product URL/product image defines the promoted offer.
2. Person image defines presenter/actor/reference identity, not the sold offer unless user says so.
3. If user says “promote this product”, do not reinterpret it as promoting the pictured person’s service.
4. Produce one 15-second concept, normally one clip with internal beats.
5. Generate at least three mechanisms internally; select the strongest.
6. On Change Concept, switch mechanism and central payoff.
7. Avoid fake proof: no fake customer result, certification, price, clinical outcome, guarantee or ROI.
8. Creativity should happen in situation, hook, framing, contrast, visual action and CTA.
9. Dialogue must be short, speakable and language-stable.
10. If the product is technical or medical-adjacent, focus on design, use case, workflow, convenience, availability and business inquiry; avoid treatment/result claims.

## UGC Review playbook

| Field | Instruction |
|---|---|
| Goal | Make the product feel noticed by a believable person, without sounding like a scripted TV ad. |
| Core psychology | “Someone like me is looking at this and making sense of why it matters.” |
| Best for | ecommerce, beauty, gadgets, home products, professional devices, apps, simple services |
| Avoid | Fake long-term personal experience, fake clinical/customer result, over-polished corporate tone |
| Script style | First-person but careful: “pierwsze co zauważyłem…”, “to może się sprawdzić gdy…”, “warto sprawdzić…” |

Mechanisms Claude can choose:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | First impression | Presenter sees product, names the visual detail that makes it worth attention. |
| 2 | “I didn’t expect this” | Hook begins from one surprising feature, size, design or use case. |
| 3 | Detail inspection | Product close-up drives the story: button, handle, texture, screen, packaging, cable, ingredient. |
| 4 | Everyday problem noticed | Presenter shows a common annoyance and product becomes the practical answer. |
| 5 | Buyer question | Start with “jeśli szukasz X…” and answer with one focused reason. |
| 6 | Comparison without competitor | “Zamiast kolejnej rzeczy, która tylko wygląda dobrze…” then show tangible difference. |
| 7 | Gift/use-case review | Present product as useful for a specific situation/person. |
| 8 | Skeptical review | Presenter starts cautious and is won by one visible detail. |
| 9 | Mini checklist | Three quick things noticed, one CTA. |
| 10 | “Would I click?” | Creator frames it as what made them stop and check the offer. |

## Product Unboxing playbook

| Field | Instruction |
|---|---|
| Goal | Build anticipation and reveal value through discovery. |
| Core psychology | “What is inside / what changes when I open it?” |
| Best for | physical products, packaging, kits, gadgets, cosmetics, apparel, accessories |
| Avoid | Inventing a box when none exists. If no package, use “first look” or “desk reveal”. |
| Script style | Short discovery language: “zobaczmy”, “pierwsze wrażenie”, “od razu widać…” |

Mechanisms:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | Classic reveal | Closed box/product off-frame → reveal → one key detail → CTA. |
| 2 | Desk reveal | Product slides into frame on clean desk; presenter reacts to first impression. |
| 3 | Mystery object | Start with partial close-up, reveal full product after 2–3 seconds. |
| 4 | First-use setup | Show product being prepared or opened, without claiming results. |
| 5 | What’s included | Show product + included visible parts, no invented accessories. |
| 6 | Texture/material reveal | Camera focuses on finish/material/packaging quality. |
| 7 | Size surprise | Reveal scale in hand/on table. |
| 8 | Giftable reveal | Position as unpacking for buyer/gift moment. |
| 9 | Professional kit reveal | For B2B/pro devices: reveal as business equipment, not consumer toy. |
| 10 | “Before I even use it” | Explain what can be judged immediately: build, layout, portability, clarity. |

## Problem → Solution playbook

| Field | Instruction |
|---|---|
| Goal | Make the viewer feel a real friction before the product appears. |
| Core psychology | “That problem is mine; this offer may solve it.” |
| Best for | services, courses, B2B, health/wellness devices, home tools, SaaS, local businesses |
| Avoid | Fake outcomes; overclaiming transformation. |
| Script style | Problem in plain language, product as one possible practical next step. |

Mechanisms:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | Daily friction | Show the annoying moment, then introduce the offer. |
| 2 | Lost time | Start with “ile razy…” or visible delay/confusion. |
| 3 | Missed opportunity | For B2B: show empty slot, unused room, missed inquiry. |
| 4 | Too complicated | Show complexity; product simplifies one step. |
| 5 | Old way/new way | Contrast a clumsy old approach with product-supported approach. |
| 6 | Customer request | A message/question appears conceptually; product answers demand. |
| 7 | Small business bottleneck | Owner lacks capacity/offer/clarity; product expands options. |
| 8 | Decision anxiety | Viewer doesn’t know what to choose; product becomes clear option. |
| 9 | Space/portability problem | Product solves location/space friction. |
| 10 | Professional readiness | Product helps look/operate more prepared without promising results. |

## Product Demo playbook

| Field | Instruction |
|---|---|
| Goal | Show the product working or being used, not only named. |
| Core psychology | “I understand how this fits into use.” |
| Best for | gadgets, tools, devices, SaaS, cosmetics, apps, equipment |
| Avoid | Talking too much; technical catalogue dump; fake interface/specs. |
| Script style | One visible action per sentence. |

Mechanisms:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | One action demo | Product is picked up/opened/placed/activated visually. |
| 2 | Three-step demo | Setup → key interaction → CTA. |
| 3 | Detail tour | Camera moves through 2–3 visible details. |
| 4 | Use environment | Product shown in realistic place where buyer would use it. |
| 5 | Feature-to-benefit | Each visible feature maps to practical use, not abstract claim. |
| 6 | Hands-only demo | No face needed; hands demonstrate product cleanly. |
| 7 | Presenter + product | Presenter explains while interacting, not just holding. |
| 8 | Mobile/portable demo | Show moving/carrying/setup when portability matters. |
| 9 | Professional workflow | B2B product placed into a working routine. |
| 10 | “Show, then say” | First 2 seconds visual action, then spoken explanation. |

## Testimonial playbook

| Field | Instruction |
|---|---|
| Goal | Create credible personal/social proof only when factual support exists. |
| Core psychology | “Someone credible had this concern and found this useful.” |
| Best for | reviews, supplied testimonials, founder/customer quotes, case studies |
| Avoid | Invented experience, fake before/after, fake numbers, fake clinical/business outcomes. |
| Script style | If no source testimonial: use “creator perspective” not “customer result”. |

Mechanisms:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | Real quote expansion | Turn supplied review into short scene. |
| 2 | Founder/customer POV | Only if user supplies that identity. |
| 3 | Objection answered | Start with common doubt, answer with source-backed fact. |
| 4 | “Why I checked it” | Personal curiosity without claiming usage results. |
| 5 | Social proof from page | Use visible/source-backed review count/logos only if present. |
| 6 | Professional recommendation style | Expert/presenter explains why the offer is worth checking, without false testimonial. |
| 7 | Mini story | Problem → considered options → CTA, only factual. |
| 8 | Category credibility | Position product as fitting a known category need. |
| 9 | User-type testimonial | “Dla osób, które…” rather than “I achieved…”. |
| 10 | Skeptic-to-interest | Believable shift from doubt to wanting more info. |

## Trending Style playbook

| Field | Instruction |
|---|---|
| Goal | Feel native to TikTok/Reels/Shorts without copying a specific copyrighted trend. |
| Core psychology | “This feels like social content, not an ad.” |
| Best for | broad consumer products, beauty, gadgets, fashion, lifestyle, quick B2C offers |
| Avoid | Random effects, chaotic cuts, trend references that don’t fit buyer. |
| Script style | Short phrases, pattern interrupt, punchy rhythm. |

Mechanisms:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | Pattern interrupt | Unexpected first visual or phrase. |
| 2 | POV setup | “POV: szukasz…” situation. |
| 3 | Micro-story | 3 quick beats: problem, product, payoff. |
| 4 | Quick cuts | Several fast but coherent product angles. |
| 5 | Myth/realization | “Myślałem, że…, ale…” without overclaim. |
| 6 | Listicle | “3 rzeczy, które zauważysz…” |
| 7 | Reaction | Presenter reacts to product detail/use case. |
| 8 | Challenge-style | Small task/product challenge, feasible in 15s. |
| 9 | Creator confession | “Nie kupiłbym kolejnej rzeczy, gdyby…” |
| 10 | Comment reply | Simulate answering a buyer question, not fake comment proof. |

## Hook → CTA playbook

| Field | Instruction |
|---|---|
| Goal | Build the whole 15s around one strong opening and one clear action. |
| Core psychology | “Stop, understand, act.” |
| Best for | lead gen, offers, product launches, services, B2B, landing page traffic |
| Avoid | Multiple CTAs; vague hook; long explanation. |
| Script style | Hook in first sentence; CTA final sentence. |

Mechanisms:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | Direct question | “Szukasz…?” opens immediately. |
| 2 | Contrarian line | “Nie potrzebujesz X, jeśli masz Y…” |
| 3 | Specific audience callout | “Dla właścicieli gabinetów…” |
| 4 | Opportunity hook | “Jedno urządzenie może poszerzyć ofertę…” without ROI claim. |
| 5 | Curiosity gap | Show product detail before naming. |
| 6 | Problem punch | Name pain in first 2 seconds. |
| 7 | Visual hook | Start with striking close-up/product movement. |
| 8 | Deadline/event | Only if user/source supplies real date. |
| 9 | Comparison hook | Old way vs new option, no competitor names needed. |
| 10 | Offer clarity | Start with exactly what it is and who it is for. |

## Before / After playbook

| Field | Instruction |
|---|---|
| Goal | Show a contrast without fabricating impossible outcomes. |
| Core psychology | “I can see the difference in situation/state.” |
| Best for | organization, setup, workflow, cleaning, beauty packaging, business offer clarity, SaaS UI, courses |
| Avoid | Fake health/medical/body/business results unless source-backed and compliant. |
| Script style | “Przed: … Po: …” but grounded in scene, not guaranteed result. |

Mechanisms:

| # | Mechanism | How it should work |
|---:|---|---|
| 1 | Messy → organized | Product creates a cleaner scene/setup. |
| 2 | Confused → clear | Product/service explains next step. |
| 3 | Static → in motion | Product photo becomes active use. |
| 4 | Empty → equipped | Business/professional space now has equipment. |
| 5 | Ordinary → premium | Visual presentation upgrade, not factual claim. |
| 6 | Long process → shorter-feeling process | Show simplification without time guarantee. |
| 7 | Hidden detail → visible detail | Before viewer doesn’t notice; after close-up reveals key detail. |
| 8 | No plan → clear CTA | Service/course: viewer gets next action. |
| 9 | Shelf → lifestyle | Product moves from plain product shot into use environment. |
| 10 | Doubt → interest | Presenter’s reaction changes after inspection. |

## Product-specific rules that would have prevented the USG/doctor mistake

| Situation | Rule |
|---|---|
| Product image is a device, person image is doctor | Promote the device unless user says “promote this doctor/service”. Doctor is presenter/reference. |
| User says “wypromuj ten produkt” | `offer.type=product`; do not convert to service. |
| URL is ecommerce product page | Product page facts outrank person image guesses. |
| YouTube URL is provided | If not fetched/transcribed, say it is not used. Do not infer content from URL. |
| Medical/professional equipment | Discuss business fit, portability, visual design, inquiry CTA. Avoid patient outcome claims. |

## Recommended implementation architecture

### Keep the current system; do not rebuild

Existing useful chain:

```text
Create UI
→ chat session
→ chat_context.enrich()
→ ContextBundle
→ ClaudeCreativeDirectorAdapter
→ CreativePlan + VideoPlan + CreativeAudit
→ compile_plan()
→ compile_recipe()
→ OpenRouterVideoProvider
→ Wan
→ storage/history
```

### Add only these layers

| Layer | Change | Risk |
|---|---|---|
| Format playbooks | Add server-side `creative_direction_format_playbooks.py` or extend prompt context with playbook for selected format | Low; prompt/context only |
| Offer facts | Compact URL/image/product interpretation into `OfferFacts` before Claude final answer | Medium; must keep bounded tokens |
| Product/person separation | Add explicit schema flags: `promotedOfferSource`, `personRole` | Low/medium; schema/tests |
| Hook field | Add `openingHook` to CreativePlan or infer from hookStrategy + first beat | Low |
| Variant memory | Store rejected/selected mechanism details | Already partly implemented; strengthen tests |
| Overlay later | Add deterministic captions/headlines after video generation | Later; separate pipeline |
| Provider preflight | Before paid generation, validate HTTPS media URLs from provider viewpoint | Medium; prevents wasted requests |

### Do not do now

- Do not add 30/45/60 seconds.
- Do not add a second provider until Wan path is stable.
- Do not generate separate audio/TTS now.
- Do not build timeline editor now.
- Do not expose internal JSON to user.
- Do not turn format buttons into fixed scripts.

## Minimal next implementation plan

| Step | Task | Done when |
|---:|---|---|
| 1 | Add `FORMAT_PLAYBOOKS` backend data with all eight playbooks | Claude receives selected playbook in final call |
| 2 | Add hard product/person rules to system prompt | USG doctor case produces product ad, not service ad |
| 3 | Add tests for each format | Each format returns a materially distinct mechanism |
| 4 | Add “Change concept” regression tests | Second concept cannot reuse same mechanism |
| 5 | Add URL/product image offer source tests | Product URL/image outranks person image role |
| 6 | Add compact debug view in audit only | Developers can inspect ContextBundle, selected playbook, candidates |
| 7 | Add reference URL preflight | Bad refs fail before paid provider submission |
| 8 | Later add overlay renderer | Exact Polish captions/CTA after video generation |

## Acceptance tests to add

| Test | Expected result |
|---|---|
| Product URL + doctor image + “promote this product” | Device/product is the offer; doctor is presenter |
| Product image only + UGC Review | First-person inspection, no fake ownership/results |
| Product image only + Unboxing | If no packaging, uses first-look reveal, not fake box |
| B2B device + Hook→CTA | Starts with business owner/audience callout, ends with inquiry CTA |
| Service/course + Problem→Solution | No product packaging assumptions |
| Testimonial without testimonial source | Uses creator impression, not fake customer story |
| Before/After medical-adjacent | Shows workflow/scene contrast, no treatment result |
| Change Concept after first plan | Mechanism slug and central payoff differ |
| Product URL failed | Claude says page was not used or asks one question; no pretending |
| Long page context | No “context too large”; compact facts sent |

## Market-critical product promise

Storyflow should promise:

> “Give us a product URL or photo. Storyflow turns it into several UGC ad concepts, picks a strong 15-second script and visual plan, generates a realistic video, and saves it with history/export.”

Not:

> “We use Wan/Seedance/OpenRouter.”

## Current files/areas likely involved

| Area | File |
|---|---|
| format biases/schema | `apps/api/app/creative_direction.py` |
| Claude adapter | `apps/api/app/providers/claude.py` |
| system prompt | `apps/api/app/prompts/video_chat/v3.py`, `v2.py` |
| context bundle / URL/image evidence | `apps/api/app/services/chat_context.py` |
| chat persistence/apply | `apps/api/app/services/chat.py` |
| provider request | `apps/api/app/providers/openrouter.py` |
| recipe compiler | `apps/api/app/video_recipe.py` |
| frontend chat summary | `apps/web/features/chat/*` |
| preview/download | `apps/web/features/create/preview.tsx`, `/api/media` route |

## Source links

- Predis product video maker: https://predis.ai/product-video-maker/
- Predis AI video generator: https://predis.ai/ai-video-generator/
- Predis AI ad generator: https://predis.ai/
- Topview advertising use case: https://www.topview.ai/use-cases/advertising
- Arcads complete platform guide: https://intercom.help/arcads/en/articles/15503340-everything-you-can-do-on-arcads-complete-platform-guide
- Arcads getting started: https://intercom.help/arcads/en/articles/14531683-getting-started-with-arcads
- Creatify AI influencer / URL-to-video info: https://creatify.ai/features/ai-influencer-generator
- Creatify API: https://creatify.ai/api

