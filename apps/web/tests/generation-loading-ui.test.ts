import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const previewSource = readFileSync(
  new URL("../features/create/preview.tsx", import.meta.url),
  "utf8",
);
const workspaceSource = readFileSync(
  new URL("../features/create/workspace.tsx", import.meta.url),
  "utf8",
);

describe("generation loading UI", () => {
  // The loader belongs inside the video frame: as a full-stage overlay it stretched to
  // the height of the whole creation block instead of a vertical video.
  it("shows the fluid state inside the preview frame, not over the whole stage", () => {
    expect(previewSource).not.toContain("Cancel generation");
    expect(previewSource).not.toContain("Generation progress");
    expect(previewSource).not.toContain("<Video");
    expect(previewSource).not.toContain(
      "Usually takes a few minutes. You can leave this page.",
    );
    expect(previewSource).not.toContain(
      "Analysing your product and choosing a creative direction.",
    );
    expect(workspaceSource).not.toContain("creation-process-overlay");
    expect(previewSource).toContain("<FluidLoader />");
    expect(previewSource).toContain("aspectRatio");
    expect(previewSource).toContain("Creating your concept…");
    expect(previewSource).toContain("Generating your video…");
  });
});
