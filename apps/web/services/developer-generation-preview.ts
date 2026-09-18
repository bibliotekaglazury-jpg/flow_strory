import type { Asset, Generation, GenerationStatus } from "@ugc/contracts";

export type DeveloperGenerationPreviewState = "live" | GenerationStatus;

const timestamp = "2026-01-01T00:00:00.000Z";

function emptyGeneration(): Generation {
  return {
    id: "developer-preview",
    userId: "developer",
    templateId: "product_demo",
    model: "auto",
    provider: null,
    status: "queued",
    progress: null,
    prompt: null,
    duration: 15,
    aspectRatio: "9:16",
    inputAssets: [],
    outputAssets: [],
    creditsEstimated: 0,
    creditsCharged: 0,
    error: null,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
}

function previewOutput(generation: Generation): Asset {
  const [width, height] =
    generation.aspectRatio === "9:16"
      ? [360, 640]
      : generation.aspectRatio === "1:1"
        ? [480, 480]
        : [640, 360];
  return {
    id: "developer-preview-output",
    role: "output_video",
    kind: "video",
    mimeType: "video/mp4",
    fileName: "developer-preview.mp4",
    sizeBytes: 0,
    url: `/demo-${generation.duration}-${generation.aspectRatio.replace(":", "x")}.mp4`,
    urlExpiresAt: null,
    width,
    height,
    durationSeconds: generation.duration,
    createdAt: timestamp,
  };
}

export function developerPreviewGeneration(
  state: DeveloperGenerationPreviewState,
  generation: Generation | null,
): Generation | null {
  if (state === "live") return generation;
  const preview = { ...(generation ?? emptyGeneration()) };
  preview.status = state;
  preview.progress = state === "completed" ? 100 : null;
  preview.outputAssets = state === "completed" ? [previewOutput(preview)] : [];
  preview.error =
    state === "failed"
      ? {
          code: "DEVELOPER_PREVIEW_FAILURE",
          message: "Developer preview of a failed generation.",
          retryable: true,
        }
      : null;
  return preview;
}
