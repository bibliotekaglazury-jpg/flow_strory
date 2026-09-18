/** Subtitle Studio: Gemini transcript, editable timed cues, styled preview and MP4 export. */
import type { Asset, ApiError } from "./index";

export type SubtitleAspectRatio = "9:16" | "16:9";
export type SubtitleProjectStatus = "transcribing" | "ready" | "failed";
export type SubtitleExportStatus = "queued" | "rendering" | "completed" | "failed";
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
  /** Present only while a share link is live; null before sharing and after revoking. */
  shareToken: string | null;
  createdAt: string;
  updatedAt: string;
}

/** What a stranger with a share link sees: no owner, revision, or project data. */
export interface SubtitleSharedExport {
  id: string;
  outputAsset: Asset | null;
  aspectRatio: SubtitleAspectRatio;
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

/** One page of newest-first project summaries; same shape as the full project minus cues. */
export interface SubtitleProjectSummary {
  id: string;
  sourceAsset: Asset;
  status: SubtitleProjectStatus;
  aspectRatio: SubtitleAspectRatio;
  durationMs: number;
  latestExport: SubtitleExport | null;
  createdAt: string;
  updatedAt: string;
}

export interface SubtitleProjectInput {
  sourceAssetId: string;
  aspectRatio: SubtitleAspectRatio;
}

/** Every field the editor can change in one save; the server recomputes cue text from
 * word timing only when transcription itself runs — a manual edit stays authoritative. */
export interface SubtitleProjectUpdate {
  revision: number;
  aspectRatio: SubtitleAspectRatio;
  cues: SubtitleCue[];
  style: SubtitleStyle;
}

export interface SubtitleExportInput {
  revision: number;
}

export interface SubtitleService {
  create(
    input: SubtitleProjectInput,
    key: string,
  ): Promise<{ project: SubtitleProject }>;
  list(
    cursor?: string,
  ): Promise<{ projects: SubtitleProjectSummary[]; nextCursor: string | null }>;
  get(id: string): Promise<{ project: SubtitleProject }>;
  remove(id: string): Promise<void>;
  update(
    id: string,
    input: SubtitleProjectUpdate,
  ): Promise<{ project: SubtitleProject }>;
  export(
    id: string,
    input: SubtitleExportInput,
    key: string,
  ): Promise<{ export: SubtitleExport }>;
  getExport(
    id: string,
    exportId: string,
  ): Promise<{ export: SubtitleExport; pollAfterMs: number | null }>;
  share(id: string, exportId: string): Promise<{ export: SubtitleExport }>;
  unshare(id: string, exportId: string): Promise<{ export: SubtitleExport }>;
  getShared(token: string): Promise<{ export: SubtitleSharedExport }>;
}
