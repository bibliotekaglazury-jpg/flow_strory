# Product Look Studio generated gallery visual QA

- Reference: user-approved dark overlapping Look Gallery mockup supplied in chat on 2026-09-13.
- Scope: generated-photo results, Look stack, bulk download, angle regeneration, desktop and mobile interaction.
- Desktop viewport: 1440 × 1100.
- Desktop capture: `/private/tmp/forma-look-gallery-desktop.png`.
- Mobile viewport: 390 × 844.
- Mobile capture: `/private/tmp/forma-look-gallery-mobile.png`.
- Uncropped-photo capture: `/private/tmp/forma-look-gallery-full-photo.png`.

## Comparison

- P0: none.
- P1: none.
- P2: none.
- P3: test fixtures reuse one image for every result and product, so the verification capture cannot demonstrate the visual variety of real generated angles. Card geometry, numbering and interaction states are verified independently of fixture content.

The result stage matches the selected direction: deep navy background, a separate vertical Look stack, portrait cards with lime borders, overlapping depth, editorial numbering and a dominant center card. A completed four-photo set opens on `01 → 02 → 03`, with the three-quarter image centered. Mouse wheel, pointer drag, keyboard arrows and direct card selection change the active image. The bulk-download action remains prominent, while the existing additional-angle panel stays directly below the gallery.

Generated images use `object-fit: contain`, so every original is visible in full inside the portrait card. The bulk action creates one `look-photos.zip`; the browser test opens the archive and verifies all result files are present.

On mobile, the Look stack becomes a horizontal strip and the card stack remains portrait-oriented with cropped neighboring cards visible as navigation cues. The page has no horizontal document overflow.

## Verification

- Changed-file ESLint: passed.
- TypeScript: passed.
- Vitest: 14 files, 63 tests passed.
- Product Look Studio Playwright: 5 tests passed, including wheel, drag, download and mobile overflow.
- Local visual captures: passed against the approved reference.

Final result: passed.

# Subtitle Studio frontend — 2026-09-14

- Source visual truth: `docs/references/subtitle-studio/approved-editor-9x16.png` (1487 × 1058 px).
- Browser implementation: `docs/verification/subtitle-studio/desktop-with-shell-final.png` (1440 × 1024 px at a 1440 × 1024 CSS viewport, device scale factor 1).
- Full-view comparison: `docs/verification/subtitle-studio/comparison-final.jpg`.
- Focused inspector comparison: `docs/verification/subtitle-studio/focused-inspector-final.jpg`.
- Additional states: `docs/verification/subtitle-studio/desktop-16x9-final.png` and `docs/verification/subtitle-studio/mobile-9x16-pass-2.png` at 390 × 844 CSS px.
- State: loaded local preview video, first transcript cue active, Modern preset active, safe area enabled, export idle.

## Findings

- P0: none.
- P1: none.
- P2: none after two correction passes.
- P3: the browser fixture is a 10-second local product clip while the approved mockup depicts a 32-second clip. Timing labels therefore differ, but the editor hierarchy and behavior are the same.

The implementation preserves the visual target's dark Forma shell, white two-column editor, complete portrait video, editable transcript rows, lime active state, four style presets, compact controls, and full-width waveform timeline. The existing Forma navigation contains the new Subtitles entry. The 16:9 state changes the player and editor proportions, while the phone state stacks the same controls without document overflow.

Typography uses the project's Instrument Serif and Inter assets. Spacing and desktop density align with the reference after constraining the workspace to the viewport. Colors map to the existing navy, white, gray, and lime product tokens. The sample video remains sharp and uses `object-fit: contain`; no visible asset is replaced with a CSS approximation. Copy is product-facing and does not mention backend providers.

Focused comparison was used for transcript row height, edit/delete affordances, style tiles, position/size controls, colors, and safe-area switch. The final browser capture shows those controls at readable scale.

## Comparison history

1. Pass 1 found a P1 vertical expansion: Remotion's intrinsic 1920 px height stretched the workspace and moved the timeline below a large blank region. The player wrapper and immediate Remotion root were constrained by the chosen aspect ratio.
2. Pass 2 found a P1 escaped video layer and invisible captions. The Remotion root now fills the bounded shell, and caption sizes use composition pixels so the overlay scales correctly.
3. Pass 3 added the reference's per-row edit/delete affordances and restored the shared Forma sidebar. The final full and focused comparisons show no actionable P0/P1/P2 difference.

## Interactions and browser checks

- Edited transcript text and observed Saving → Saved.
- Selected a caption style.
- Switched 9:16 → 16:9.
- Ran the frontend export state through Exporting → Download video.
- Checked the 390 × 844 layout for horizontal overflow.
- Checked browser console and page errors in the focused Playwright scenario; the repository-wide missing `/favicon.ico` request was excluded because it is unrelated to this screen.

Final result: passed.

# Create template placement and image fit — 2026-09-13

- Reference: production Create screenshot supplied by the user on 2026-09-13.
- Desktop viewport/capture: 1440 × 1100, `/private/tmp/create-templates-desktop.png`.
- Mobile viewport/capture: 390 × 1200, `/private/tmp/create-templates-mobile.png`.
- Verified: the Recommended template selector renders immediately below the step indicator and before the upload grid at both widths.
- Verified: template artwork uses `object-fit: contain` with a neutral backing surface, so the complete source frame remains visible.
- Deviation: the local API was not running during capture, so template records were absent from the local screenshots. The deployed source, production CSS and healthy production route were checked separately.

Verification: 64 Vitest tests, TypeScript, changed-file ESLint and production build passed.

# Create hero video gallery — 2026-09-13

- Reference: user-approved 1536 × 960 hero mockup supplied in chat; background source `background.png`.
- Local desktop capture: 1536 × 960 viewport, `/private/tmp/hero-video-gallery-desktop.png`.
- Local mobile capture: 390 × 844 viewport, `/private/tmp/hero-video-gallery-mobile.png`.
- Production desktop capture: 1536 × 960 viewport, `/private/tmp/hero-video-gallery-production-desktop.png`.
- Verified: supplied background covers the hero; four overlapping portrait videos appear on desktop and two on mobile; all cards preserve the reference tilt and lime-accent interaction.
- Verified: all 16 former side-rail videos cycle through the hero with automatic advance and previous/next controls. Hover and keyboard focus pause carousel rotation while video playback continues.
- Verified: the side video rail is absent, the closed Try On panel leaves the Create workspace full width, and neither viewport has horizontal document overflow.
- P3: brightness varies between source videos; this is authentic source footage rather than a layout defect.

Verification: 64 Vitest tests, TypeScript, changed-file ESLint, production build and 29 Playwright tests passed; 1 developer-only Playwright case was skipped by configuration. Production route and background asset returned HTTP 200.

Final result: passed.

# Create hero gallery auto-scroll correction — 2026-09-13

- Replaced timed card swapping with a real horizontal track transition: four cards remain visible while a fifth card waits outside the clipped viewport and slides in from the right.
- The track advances one card every 5.2 seconds with a 700 ms eased transition and continues through all 16 videos.
- Hover and keyboard focus pause only the gallery movement; the videos continue playing.
- Responsive track windows preserve four desktop cards, three tablet cards and two mobile cards without horizontal page overflow.

Verification: focused Playwright tests passed locally (2/2) and against the production container through an SSH tunnel (1/1); TypeScript, changed-file ESLint and the production build passed.

Final result: passed.
