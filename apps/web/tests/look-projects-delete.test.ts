import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const studio = readFileSync(
  new URL("../features/try-on/product-look-studio.tsx", import.meta.url),
  "utf8",
);
const styles = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

describe("try-on look history delete", () => {
  it("deletes one look, and Select mode bulk-deletes the rest, ownership-checked server-side", () => {
    expect(studio).toContain("lookProjects.remove(id)");
    expect(studio).toContain("deleteSelectedProjects");
    expect(studio).toContain("window.confirm(");
    expect(studio).toContain("Delete this look");
    expect(studio).toContain("Delete selected");
    // Deleting the open project clears the workspace instead of pointing at a gone folder.
    expect(studio).toContain("if (projectId === id) setProjectId(null)");
    expect(styles).toContain(".look-project-delete");
    expect(styles).toContain(".look-bulk-delete");
  });
});
