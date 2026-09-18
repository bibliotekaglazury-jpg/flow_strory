import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const collections = readFileSync(
  new URL("../features/create/collections.tsx", import.meta.url),
  "utf8",
);
const library = readFileSync(new URL("../app/library/page.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

describe("video library delete", () => {
  it("the Library page wires bulk delete into Collections, not the homepage teaser", () => {
    expect(collections).toContain("onDelete?: (ids: string[]) => Promise<void>");
    expect(library).toContain("generations.remove(id)");
    expect(library).toContain("onDelete={remove}");
  });

  it("offers Select mode with a per-card delete button and a bulk delete bar", () => {
    expect(collections).toContain("Delete this video");
    expect(collections).toContain("Delete selected");
    expect(collections).toContain("window.confirm(");
    // Clicking the video thumbnail in select mode toggles selection, like Subtitle Studio's history.
    expect(collections).toContain("onToggleSelect?.(generation.id)");
    expect(styles).toContain(".history-select-toggle");
    expect(styles).toContain(".history-bulk-delete");
  });
});
