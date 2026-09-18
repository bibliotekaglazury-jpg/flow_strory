# Local render verification

Source of truth is the pinned RVE commit in NOTICE.md. `stats.json` contains the
measured counts; `manifest.json` contains each component's source hashes and render
evidence. Import has also been repeated into a separate temporary output: all 81
source hashes, schemas, renderer configs, categories and supported formats match.
See validation/repeatability.json.

The completed checks use Remotion 4.0.523 and its managed Chrome Headless Shell 149:

- All 81 components compile and register, validate defaults against their schemas,
  and render frame 30 and frame 449 at 1280×720, 30 fps, 15 seconds.
- Each editable template must produce different actual pixels for changed inputs.
  The 3 image templates use an original local PNG passed through the same byte
  validation and data-URL conversion as worker media. No remote stock images load.
- Glitch Text and Logo Glitch Reveal additionally change each field independently
  at settled frame 120. RGB copies share their headline; the clean logo, company
  name and tagline remain editable after the ghost layers disappear.
- All 81 thumbnails are genuine rendered WebP images. `validation/contact-sheet.png`
  is a contact sheet of those actual thumbnails.
- The shared fit/duration wrapper was rendered for text (`animated-text`), image
  (`ken-burns`) and duration-sensitive motion (`camera-shake`) across all 3 aspect
  ratios and 3 durations. Exact frames/hashes: validation/wrapper-matrix.json.
  These are representative shared-wrapper checks, not 81 full aspect/duration
  matrices. Twelve components that read output geometry directly advertise 16:9
  only. Other portrait/square outputs fit a landscape stage with letterboxing.
- Three genuine H.264 preview excerpts contain 90 frames / 3 seconds. Their underlying
  compositions remain 15 seconds; actual jobs retain 15/20/30-second duration semantics.
  The backend also rendered and stored a real 15-second portrait job; its independent
  receipt and artifacts are under docs/verification/rve-job.*.

The five bounded review repairs were re-rendered. Evidence for the other 76 was
retained only after reproducing the original global fingerprint, proving shared
executable code unchanged, and verifying every individual source/config and actual
thumbnail hash. See validation/pre-review-checkpoint.json and review-migration.json.
Renderer fingerprints are now per template plus shared executable code; TypeScript
annotations do not invalidate unchanged executable evidence.

The 61 enabled entries exclude 10 fixed-data charts and 10 layouts that only contain
media placeholders. Those 20 remain imported, compiled and frame-validated, but are
curated off until actual data/media mappings exist. Eight enabled entries are
featured. No failed components remain.

Similarity review found no identical source hashes, thumbnail files, or combined
early/late frame pairs. A broad 64-bit difference hash produced 241 candidates;
a 128×72 RGB comparison narrowed these to 10 close pairs. Source and contact-sheet
review retained those as distinct motions (for example, blur, squash/drop, rotation,
RGB separation, blinds, spring push and whip-pan). Decisions are tied to exact
adapted source hashes in similarity-decisions.json; near-duplicates.json records
all measurements. Shared end artwork alone is not treated as duplicate animation.

Publication disables affected entries before compile/browser startup and keeps them
disabled until individual checks and the shared wrapper gate succeed. Fatal shared
failures disable the catalog. Resume additionally requires the matching fingerprint
and actual thumbnail bytes. Tests exercise compile/startup/wrapper failure paths,
missing or changed thumbnails, source provenance, input validation and public-field
projection. No production deployment or commercial runtime authorization is implied.
