import { describe, expect, it } from "vitest";
import type { Generation } from "@ugc/contracts";
import { recentCompletedVideos } from "../services/history-filter";

function generation(id: string, createdAt: string): Generation {
  return {
    id,
    userId: "user",
    templateId: "product_demo",
    model: "auto",
    provider: null,
    status: "completed",
    progress: 100,
    prompt: "prompt",
    duration: 15,
    aspectRatio: "9:16",
    inputAssets: [],
    outputAssets: [
      {
        id: `video-${id}`,
        role: "output_video",
        kind: "video",
        mimeType: "video/mp4",
        fileName: `${id}.mp4`,
        sizeBytes: 1,
        url: `/media/${id}.mp4`,
        urlExpiresAt: null,
        width: 720,
        height: 1280,
        durationSeconds: 15,
        createdAt,
      },
    ],
    creditsEstimated: 10,
    creditsCharged: 10,
    error: null,
    createdAt,
    updatedAt: createdAt,
  };
}

describe("recentCompletedVideos", () => {
  it("keeps the selected Wan baseline and automatically includes newer videos", () => {
    const newVideo = generation("new", "2026-09-12T15:00:00.000Z");
    const wanBaseline = generation("wan", "2026-09-11T20:32:47.000Z");
    const oldLegacyVideo = generation("legacy", "2026-09-11T20:24:10.000Z");

    expect(
      recentCompletedVideos([newVideo, wanBaseline, oldLegacyVideo]).map(
        ({ id }) => id,
      ),
    ).toEqual(["new", "wan"]);
  });
});
