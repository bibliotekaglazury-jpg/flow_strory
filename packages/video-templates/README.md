# Audited RVE render package

Source commit: `6209b724798e48ff395f8df1a6fa2d26082372b5` only.
Read NOTICE.md and upstream README for attribution and separate runtime licensing.

From repository root:

```sh
pnpm templates:rve:import
# Or supply an existing audited checkout:
# pnpm templates:rve:import /path/to/audited/git/checkout
pnpm templates:rve:test
pnpm templates:rve:validate
pnpm templates:rve:stats
node --import tsx scripts/templates/render-rve.ts --template rve_animated_text --input /tmp/input.json --output /tmp/result.mp4 --duration 15 --aspect-ratio 9:16
```

The default import clones only the audited source repository into ignored
`.cache/rve-source`, disables Git hooks, and checks out the pinned commit.
Import verifies checkout commit and every source hash against the pre-copy audit,
discovers all TSX exports, regenerates imports, AST text mappings and manifests,
and resets every record to disabled. Revalidate after import. `mapping-audit.json`
records each actual source-to-input mapping; schema controls exist only where
rendered source consumes the field. Charts with fixed illustrative data remain
curation-disabled until an editable metrics adapter exists. Original motion/
layout code remains in src/imported, with deterministic corrections recorded.

Validation typechecks all components, validates schema/defaults and registration,
renders early/terminal frames for every component at15s/16:9 and verifies that
custom inputs change actual pixels. It creates real WebP thumbnails, checks the
shared wrapper across all aspect/duration combinations using representative text,
image and duration-sensitive effect components, then renders three3-second MP4
preview excerpts. Full job output durations remain15/20/30seconds. Per-template
evidence and the representative wrapper matrix record exactly what was rendered. Browser errors
or exact duplicate thumbnails disable records. `manifest.json` is server-only;
`public-manifest.json` omits renderer/source/validation internals.

Each animation keeps its 1280×720 composition stage. The12effects reading
output width/height directly are restricted to16:9 to preserve their geometry. Portrait/square outputs fit
that stage, centered with dark letterboxing, preserving content without cropping.
Durations are 15/20/30 seconds at30fps; source animations may settle into a static
final state. This is not a responsive redesign of81source templates.

CLI input is normalized JSON. Media is a trusted worker-resolved absolute local
path to a regular PNG/JPEG/WebP (10MB/40MP max); the renderer embeds verified bytes.
Remote URLs and caller-provided data URLs are rejected. Public requests must use
owned asset IDs and backend ownership validation. Output MP4 and sibling WebP
are written only to worker-selected paths. The runtime uses the Remotion-managed Chrome Headless Shell (downloaded during
local setup); set REMOTION_BROWSER_EXECUTABLE for a different managed browser. Browser
launch/local HTTP serving needs permission outside restrictive execution sandboxes.

The catalog web server must serve `public/template-media` at `/template-media`.
The neutral SVG is original artwork; licensed Inter files and OFL notice are local.
No third-party photos, logo downloads, or external font requests are required.

`remotion.defaultProps` contains normalized wrapper preview defaults. For the
three image components, private `propSchema` describes the mapped source
`imageUrl`; the public `inputSchema` describes owned-asset `productImage`.
