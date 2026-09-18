import type { Generation } from "@ugc/contracts";

const PREFERRED_REAL_VIDEO_TIMESTAMPS = [
  "2026-09-11T18:32:47",
  "2026-09-11T20:32:47",
];

function hasOutputVideo(generation: Generation) {
  return generation.outputAssets.some(
    (asset) =>
      asset.role === "output_video" && asset.kind === "video" && asset.url,
  );
}

export function recentCompletedVideos(history: Generation[]) {
  const completedVideos = history.filter(
    (generation) => generation.status === "completed" && hasOutputVideo(generation),
  );
  const baseline = completedVideos.find((generation) =>
    PREFERRED_REAL_VIDEO_TIMESTAMPS.some((timestamp) =>
      generation.createdAt.startsWith(timestamp),
    ),
  );
  if (!baseline) return completedVideos;
  const baselineTime = Date.parse(baseline.createdAt);
  return completedVideos.filter(
    (generation) =>
      generation.id === baseline.id || Date.parse(generation.createdAt) > baselineTime,
  );
}
