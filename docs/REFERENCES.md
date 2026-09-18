# Visual references

## Primary reference

The supplied dark Luma-style dashboard mockup is the PRIMARY VISUAL SOURCE OF TRUTH. The user supplied and designated the attached image as the frontend reference on 2026-09-10. Visual inspection confirms:

- Dark application shell and compact left navigation.
- White central “Create Your Video” workspace with lime accents.
- Large but restrained hero.
- Video result/preview area.
- Templates and recent generations below.

## Availability and approval record

Reference ID: **REF-001 — Luma-style creation dashboard**, supplied in the user's follow-up message on 2026-09-10. Applicable screen: desktop Create page, with populated sample inputs, selected style, video preview, templates, and recent creations. The attachment is visually available in this conversation and has been inspected. The displayed image is approximately 1222 × 1287 px; original file metadata has not been verified.

Original REF-001 located and saved as [dashboard-reference.png](references/dashboard-reference.png), copied unchanged from `/Users/stas/Downloads/2a84f812-c178-4a42-a795-bbf57187b45d.png`. Verified size: 1222 × 1287 px, RGB. The original is now available to future agents. HERO-001 is saved unchanged as `references/hero-photo-original.png` and `apps/web/public/hero-woman.png`. HERO-002 also has the requested canonical alias `references/make-it-real.svg`.

Desktop visual direction is now confirmed by REF-001. Mobile reference/adaptation is still pending. Measurements below are approximate visual readings of the displayed attachment, not pixel-sampled tokens. Frontend implementation is now authorized by BUILD_BRIEF.md.

## Generated template artwork — 2026-09-10

The first eight business templates use original generated product/UGC preview
artwork in `apps/web/public/template-styles/`. These images establish the
template-selection visual bar: authentic creator-led product moments, vertical
composition, and no decorative graphic placeholders. They are illustrative
preview art only and do not promise a matching generated video output. They
contain no third-party logos, brands, or licensed stock imagery.

## Observed desktop composition

- Full-height near-black blue-tinted shell. Left sidebar is approximately 178 px wide, with icon-and-text navigation rather than an 80 px icon rail.
- Main content begins near x=198 px, with approximately 20 px gutters. Hero occupies the upper region down to roughly y=342 px. Large editorial serif text sits left; a photographic person/product composition fills the right. Account and credit controls sit at the upper right.
- White creation workspace spans approximately x=198–927 and y=342–903: about 729 × 561 px. The adjacent preview column begins near x=937 and is approximately 264 px wide. Preserve the roughly 2.75:1 workspace-to-preview width relationship at this reference size, not fixed widths on every viewport.
- Workspace order: title; compact Input / Style / Prompt / Generate indicator; three side-by-side input groups; thumbnail style selector; campaign textarea; bottom row with duration, aspect ratio, collapsed advanced options, and dominant lime Generate Video CTA.
- Product, optional person, and existing-video inputs have thin pale outlines, light surfaces, restrained rounded corners, and real image/video thumbnails.
- The right preview is a tall portrait video frame with rounded border and a small thumbnail strip underneath. Preview starts level with the white workspace, not above the hero or below history.
- Templates and Recent Creations form compact horizontal thumbnail rows below the workspace/preview band. They sit directly on the dark shell without large wrapper cards.
- The hero uses a high-contrast serif with a lime italic word; functional UI uses a clean sans-serif. Use the explicitly supplied HERO-002 asset for the handwritten slogan; do not add a decorative UI typeface.

## Reference versus product scope

REF-001 establishes visual composition, not permission to expand the MVP. Preserve the original written constraints where the image contains excluded features:

- BUILD_BRIEF now explicitly authorizes Create, Templates, Library, Brand Kit, Analytics, Billing, and Settings navigation. Only Create is a complete MVP workflow; unsupported destinations must clearly state they are not available, without fake functionality.
- Do not copy brand logos, Luma identity, promotional slogans, the +320% engagement block, social engagement counters, or fabricated customer endorsements.
- Credit balance, 36-credit CTA cost, subscription upsell, sample durations, and media file limits shown in the image are illustrative, not approved product economics or validation rules.
- The selected 15s, 9:16, and UGC Review options are observed reference state; production defaults remain a product decision.
- Product-spec template names and all eight required templates take precedence over the image's abbreviated/different gallery labels. Do not add Lifestyle as a ninth template.
- The four-step indicator is visual guidance within the one-page flow, not authorization for a multi-page wizard. Interaction semantics remain to be documented before implementation.
- Generate Prompt remains required by PRODUCT_SPEC even though the reference does not show a separate button. Its secondary placement needs resolution without displacing the dominant CTA.
- Dark photographic shading does not authorize gradients throughout the UI. The reference's translucent promotional block does not override the explicit no-glassmorphism rule.

## Hero photo — HERO-001

The user explicitly selected the photo attached after REF-001 for the hero section on 2026-09-10. It shows a woman wearing a beige cap and light sweater, holding a skincare jar. Use this specific supplied photo as the hero artwork, positioned on the right in REF-001's composition, with the heading on the left. Do not substitute a generated image. Preserve the face, cap, and held product when adapting the crop; do not stretch the image.

Asset status: supplied original `/Users/stas/Downloads/hero  girl.png` saved unchanged as [hero-photo-original.png](references/hero-photo-original.png) and `apps/web/public/hero-woman.png`. Verified PNG dimensions: 1222 × 1287 px, with alpha transparency. The original remains intact; the application uses CSS positioning and cropping only.

This selection authorizes this specific photo for the hero, including its embedded product details; it does not authorize copying Luma branding elsewhere in the interface.

## Hero lettering — HERO-002

The user explicitly supplied `make-it-real-production.svg` as hero text artwork. Original source: `/Users/stas/Downloads/make-it-real-production.svg`. Saved repository asset: [make-it-real-production.svg](references/make-it-real-production.svg). Preserve this original unchanged.

The SVG reads “Make it real!”, uses a 300 × 180 viewBox, a slightly rotated text group, and an underline. Use it as the small hero lettering on the right in REF-001, not as the main heading. This explicit selection supersedes the earlier exclusion of the handwritten slogan for this asset only; it does not authorize a decorative font throughout the UI.

Implementation note: this SVG uses live text with `Segoe Script, Brush Script MT, cursive` fallbacks, not outlined paths, so its appearance depends on available fonts. It also uses `currentColor`; future integration must deliberately supply the lime color and verify rendering, since an external image does not inherit page text color. Do not silently modify the source. Exact cross-device lettering fidelity requires a verified font or an approved outlined derivative. Integrated into the hero using a lime CSS mask; font-dependent lettering remains a fidelity limitation.

## Composition qualities to keep

Preserve visual hierarchy, strong contrast, the white workspace against the dark shell, dominant Generate button, clean upload fields, simple template selection, strong product imagery, and low cognitive load.

## Do not copy

Do not copy exact Luma branding, logos, copyrighted assets, exact marketing copy, or proprietary imagery. Use supplied authorized product assets or clearly labeled neutral test assets. The requested “Create Your Video” workspace label is part of this product brief.

## Recreate

Recreate layout logic, visual hierarchy, spacing, contrast, premium feel, and workflow clarity. The reference is not permission to import unrelated features visible in a source product. PRODUCT_SPEC remains the scope boundary.

## Visual acceptance evidence

Record the reference revision, screen/state, runtime URL, viewport and device scale, rendered screenshot path, comparison method, visible differences, and fixes. Compare at the reference viewport; inspect mobile at an approved viewport separately. If a mobile reference is absent, assess an explicitly approved responsive adaptation and do not call it a pixel match.

## Hero background — HERO-003

The user explicitly supplied and approved the hero background CSS. Saved reference asset: [hero-background.css](references/hero-background.css). This is a preserved design source, not an imported application stylesheet; integration is now authorized by BUILD_BRIEF.md.

Preserve the supplied dark linear base, cyan ambient layer, warm amber bloom, blue depth, small lime halo, vignette, and subtle film grain. This is an explicit hero-only exception to the earlier restrictions on gradients and glow; it does not authorize gradient-heavy cards, glassmorphism, or additional decorative colors elsewhere.

Normalization performed while saving: removed pasted Markdown escapes and repaired the Markdown-link artifact inside the grain data URI to restore the SVG namespace `http://www.w3.org/2000/svg`. Visual values and selectors were retained. The embedded SVG parses successfully; the background is integrated; rendered comparison evidence is recorded in VERIFICATION.md.

For future integration, the stylesheet expects `.glow-cyan`, `.glow-amber`, `.glow-depth`, `.glow-lime`, and `.grain` children within `.hero`. Scope the generic root variables to the hero when integrating to avoid collisions with application tokens. `--bg` is declared but not used by this snippet and does not replace the shell token; `--lime` is a translucent halo color, not the primary CTA color. Verify layer order, contrast, and responsive cropping with the actual hero photo before claiming completion.


User-approved preview video (2026-09-10): `/Users/stas/Downloads/Create_a_realistic_second_ve.mp4`, preserved at `apps/web/public/media/create-preview.mp4`. Use in the existing large 9:16 preview immediately right of the white creation workspace, beneath the hero. It is a supplied example, not a generated user job. Real job loading/error/output behavior takes precedence. Playback starts automatically, muted and looping, per the latest user instruction; controls retain pause access. Poster derived from this same video. Source: 720×1280 H.264/AAC, approximately10seconds.
