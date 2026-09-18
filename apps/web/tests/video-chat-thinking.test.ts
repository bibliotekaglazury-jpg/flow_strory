import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const chat = readFileSync(
  new URL("../features/chat/video-chat.tsx", import.meta.url),
  "utf8",
);

describe("chat thinking indicator", () => {
  it("shows a live elapsed timer instead of a static line while the director works", () => {
    expect(chat).toContain("elapsedSeconds");
    expect(chat).toContain("setInterval");
    expect(chat).toContain("thinkingStage");
    expect(chat).not.toContain("Preparing your reply…");
  });
});
