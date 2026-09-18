## Creative concept extension — 2026-09-10

Add a compact Auto choice above existing format thumbnails; default Auto. Keep the chat within the white workspace and show a short concept plus spoken script and Use this concept / Change concept. Raw planning keys and provider details are not shown. Existing manual production-prompt editing remains. No shell/hero/sidebar redesign. See CREATIVE_DIRECTOR.md.

# UI system

## Prompt chat extension — authorized 2026-09-10

Use compact AI Chat / Manual segmented controls inside the white workspace after
style selection. assistant-ui primitives use existing ink/muted/line/radius tokens.
Bound conversation height with internal scrolling; composer stays next to messages.
Recipe summary is a simple divider and text, with a restrained outlined Apply action.
Generate Video remains the dominant lime CTA. No standalone chat page, agent sidebar,
tool transcript, provider badges, markdown HTML execution or decorative chat cards.
Mobile retains readable input text and wrapping actions. Reset cancels/deletes the
application conversation; it does not cancel a submitted video generation.

## Status and governing direction

Approved direction: dark shell, white creation workspace, lime accent, premium typography, strong contrast, minimal visual noise, and one-page creation. REF-001 is now visually inspected; see REFERENCES for composition and scope exclusions. Geometry readings are approximate; all exact numeric tokens below are **provisional until verified against the original reference file**. They are not pixel-sampled measurements. Use semantic token names so approved corrections apply consistently.

## Color system

| Semantic token | Provisional value | Use |
| --- | --- | --- |
| shell | #071117 | Overall application background |
| sidebar | #0B151C | Compact left navigation |
| workspace | #FFFFFF | Central creation surface |
| text-on-light | #171917 | Primary workspace text |
| text-on-dark | #F5F5F2 | Shell headings and content |
| muted-on-light | #62665E | Secondary workspace text |
| muted-on-dark | #A6AAA1 | Secondary shell text |
| border-on-light | #D8DCD3 | Form and workspace dividers |
| border-on-dark | #343831 | Shell dividers |
| accent | #D5FF32 | Dominant CTA and limited selection cues |
| accent-hover | #C5EF26 | Hovered primary action |
| accent-ink | #171917 | Text on lime surfaces |
| error-on-light | #B42318 | Actionable errors on white |
| error-on-dark | #FDA29B | Errors in shell |
| success-on-light | #276738 | Confirmed success on white |
| success-on-dark | #86CB97 | Confirmed success in shell |
| disabled-surface-light / ink-light | #E9EBE5 / #686D63 | Disabled workspace controls |
| disabled-surface-dark / ink-dark | #292C26 / #969C8F | Disabled shell controls |

No decorative palette expansion. Semantic success and error colors appear only for actual states; never color alone. Borders above are subtle separators, not sufficient by themselves for interactive-boundary contrast: use text, structure, or an approved stronger boundary where required. Validate rendered text and control contrast to WCAG AA before token approval. Use visible two-tone focus treatment appropriate to dark and light surfaces; lime alone is insufficient against white.

## Typography

Proposed primary font: locally hosted Inter, with system sans-serif fallback, subject to reference/font-license verification. REF-001 establishes an editorial serif for the hero, including restrained italic lime emphasis. Its exact family is unidentified: select a matching licensed face after original-image inspection. Keep the rest of the interface sans-serif; the only handwritten exception is the user-supplied HERO-002 SVG lettering asset documented in REFERENCES, not an additional UI font.

| Role | Proposed desktop size / line height | Weight |
| --- | --- | --- |
| Display/hero | Approximately 64 / 62 px serif at reference desktop width; mobile proposal 32 / 36 px | 400 |
| Section title | 22 / 28 px; mobile 20 / 26 px | 600 |
| Body | 15 / 22 px | 400 |
| Label | 13 / 18 px | 500 |
| Button | 14 / 20 px | 600 |
| Metadata | 12 / 18 px | 400 |
| Numeric/credits | 14 / 20 px, tabular numerals | 500 |

Use restrained tracking; no all-caps marketing treatment or oversized credit counters. Form text should be at least 16 px on touch layouts where needed to avoid browser zoom. Hero is a concise product heading, not a landing-page section.

## Spacing and layout

Proposed base spacing scale: 4, 8, 12, 16, 24, 32, 40, 48 px. Keep alignment on shared columns.

| Context | Proposed rule |
| --- | --- |
| Page gutters | Approximately 20 px at reference desktop width; proposed 20 px tablet, 16 px mobile |
| Sidebar | Approximately 178 px at reference width, with icon-and-text items; not an icon-only rail |
| Workspace padding | Approximately 22 px desktop; proposed 20 px tablet, 16 px mobile |
| Secondary item padding | 16 px; do not wrap every field in a card |
| Vertical section gaps | 24 px within workspace; 32 px between main regions |
| Form controls | 8 px label-to-control, 16 px field-to-field |
| Grid gaps | 16 px desktop/tablet, 12 px mobile |
| Controls | 44 px minimum proposed height; preserve readable labels |
| Responsive layout | Proposed mobile <768 px, tablet 768–1023 px, desktop ≥1024 px |

At the displayed reference size, the workspace is approximately 729 px wide and the right preview column 264 px wide, separated by about 10 px. Both begin near y=342 px; the hero stays above them. Three input groups share one row. Template and recent-generation rows span the main region below. These are reference proportions, not rigid viewport-independent dimensions; see REFERENCES. Exact font identity, pixel colors, and production navigation contents remain unresolved. Proposed mobile adaptation stacks inputs and preview in workflow order without horizontal overflow; compact navigation must preserve existing destinations and requires approval before implementation. Do not invent a drawer or extra navigation destinations. Avoid arbitrary empty gutters or fixed heights that truncate content.

## Radius and shadows

Proposed radii: 4 px small tags/thumbnails, 8 px inputs/buttons, 12 px primary workspace and preview frame. Pills only for a confirmed segmented-control design. Never assign unrelated radii per page.

Default shadow: none. Optional restrained overlay shadow: 0 4px 16px rgba(0,0,0,0.12), only where an approved popover needs separation. No glow, stacked shadows, or decorative elevation on UI components. The explicitly supplied HERO-003 ambient hero background is a scoped exception, not a component shadow style.

## Component rules

| Component | Required behavior and visual constraint |
| --- | --- |
| Sidebar | Compact 178 px icon-and-label dark navigation at reference size; only approved destinations. Consistent meaningful icons with accessible names; no speculative complexity. |
| Header | Quiet utility area; credits/account only where approved; do not compete with creation. |
| Hero | Reference-height photographic band, editorial serif heading left and authorized person/product imagery right; no added marketing sections, brand strip, or engagement metric. |
| Create-video workspace | One white central surface left of portrait preview. Preserve title, compact four-step indicator, three input groups, style row, brief, and settings/CTA row. Indicator must not turn the flow into a multi-page wizard. |
| Upload cards | Clean outlined image/video inputs with descriptive labels, optional markers, keyboard-operable picker, preview, remove/replace, upload/error feedback. Drag-and-drop is supplementary. |
| Template selector | Simple single selection from the eight MVP templates; visible and programmatic selected state. No model badges. |
| Textarea/prompt editor | Campaign brief is primary natural-language input; editable generated prompt lives in collapsed advanced settings. Preserve edits, show validation inline. |
| Segmented controls | Duration and aspect ratio; compact mutually exclusive options with keyboard navigation and clear labels. |
| Model/advanced settings | Collapsed by default; Auto model/voice. Show capabilities returned by API; no provider branding or invented settings. |
| Generate CTA | Single dominant lime “Generate Video” button. Estimated credits immediately adjacent before submission; Generate Prompt is secondary. Explain disabled states. |
| Video preview | Right-hand portrait frame and small thumbnail strip as observed; use actual output aspect ratio, accessible playback, and real output/download action. No fabricated social counters; thumbnail semantics need product definition. |
| Progress/loading | Separate uploading, queued, generating; use actual progress or indeterminate feedback, never fabricated percentages or countdowns. Announce updates politely without focus theft. |
| History cards | Compact recent-generation items with thumbnail/status/duration/time/open or download; no analytics embellishment. |
| Template gallery | Below creation, as described in reference; uses the same templates and selected-template state as selector, not a second workflow. Use authorized imagery only. |
| Billing/credits | Quiet real balance plus current estimate; accessible billing entry to external checkout/portal. No decorative metrics or invented pricing. |

## Anti-AI-slop rules

Forbid gradient-heavy UI; gradients are allowed only when explicitly present in the approved reference or supplied by the user. HERO-003 is the approved hero-only background exception, including its ambient glow and grain; preserve its supplied values without extending them to other surfaces. Forbid giant rounded cards everywhere, unnecessary glass panels/glassmorphism, neon everywhere, fake analytics blocks, meaningless badges, 3D decorative blobs, excessive shadows, oversized empty whitespace, landing-page sections inside the product, generic “AI magic” clichés, random icons, inconsistent icon styles, and inconsistent border radii. Do not replace the approved custom composition with a generic AI-SaaS dashboard.

## Phase2A catalog extension

Preserve dark shell, typography, lime selections and original Create layout. /templates uses search, primary category chips (All, UGC, Product, Ads, Hooks, Testimonials) and More for other categories; compact secondary selects for type, format, duration, inputs, use case. Active filter chips, result count and one conditional Clear action. Metadata drives visibility and filtering; never render all categories as a long single row. Media thumbnails show real validated template frames. Template engine labels are AI Generated and Render Template; hide repository, component paths and Remotion branding from normal users. No decorative metrics; numeric content inside source render templates is user-provided video content, not dashboard analytics.

Chat repair (2026-09-10): Manual explicitly describes the brief field and missing
prerequisites. Full-plan labels are human-readable; unknown/gibberish input must
produce clarification instead of placeholder scenes. Demo sessions carry explicit
simulation copy; live sessions never show it. Keep the existing composition.

## Manual simplification — user approved 2026-09-10

The user explicitly requested removal of the pictured campaign-brief block from
Manual. Remove its explanatory paragraph, brief textarea/label and Generate Prompt
action. AI Chat remains only in AI Chat mode; existing production-prompt editing
and generation settings remain. This supersedes the earlier Manual brief guidance.


## User-approved result placement — 2026-09-10
Generation status, errors and the playable result belong directly below the chat in the white workspace. Before submission show a compact explanatory empty state. The right-side reference/example video remains separate. Result dimensions follow the generation aspectRatio (9:16,1:1,16:9); never crop output to fake a format. This supersedes the original right-column placement of actual job output.
