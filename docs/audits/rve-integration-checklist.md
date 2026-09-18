# Phase2A integration review checklist

- Source metadata stays private; public catalog contains filter/input data and safe preview paths.
- Generative prompt provenance/idempotency/quote fingerprints remain compatible; missing normalizedInputs defaults do not invalidate old snapshots.
- Render input schemas expose only controls mapped to output; ignored fields must not masquerade as supported.
- Media input strings are owned asset IDs at API; renderer receives bounded local files, never remote URLs from user data.
- Duration/ratio constraints checked by backend and CLI; manifest enabled entries carry render evidence.
- Rendering happens inside existing worker with lease/cancellation/timeout behavior; output ingestion and ledger settlement remain atomic/once-only.
- Same search/filter fixtures cover backend and frontend; URL back/forward restores search and all filters.
- Create featured subset; /templates complete catalog. Empty filters clear once and count is honest.
- Enabled thumbnails are actual frames; failed/duplicate entries stay disabled. No imported template result replaced with simulation fixture.
- Default/source transformations and font/media exclusions are auditable; importer repeatable against pinned clean checkout.
- Render preview paths are available in both browsermock and connectedAPI; no implementation labels in normal UI.
