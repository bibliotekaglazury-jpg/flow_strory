import { describe, expect, it } from "vitest";
import type { Generation } from "@ugc/contracts";
import { developerPreviewGeneration } from "../services/developer-generation-preview";

const base: Generation = {
  id: "real-job",
  userId: "demo-user",
  templateId: "product_demo",
  model: "auto",
  provider: null,
  status: "queued",
  progress: null,
  prompt: "Real prompt",
  duration: 15,
  aspectRatio: "9:16",
  inputAssets: [],
  outputAssets: [],
  creditsEstimated: 10,
  creditsCharged: 0,
  error: null,
  createdAt: "2026-09-12T10:00:00Z",
  updatedAt: "2026-09-12T10:00:00Z",
};

describe("developerPreviewGeneration", () => {
  it("previews every state without mutating the real generation", () => {
    expect(developerPreviewGeneration("live", base)).toBe(base);

    const queued = developerPreviewGeneration("queued", base)!;
    const generating = developerPreviewGeneration("generating", base)!;
    const completed = developerPreviewGeneration("completed", base)!;
    const failed = developerPreviewGeneration("failed", base)!;

    expect(queued.status).toBe("queued");
    expect(queued.progress).toBeNull();
    expect(generating.status).toBe("generating");
    expect(generating.progress).toBeNull();
    expect(completed.status).toBe("completed");
    expect(completed.outputAssets[0]).toMatchObject({
      role: "output_video",
      url: "/demo-15-9x16.mp4",
    });
    expect(failed.status).toBe("failed");
    expect(failed.error?.code).toBe("DEVELOPER_PREVIEW_FAILURE");
    expect(base).toMatchObject({
      id: "real-job",
      status: "queued",
      outputAssets: [],
      error: null,
    });
  });

  it("can preview a state before any generation exists", () => {
    expect(developerPreviewGeneration("generating", null)).toMatchObject({
      id: "developer-preview",
      status: "generating",
      aspectRatio: "9:16",
    });
  });
});
