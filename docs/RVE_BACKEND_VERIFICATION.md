# RVE Phase 2A backend integration

The existing Template API, quotes, generations, durable database jobs, private assets, history and append-only credit ledger are extended. No new provider abstraction, queue, authentication or billing architecture is introduced.

- Catalog source: `packages/video-templates/manifest.json`, plus the existing eight generative templates. Public allowlist excludes source paths, hashes, component configuration and Remotion implementation details. Legacy `thumbnailUrl` and `available` aliases remain.
- `/api/templates` applies AND filters for search, category, templateType, aspectRatio, duration, inputType, useCase, featured and enabled. Public requests default to `enabled=true`; an explicit `enabled=false` selects unavailable records. Category/use-case aliases are case-insensitive URL slugs. Duration supports `up-to-15`, `20`, `30-plus`, or an exact numeric string. Input filters distinguish product-image, product-url, person-image, existing-video, images and text-only. Twenty-two shared fixture vectors are consumed by backend and frontend tests.
- `normalizedInputs` is optional. Remotion requests require no generated prompt or product URL/image unless their schema requests it. Generative requirements remain intact. Quote fingerprints include normalized inputs; changing them invalidates the quote.
- Input schemas enforce known string properties, required fields, minimum/maximum lengths and enumerations. Media properties accept only current-user owned uploaded assets with the appropriate media kind. URLs, local paths and another user's IDs are rejected as media. Workers copy validated storage objects into temporary local files; no client-controlled media URL reaches the renderer.
- `render_only` is a server-only cost class/selected execution mode. `RENDER_ONLY_CREDITS_PER_SECOND` defaults to 1 development credit per second, independent of AI pricing. Existing reserve/finish ledger operations handle admission, completion and refunds.
- Worker invokes `node --import tsx scripts/templates/render-rve.ts` from verified repository root. `RENDER_NODE_PATH` configures the executable. `RENDER_TIMEOUT_SECONDS` defaults to 600; the process group is killed on timeout. Lease extends to timeout + 180 seconds, and publication requires the same owner and a nonterminal generation. Safe deterministic retries after crashed leases have no remote charge.
- Cancellation, including an in-flight local render, refunds through the existing ledger. Returning output from a cancelled/stale worker is discarded before storage publication. Temporary input/output files are cleaned up. Generative cancellation restrictions are unchanged.
- Renderer MP4 and WebP thumbnail enter existing media validation and private Storage/Asset/Output records. History returns those owned assets with signed links.

## Verification

Final code passed **88 backend tests in 14.07 seconds** with PostgreSQL enabled; the single real Remotion test was run separately to avoid repeating a costly full render. That genuine pipeline test also **passed**, in **563.16 seconds**, within the configured 600-second subprocess timeout. Combined verified suite: **89 passing tests**. The two existing Starlette/AnyIO dependency warnings remain. Ruff passed.

Commands from `apps/api`:

```sh
export DATABASE_URL=postgresql+psycopg://ugc@127.0.0.1:55432/ugc
export RUN_POSTGRES_TESTS=1
export FFMPEG_PATH=/Users/stas/Documents/UGC/apps/api/.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-x86_64-v7.1
.venv/bin/python -m pytest -q -k 'not remotion_real'

# Same environment; separately executed actual browser/Remotion render:
.venv/bin/python -m pytest -q tests/test_postgres_integration.py::test_remotion_real_worker_storage_and_history
.venv/bin/ruff check app tests
```

The PostgreSQL cluster and external FFmpeg are the previously authorized local tools, not newly introduced application dependencies. No paid calls, production changes or deployment occurred.

The actual test submitted an enabled `rve_animated_list` through estimate → matching persisted quote → queued generation/reservation → durable worker → real Node/Remotion MP4 → existing private Storage/Asset/Output → completed job/settlement → signed download and history. The actual artifact and nonsecret receipt are saved as `docs/verification/rve-job.mp4`, `rve-job.webp` and `rve-job.json`. This template has no input fields; it proves the rendering pipeline, not custom text propagation, which is separately covered by the importer's corrected render gate.

Additional tests cover all 22 shared filter vectors, unknown/oversized schema inputs, arbitrary media URLs/paths and foreign assets, quote changes, exact idempotency, provider bypass, in-flight cancellation, failure refund, stale worker ownership and changed queued definitions. Injected late worker bytes are deliberately invalid, proving terminal and ownership checks prevent storage publication before decoding.

Definition provenance is bound into quotes and accepted job snapshots using version, adapted source hash, schema, composition/default settings and supported formats/durations. Changed definitions invalidate unused quotes or fail queued jobs with a refund. Preview paths, featured status and validation timestamps do not alter the definition fingerprint. Accepted owned media IDs are persisted separately; status/history reads use those immutable IDs rather than the current schema. Completed/failed history and changed-schema failure endpoints are tested.

Updated API and worker run on loopback with the reviewed code; `/health/ready` returns 200. Development identity remains `development-user`. API access logging stays disabled so signed asset query strings are not written to access logs.
