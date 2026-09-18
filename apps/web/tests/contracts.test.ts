import { describe, expect, it } from "vitest";
import type {
  Services,
  SubtitleAspectRatio,
  SubtitleCue,
  SubtitleExport,
  SubtitleSharedExport,
  SubtitleExportInput,
  SubtitleProject,
  SubtitleProjectInput,
  SubtitleProjectSummary,
  SubtitleProjectUpdate,
  SubtitleStyle,
  SubtitleWord,
} from "@ugc/contracts";

// Compile-time-only fixture: if a method's params or return shape ever drifts from
// packages/contracts/subtitles.ts, this file fails to typecheck before any runtime
// adapter (mock or HTTP) has to disagree about it.
const word: SubtitleWord = { id: "w1", text: "Hi", startMs: 0, endMs: 300 };
const cue: SubtitleCue = { id: "c1", startMs: 0, endMs: 300, text: "Hi", words: [word] };
const style: SubtitleStyle = {
  preset: "modern",
  position: "bottom",
  size: "medium",
  safeArea: true,
  textColor: "#FFFFFF",
  highlightColor: "#C9FF27",
};
const asset = {
  id: "a1",
  role: "source_video" as const,
  kind: "video" as const,
  mimeType: "video/mp4",
  fileName: "clip.mp4",
  sizeBytes: 1024,
  url: "https://example.com/a1",
  urlExpiresAt: null,
  width: 1080,
  height: 1920,
  durationSeconds: 12,
  createdAt: "2026-09-14T00:00:00Z",
};
const project: SubtitleProject = {
  id: "p1",
  sourceAsset: asset,
  status: "ready",
  aspectRatio: "9:16",
  language: "en",
  durationMs: 12000,
  revision: 1,
  cues: [cue],
  style,
  latestExport: null,
  error: null,
  createdAt: "2026-09-14T00:00:00Z",
  updatedAt: "2026-09-14T00:00:00Z",
};
const summary: SubtitleProjectSummary = {
  id: project.id,
  sourceAsset: asset,
  status: project.status,
  aspectRatio: project.aspectRatio,
  durationMs: project.durationMs,
  latestExport: null,
  createdAt: project.createdAt,
  updatedAt: project.updatedAt,
};
const exported: SubtitleExport = {
  id: "e1",
  status: "completed",
  progress: 100,
  outputAsset: asset,
  error: null,
  shareToken: null,
  createdAt: "2026-09-14T00:00:00Z",
  updatedAt: "2026-09-14T00:00:00Z",
};
const shared: SubtitleSharedExport = {
  id: exported.id,
  outputAsset: asset,
  aspectRatio: project.aspectRatio,
};
const ratio: SubtitleAspectRatio = "16:9";
const createInput: SubtitleProjectInput = { sourceAssetId: asset.id, aspectRatio: ratio };
const updateInput: SubtitleProjectUpdate = {
  revision: project.revision,
  aspectRatio: project.aspectRatio,
  cues: project.cues,
  style: project.style,
};
const exportInput: SubtitleExportInput = { revision: project.revision };

const fixture: Services["subtitleProjects"] = {
  async create() {
    return { project };
  },
  async list() {
    return { projects: [summary], nextCursor: null };
  },
  async get() {
    return { project };
  },
  async remove() {},
  async update() {
    return { project };
  },
  async export() {
    return { export: exported };
  },
  async getExport() {
    return { export: exported, pollAfterMs: null };
  },
  async share() {
    return { export: { ...exported, shareToken: "tok-1" } };
  },
  async unshare() {
    return { export: exported };
  },
  async getShared() {
    return { export: shared };
  },
};

describe("subtitleProjects contract fixture", () => {
  it("exercises every method with the full request/response shape", async () => {
    expect((await fixture.create(createInput, "key-1")).project.id).toBe("p1");
    expect((await fixture.list()).projects).toHaveLength(1);
    expect((await fixture.get(project.id)).project.status).toBe("ready");
    expect(await fixture.remove(project.id)).toBeUndefined();
    expect((await fixture.update(project.id, updateInput)).project.revision).toBe(1);
    expect((await fixture.export(project.id, exportInput, "key-2")).export.status).toBe(
      "completed",
    );
    expect((await fixture.getExport(project.id, exported.id)).export.id).toBe("e1");
    expect((await fixture.share(project.id, exported.id)).export.shareToken).toBe("tok-1");
    expect((await fixture.unshare(project.id, exported.id)).export.shareToken).toBeNull();
    expect((await fixture.getShared("tok-1")).export.id).toBe("e1");
  });
});
