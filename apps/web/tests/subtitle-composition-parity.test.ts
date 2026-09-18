import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const web = readFileSync(
  new URL("../features/subtitles/subtitle-composition.tsx", import.meta.url),
  "utf8",
);
const server = readFileSync(
  new URL(
    "../../../packages/video-templates/src/subtitles/subtitle-composition.tsx",
    import.meta.url,
  ),
  "utf8",
);

function body(source: string) {
  const start = source.indexOf("// shared-composition:start");
  const end = source.indexOf("// shared-composition:end");
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return source.slice(start, end);
}

describe("subtitle composition parity", () => {
  it("renders the browser preview and the server export from identical code", () => {
    // The Player and the renderer live in different packages; this keeps them in lockstep.
    expect(body(web)).toBe(body(server));
  });

  it("keeps the caption background on the inline words so a highlight cannot overflow it", () => {
    expect(body(web)).toContain('boxDecorationBreak: "clone"');
    expect(body(web)).toMatch(/<span\s+style=\{\{\s+background: preset === "modern"/);
  });

  it("separates words with real spaces so long captions can wrap inside the picture", () => {
    expect(body(web)).toContain('{index > 0 ? " " : null}');
    expect(body(web)).not.toContain("marginRight");
  });
});
