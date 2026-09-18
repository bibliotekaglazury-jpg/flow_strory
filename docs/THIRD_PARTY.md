# Third-party review

## Local chat dependencies — 2026-09-10

`@assistant-ui/react` 0.15.18 installed as UI primitives only, with external-store
runtime calling our typed services; no ChatKit or separate agent backend. Installed
package declares MIT. No upstream visual design copied. Lockfile pins transitives.

`@higgsfield/cli` 1.1.24 installed as a local dev tool. Audited actual MIT LICENSE in
https://github.com/higgsfield-ai/cli at
`8827135df7601667f66cd36ce84cf72106d690c4` (Copyright 2026 Higgsfield AI).
The repository contains README, MODELS, install script and notices, not complete
CLI implementation source. Reviewed npm install.js before running; it downloads
the versioned official darwin-amd64 release and extracts only the named binary.
No template/code/media library was imported. `auth --help` confirms OAuth PKCE;
`auth token` was deliberately not invoked. Account login did not complete.
CLI help confirms create/get/wait and media UUID/local-path inputs; live schemas
are not yet audited. MockHiggsfieldProvider uses our existing original video fixture.

Official MCP documentation: https://higgsfield.ai/creator-hub/help-center/integrations/what-is-higgsfield-mcp .
Official CLI documentation: https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-access-higgsfield-via-cli .
Both use OAuth/account credits; website Unlimited/free allowances do not carry into
CLI/MCP generation. No real generation or external credit-spending test was run.

Inspected 2026-09-10 before application implementation. No source code has been copied from the four reference projects. Architectural observations are recorded below; implementation is original. Reassess this record if any source is later adapted.

| Repository / pinned commit | Actual license inspection | Observed patterns / reuse decision |
| --- | --- | --- |
| [Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI/tree/288f7da15999bc9804d9a235e95d65bc31668671) | Root LICENSE: MIT, © 2026 Open Generative AI Contributors | Inspected src/lib/muapi.js, packages/studio/src/utils/generationLifecycle.js and registry paths. Study request-ID polling, terminal-state normalization, model endpoint metadata. Reimplement server-side; reject its browser API-key storage and raw-payload logging patterns. No copied code. |
| [nanoart](https://github.com/nanoartApp/nanoart/tree/dafa9bd878d3bd16e424903ebc7f4306a7cdd212) | No LICENSE/COPYING found in checkout | Inspected package.json, middleware.ts, lib/api/image-service.ts and repository tree. Current checkout is a frontend/image-service project, not evidence of a production credit ledger, Prisma, Stripe, or R2 implementation. No source reuse permitted without compatible license. |
| [dart](https://github.com/jasonca2023/dart/tree/257c5650f9cf90dedfe1978163e46f0978813c4f) | Root LICENSE: MIT, © 2026 Jason Guo | Inspected backend/app/models.py and providers/base.py; product → structured script → video boundary and normalized errors inform domain separation. No copied code or visual design. |
| [ai-video-generation](https://github.com/GongLingRui/ai-video-generation/tree/0ffb85a1fbb0e93896cad530831a5ecf8888a175) | Root LICENSE: MIT, © 2026 AI Video Storyboard Platform Contributors | Inspected src/lib/model-registry.ts and hooks/use-chain-generation.ts. Record future first/last-frame continuity through ordered beats. No canvas/editor copied or implemented. |

MIT notices must accompany any future substantial copied portions. No AGPL/GPL application source is introduced. Runtime package licenses and bundled font notices must be recorded after exact dependency installation; source-review licenses do not cover all transitive dependencies.

User-supplied dashboard is a comparison artifact, not a flattened application background. User-supplied SVG/background CSS are approved artwork sources. Do not extract copyrighted template thumbnails from the reference without authorization; neutral test assets must be clearly labeled.

## Installed direct JavaScript dependencies

Versions and license metadata read from installed package manifests; pnpm-lock.yaml pins transitives. This is a direct-dependency inventory, not a legal audit of all transitives.

| Package | Version | Declared license |
| --- | --- | --- |
| @fontsource/instrument-serif | 5.3.0 | OFL-1.1 |
| @fontsource/inter | 5.3.0 | OFL-1.1 |
| @playwright/test | 1.63.0 | Apache-2.0 |
| @radix-ui/react-slot | 1.3.3 | MIT |
| @supabase/auth-ui-react | 0.4.7 | Check package license |
| @supabase/auth-ui-shared | 0.1.8 | MIT |
| @supabase/ssr | 0.12.7 | MIT |
| @supabase/supabase-js | 2.116.0 | MIT |
| @tailwindcss/postcss | 4.3.3 | MIT |
| @types/node | 22.20.2 | MIT |
| @types/react | 19.3.0 | MIT |
| @types/react-dom | 19.3.0 | MIT |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx | 2.1.1 | MIT |
| eslint | 9.39.5 | MIT |
| eslint-config-next | 16.3.4 | MIT |
| lucide-react | 1.43.0 | ISC |
| next | 16.3.4 | MIT |
| prettier | 3.6.2 | MIT |
| react | 19.3.0 | MIT |
| react-dom | 19.3.0 | MIT |
| tailwind-merge | 3.6.0 | MIT |
| tailwindcss | 4.3.3 | MIT |
| typescript | 5.9.3 | Apache-2.0 |
| vitest | 5.0.0 | MIT |

The supplied hero PNG is preserved unchanged. Original neutral SVG template fixtures and labeled demo video outputs are test media, not real customer results.

## Backend and media licensing

Backend source is original; FastAPI/Pydantic/SQLAlchemy/Alembic use MIT, psycopg uses LGPL-3.0, boto3/botocore and Stripe Python use Apache-2.0, Redis Python and uvicorn use BSD licenses. Verify installed versions against apps/api/pyproject.toml before distribution; backend dependency ranges are not a frozen deployment lock. No GPL imageio-ffmpeg or PyAV wheel is an application dependency. Docker defines an LGPL-only FFmpeg source build, not yet built locally; exact source hash, flags and redistribution obligations are recorded in BACKEND_VERIFICATION.md. Existing external FFmpeg was used only as a local tool. Fontsource Inter and Instrument Serif declare SIL OFL-1.1; retain the package license files when distributing font assets.

## Phase2A — RVE audit completed before copying application code

Source: https://github.com/reactvideoeditor/remotion-templates/tree/6209b724798e48ff395f8df1a6fa2d26082372b5 . Exact commit: `6209b724798e48ff395f8df1a6fa2d26082372b5`. Read-only checkout: /private/tmp/ugc-rve-phase2a. Tracked tree contains README.md and81TSX files directly under templates/, no package.json, lockfile, LICENSE/COPYING, media files, fonts or composition registry. Actual discovered count81, independently counted from files. File hashes/dependencies/remote references: audits/rve-source.json.

License evidence: README's License section explicitly assigns MIT to all templates and permits personal/commercial use. No full LICENSE text or copyright-year statement is shipped; do not falsely claim one was verified. Individual headers in some files name the React Video Editor team and grant project use; no contradictory license or separate asset grant found in any source file. Import code under the repository-wide MIT declaration, retain original headers, attribution, README declaration and standard MIT terms; do not fabricate upstream copyright years. This is source evidence, not a guarantee of upstream title to third-party material.

Imports actually found:78files import remotion;3import React;2of those import next/image. No versions declared.78default function components have hard-coded content and no prop interfaces;3image components expose imageUrl and motion options. No registered compositions; README only illustrates caller registration. Fonts are CSS fontFamily references (Inter/system/sans-serif/monospace), no font downloads/files. Use our licensed local Inter with OFL notice.

Remote example media exclusions: ken-burns uses an Unsplash URL; parallax-pan and zoom-pulse use Pexels URLs. Do not download or redistribute those media: replace URL defaults with our own neutral local illustration. The source does not separately license these photos. No other runtime external media found; attribution URLs in comments are not runtime fetches. Logo templates draw generic shapes/text in source; inspect/replace any demo brand wording before public enablement. No stock/logo/font assets copied.

Render-specific corrections required before enablement:3image components use wall-clock CSS keyframes (2also next/image); floating-bubble-text contains CSS animation; typewriter-subtitle uses Math.random. Adapt to Remotion frame-driven motion and seeded randomness, documenting derivative hashes. README's blanket deterministic claim is inaccurate for these files. Each component must pass actual render gates; source count is not validated count.

Remotion runtime has its own commercial license, independent of these MIT templates: https://www.remotion.dev/license . Local noncommercial evaluation is permitted; commercial eligibility/company licensing must be resolved before production use. No license purchase or deployment in this phase. Dependencies must be pinned and their installed licenses retained. Other template repositories are excluded from this phase.

Additional source-content exclusion: quote-card.tsx embeds an attributed Steve Jobs quotation; replace the default with an original neutral testimonial and fictional demo author. Demo company wording is normalized to neutral user-editable branding. Existing font families also reference Georgia, Courier New, Impact and Arial Black as browser/system fallbacks; no corresponding licensed font binaries are supplied by upstream or copied by us.

Installed Phase2A runtime: remotion/@remotion/bundler/@remotion/renderer4.0.523 (same version, custom Remotion license retained at licenses/Remotion-4.0.523.md), tsx4.23.13 (MIT), sharp0.35.4 (Apache-2.0; native libvips LGPL), React19.3.0 (MIT). Runtime versions are pinned in root package.json/pnpm-lock.yaml. Local evaluation uses installed Chrome where available; no browser or stock media copied from RVE. FontInter5.3.0 remains OFL-1.1. This inventory distinguishes MIT template source from renderer/native dependency terms.

Native renderer audit: installed @remotion/compositor-darwin-x64@4.0.523 ships FFmpeg n7.1. Running its actual `ffmpeg -L` from the binary directory reports GPL-2.0-or-later and build flags `--enable-gpl`, libx264/libx265. Thus the Phase2A Remotion toolchain is NOT wholly permissive or LGPL-only. Template TSX source remains MIT-declared. No FFmpeg source/binary is copied into our application source tree; it is a separate installed local renderer executable invoked by Remotion. GPL allows commercial use subject to its terms; bundling/redistribution of this native tool requires its notices/corresponding source obligations. Do not reuse Phase1's LGPL-only Docker claim for this new toolchain. No production image or renderer binary distribution is performed in Phase2A.


Final Phase 2A validation: all 81 MIT-declared source components imported and frame-validated; 81 actual WebP thumbnails and three 3-second MP4 preview excerpts generated. 61 enabled, eight featured; 20 retained but disabled by curation (10 fixed illustrative metric animations, 10 fixed media-layout demos without owned-asset mappings). These are product-readiness exclusions, not code-license rejections.

Additional recorded adaptations remove wall-clock CSS transitions in sound-wave, pixel-transition and progress-steps; glitch-text overlapping RGB layers share one editable headline, and logo-glitch-reveal maps its settled logo/company/tagline as well as ghost layers. Source and derivative hashes, per-field pixel checks, fail-closed gate evidence and the 54-frame shared wrapper matrix remain in packages/video-templates. Twelve native-size effects support 16:9 only; other compositions fit their source stage into supported output formats with letterboxing. No stock/demo photo was fetched.

User-supplied local preview (2026-09-10): Create_a_realistic_second_ve.mp4 copied unchanged into apps/web/public/media/create-preview.mp4 at explicit user request. Poster derived from the same file. This asset is not sourced from RVE or covered by its MIT declaration; no additional licensing claim is made.


## Single-model MVP update — 2026-09-10
Higgsfield local adapter and @higgsfield/cli dependency removed. OpenAI Responses and OpenRouter video use the already installed httpx; no new provider SDK, media or font dependency. Official contract sources and model verification are linked in CHAT_ARCHITECTURE.md. One failed real submission used two owned-role uploads of the existing original generated ugc-review.png image, not imported stock media. Temporary Cloudflare signed-media-only access was closed after testing. No production distribution or deployment.

## Claude creative reference catalog — 2026-09-11

Six scoped MIT skill-text adaptations are vendored server-side under
`apps/api/app/creative_skills/vendor/`. Verified by GitHub REST commit resolution and
pinned raw-file downloads; no Git commands or upstream code were executed.

- [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills/tree/5b2c0007766c6a1cf1d53fd8fc73e979e0821022), commit `5b2c0007766c6a1cf1d53fd8fc73e979e0821022`: `skills/{customer-research,product-marketing,offers,ad-creative,copywriting}/SKILL.md`. MIT, © 2025 Corey Haines; original root LICENSE retained unchanged.
- [DV0x/creative-ad-agent](https://github.com/DV0x/creative-ad-agent/tree/751b9e5146604dc65049bd0f62dcbdad6212f8a3), commit `751b9e5146604dc65049bd0f62dcbdad6212f8a3`: `agent/.claude/skills/hook-methodology/SKILL.md`, adapted as `hook-method.md`. MIT, © 2025 Creative Ad Agent; original root LICENSE retained unchanged.

Only relevant planning sections are imported. Shell commands, campaign execution,
filesystem discovery/writes, arbitrary browsing, external reference loads, alternate
provider pipelines and unrelated output schemas are excluded. Attribution, factual
qualification and source-first methodology remain. Illustrative numbers are not offer
facts. Unsupported marketing uplift statistics are removed.

The [review record](audits/claude-skill-review.md),
[transformation manifest](audits/claude-skill-transformations.json), and six
`audits/claude-skill-*.diff` files identify every section selection, removal/rewrite,
original and derivative hash, and recorded per-skill approval. Review is an agent
self-review, not an independent human audit. Only reviewed enabled manifest IDs are
loadable; text is bounded, hash checked, and returned as untrusted reference data.
No images, datasets, application code, reference libraries, scripts or SDKs from these
repositories are imported.
