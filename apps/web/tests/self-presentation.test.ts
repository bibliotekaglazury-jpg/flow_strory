import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { templateArtwork } from "../services/template-visuals";

const workspace = readFileSync(
  new URL("../features/create/workspace.tsx", import.meta.url),
  "utf8",
);

describe("self-presentation", () => {
  it("offers the template when only a person photo is supplied", () => {
    expect(workspace).toContain("const personOnly =");
    expect(workspace).toContain('c.selectTemplate("self_presentation")');
    expect(workspace).toContain("Use Self-presentation");
  });

  it("has artwork on its style card", () => {
    expect(templateArtwork({ id: "self_presentation", thumbnailUrl: "" })).toBeTruthy();
  });
});
