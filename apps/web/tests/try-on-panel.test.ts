import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const panel = readFileSync(
  new URL("../features/create/try-on-panel.tsx", import.meta.url),
  "utf8",
);
const hook = readFileSync(
  new URL("../hooks/use-creation.ts", import.meta.url),
  "utf8",
);
const slots = readFileSync(
  new URL("../features/create/workspace.tsx", import.meta.url),
  "utf8",
);

describe("try-on", () => {
  it("opens itself for a look instead of waiting for a typed chat instruction", () => {
    expect(hook).toContain("!!draft.inputAssets.personImageId && lookPieces >= 2");
    expect(hook).toContain("open: true");
    // Closing has to stick until the look itself changes, or it would fight the user.
    expect(hook).toContain("dismissed");
    expect(panel).toContain("c.closeTryOn");
  });

  it("sends a fresh idempotency key so a retry cannot be charged twice", () => {
    expect(hook).toContain("idempotencyKey: crypto.randomUUID()");
  });

  it("offers the video only after a photo exists, through the existing flow", () => {
    expect(panel).toContain("Generate video with this look");
    expect(panel.indexOf("photo &&")).toBeLessThan(
      panel.indexOf("Generate video with this look"),
    );
    // The panel must not reach for a video API of its own.
    expect(panel).not.toContain("generateVideo");
  });

  it("lets a whole look be picked in one go", () => {
    expect(slots).toContain("multiple");
    expect(slots).toContain("c.addItems");
    expect(slots).not.toContain("3 - filled.length");
  });
});
