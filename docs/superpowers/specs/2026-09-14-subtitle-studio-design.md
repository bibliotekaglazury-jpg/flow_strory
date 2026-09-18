# Subtitle Studio Design Specification

**Status:** Approved visual direction; ready for split frontend/backend implementation  
**Date:** 2026-09-14  
**Visual source:** [`docs/references/subtitle-studio/approved-editor-9x16.png`](../../references/subtitle-studio/approved-editor-9x16.png)  
**Owners:** Codex — frontend and browser preview. Claude — API, Gemini transcription, persistence, jobs, storage, and server export.

## Goal

Add a separate **Subtitle Studio** where an authenticated Forma user uploads or selects a video, receives an editable timed transcript, previews styled captions, and exports a new MP4. The same editor supports vertical `9:16` and horizontal `16:9` output. Every project and successful export remains available after reload and can be reopened from Library.

## Product decisions

- One transcription provider in this phase: Gemini paid tier behind a server-only adapter.
- Browser preview: `@remotion/player` `4.0.523`.
- Caption normalization and pagination: `@remotion/captions` `4.0.523`.
- Final MP4: existing server-side Remotion toolchain and storage abstraction.
- VoiceStudio, dubbing, translation, voice cloning, speaker replacement, collaborative editing, mobile-native editing, and a general-purpose video timeline are out of scope.
- Credit pricing is outside this experiment. The frontend must not invent or display a price. Any later charging must be added through the existing quote and ledger system before production enablement.

## Entry and flow

Add **Subtitles** to the sidebar between Try On and Templates. `/subtitles` has one persistent project surface with these states:

1. **Empty:** upload a source video or choose one owned video from Library.
2. **Uploading:** real byte progress and a cancel-upload action.
3. **Transcribing:** the source preview is available; editor controls are disabled; show an indeterminate transcription state without fabricated percentage or completion time.
4. **Ready/editing:** selected visual layout with player, transcript, styles, and timeline.
5. **Saving:** edits are locally optimistic; top status reads `Saving…` and then `Saved` after the server confirms the current revision.
6. **Exporting:** preview remains usable; the primary button shows `Exporting…`; leaving the page is safe.
7. **Completed:** show `Download video` and keep `Export again` available after further edits.
8. **Failed:** preserve all confirmed edits, show the server error beside the failed operation, and offer `Retry` only when the error is retryable.

The browser stores only an unsaved working copy. The backend is the source of truth for projects, transcript revisions, and exports.

## Approved editor layout

The selected desktop composition is the first generated mockup:

- Dark Forma shell and sidebar around a broad white editor workspace.
- Header: Back, `Subtitle Studio`, saved state, `9:16`/`16:9` switch, and one lime primary action.
- Main row: player on the left, transcript and caption styling on the right.
- Bottom row: waveform, timed caption blocks, and playhead across the full workspace.
- No phone bezel, social counters, templates, analytics, or unrelated creation controls.

For `9:16`, the player column occupies about 42% and the editor column 58%. The video uses `object-fit: contain`; the full source frame stays visible. For `16:9`, the player column grows to about 58% and the inspector becomes a narrower 42% column. The timeline remains full width in both modes. Below 1100 px, the player appears above the transcript; below 720 px, the timeline becomes horizontally scrollable and style controls collapse into a drawer. This is a responsive adaptation, not a separate mobile editor design.

Switching aspect ratio changes the composition canvas and export setting. It never stretches the source video. If source and output ratios differ, the source is contained on a neutral near-black canvas.

## Editing behavior

- Clicking a transcript row seeks to its start and selects its caption block.
- Clicking a caption block selects the matching transcript row.
- Player time updates the active row and scrolls it into view without stealing keyboard focus.
- Transcript text is directly editable. Empty cues are rejected before save.
- `Split` divides the selected cue at the current playhead. It is enabled only when the playhead is inside the cue and both resulting cues are at least 250 ms.
- `Merge` joins the selected cue with the next cue. It is disabled for the last cue.
- Cue boundaries may be dragged on the timeline. Cues must be ordered, non-overlapping, and at least 250 ms long.
- Undo/redo covers transcript text, cue boundaries, split/merge, style, position, and aspect ratio for the current browser session.
- Autosave is debounced by 700 ms. Save requests include the last confirmed `revision`; a stale revision returns `409 REVISION_CONFLICT`, after which the UI reloads the confirmed project and offers to restore the local draft.

## Caption styles

Ship four presets only:

1. `modern` — white bold text on a dark rounded background with lime active words.
2. `classic` — white medium text with a subtle dark stroke.
3. `impact` — uppercase condensed white text with lime word blocks.
4. `editorial` — white serif text with restrained shadow.

Editable controls in this phase: preset, bottom/center/top position, small/medium/large size, safe-area toggle, text color, and highlight color. The preview and exported composition consume the same serializable `SubtitleStyle`; there must not be a separate CSS-only preview implementation.

## Shared contract

Add `packages/contracts/subtitles.ts` and re-export it from `packages/contracts/index.ts`.

```ts
export type SubtitleAspectRatio = "9:16" | "16:9";
export type SubtitleProjectStatus =
  | "transcribing"
  | "ready"
  | "failed";
export type SubtitleExportStatus =
  | "queued"
  | "rendering"
  | "completed"
  | "failed";
export type SubtitlePreset = "modern" | "classic" | "impact" | "editorial";

export interface SubtitleWord {
  id: string;
  text: string;
  startMs: number;
  endMs: number;
}

export interface SubtitleCue {
  id: string;
  startMs: number;
  endMs: number;
  text: string;
  words: SubtitleWord[];
}

export interface SubtitleStyle {
  preset: SubtitlePreset;
  position: "top" | "center" | "bottom";
  size: "small" | "medium" | "large";
  safeArea: boolean;
  textColor: string;
  highlightColor: string;
}

export interface SubtitleExport {
  id: string;
  status: SubtitleExportStatus;
  progress: number | null;
  outputAsset: Asset | null;
  error: ApiError | null;
  createdAt: string;
  updatedAt: string;
}

export interface SubtitleProject {
  id: string;
  sourceAsset: Asset;
  status: SubtitleProjectStatus;
  aspectRatio: SubtitleAspectRatio;
  language: string | null;
  durationMs: number;
  revision: number;
  cues: SubtitleCue[];
  style: SubtitleStyle;
  latestExport: SubtitleExport | null;
  error: ApiError | null;
  createdAt: string;
  updatedAt: string;
}
```

Extend `Services` with `subtitleProjects.create/list/get/update/export/getExport`. The HTTP and mock adapters implement identical behavior.

## API contract

All routes require the existing authenticated identity and enforce `user_id` ownership.

- `POST /api/subtitle-projects`, header `Idempotency-Key`, body `{sourceAssetId, aspectRatio}` → `202 {project}`. The same user/key/body returns the same project before another Gemini call. Same key with another body returns `409 IDEMPOTENCY_CONFLICT`.
- `GET /api/subtitle-projects?cursor=&limit=` → newest-first summaries.
- `GET /api/subtitle-projects/{id}` → `{project}`.
- `PATCH /api/subtitle-projects/{id}`, body `{revision, aspectRatio, cues, style}` → `{project}` with incremented revision.
- `POST /api/subtitle-projects/{id}/exports`, header `Idempotency-Key`, body `{revision}` → `202 {export}`. The export stores an immutable snapshot of the referenced revision.
- `GET /api/subtitle-projects/{id}/exports/{exportId}` → `{export, pollAfterMs}`; polling stops for terminal states.

Validation:

- Source asset must be an owned video with role `source_video` or `output_video`.
- Supported source duration: 1 second through 30 minutes. Existing upload size and MIME validation remain authoritative.
- Project aspect ratio is only `9:16` or `16:9`.
- Cue times are integer milliseconds, monotonic, non-overlapping, within source duration, and at least 250 ms.
- Hex colors use `#RRGGBB`; preset and style values are enums.
- The server recomputes cue text from normalized word text when Gemini returns word timing. Manual text edits remain authoritative after transcription.

## Backend design — Claude owner

Create a focused `apps/api/app/subtitles/` package containing routes, schemas, service, Gemini adapter, and worker operations. Persist projects and immutable exports in new tables. Store cues and style as JSON because each edit replaces one small document and no cross-project cue query is required.

`subtitle_projects` stores user, source asset, status, aspect ratio, language, duration, revision, cues, style, idempotency key/hash, error, and timestamps. `subtitle_exports` stores project, user, source revision, immutable snapshot, status, progress, output asset, idempotency key/hash, error, and timestamps. Add a durable `subtitle_jobs` table using the same lease/retry semantics as `generation_jobs`; job kinds are `transcribe` and `render`.

The Gemini adapter receives extracted audio, requests structured word timestamps, validates them, and normalizes them into cues. Provider identifiers stay server-side. Missing or invalid word timings cause a retryable transcription failure; the server must not invent timings.

The render job invokes one new Remotion composition with the source video, aspect ratio, immutable cue/style snapshot, and existing signed media access. Successful MP4 and thumbnail assets use the existing storage abstraction under `users/{userId}/subtitle-projects/{projectId}/exports/{exportId}/`. Only database references are used to reopen a project; no client-local identifier is authoritative.

## Frontend design — Codex owner

Create the `/subtitles` route as small state-focused components: entry/import, editor header, video preview, transcript editor, caption style inspector, and timeline. A `useSubtitleProject` controller owns polling, selection, autosave, revision conflicts, undo/redo, and export state. Presentation components receive serializable project data and callbacks and never call Gemini or inspect provider metadata.

Use the shared Remotion caption composition inside `@remotion/player` so browser preview and server export render the same style. Use accessible native controls or existing UI primitives for buttons, selects, toggles, and text editing. All icon-only controls need labels and tooltips; keyboard focus must remain visible.

Library adds a `Subtitles` filter and shows projects/exports owned by the current user. Clicking a project reopens `/subtitles/{id}`. A completed export can be downloaded again using its output asset URL.

## Error and recovery rules

- Upload failure: remain on the entry state with the selected local file and explicit retry.
- Transcription failure: keep the project and source video; retry uses a new job but the same project.
- Save conflict: never overwrite a newer server revision silently.
- Export failure: keep the transcript and style; allow retry with a new idempotency key.
- Expired asset URLs: fetch the project/export again to receive refreshed signed URLs.
- Page reload during transcription or export: restore the project by route id and resume polling.
- Navigation away: do not show a blocking confirmation after the latest revision is confirmed.

## Acceptance criteria

- A user can upload/select an owned video, receive Gemini captions, edit them, preview them, and export MP4.
- Vertical and horizontal projects preview and export without stretching or cropping the source.
- Preview and final render match for all four presets at the same timestamp.
- Every project survives reload; every completed export is available in Library.
- Repeating create/export with the same idempotency key does not call Gemini/render twice or create duplicate assets.
- Alice cannot read, modify, export, or download Bob's projects or assets.
- Keyboard editing, focus order, error messaging, disabled states, and reduced-motion behavior are verified.
- No provider key or Gemini metadata reaches browser bundles or API responses.

## Verification evidence

Frontend completion requires desktop captures at `1440x1024` for both `9:16` and `16:9`, plus responsive captures at `390x844`. Compare the `9:16` capture with the approved mockup and record deviations in `docs/VERIFICATION.md`. Backend completion requires focused ownership, idempotency, revision-conflict, provider-normalization, job-retry, persistence, and render tests. Paid Gemini testing is a separate explicitly authorized operation; automated tests use a fake provider.
