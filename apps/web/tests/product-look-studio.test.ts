import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const studio = readFileSync(
  new URL("../features/try-on/product-look-studio.tsx", import.meta.url),
  "utf8",
);
const styles = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

describe("product look studio", () => {
  it("uploads real assets instead of keeping local blob previews", () => {
    expect(studio).toContain("assets.uploadMany(files)");
    expect(studio).toContain('assets.upload(file, "person", "try_on")');
    expect(studio).not.toContain("URL.createObjectURL(file)");
  });

  it("generates photos through the try-on endpoint with a fresh key per shot", () => {
    expect(studio).toContain("tryOn.preview(");
    expect(studio).toContain("idempotencyKey: crypto.randomUUID()");
    // Every angle after the first re-shoots the approved front photo, so the set matches.
    expect(studio).toContain("shoot(project.id, angle.id, front.id)");
  });

  it("keeps every generation in its own project folder that survives a reload", () => {
    // A new folder per generation, photos saved into it, folders reloaded from the API.
    expect(studio).toContain("lookProjects.create(");
    expect(studio).toContain("lookProjects.list()");
    expect(studio).toContain("lookProjects.get(id)");
    expect(studio).toContain("projectId,");
  });

  it("creates video through the existing chat, quote and generation flow", () => {
    expect(studio).toContain("chat.apply(");
    expect(studio).toContain("estimateInput(");
    expect(studio).toContain("generations.create(");
    expect(studio).toContain("pollGeneration(");
    // Video has no 4:5 frame; it must say so instead of sending an invalid request.
    expect(studio).toContain('ratio === "4:5"');
  });

  it("shows the real balance and no placeholder copy", () => {
    expect(studio).toContain("credits.get()");
    expect(studio).not.toContain("1,240 credits");
    expect(studio).not.toContain("connects in the next backend step");
  });

  it("lists only model photos uploaded in try-on, never Create uploads", () => {
    expect(studio).toContain('assets.list("person", "try_on")');
    expect(studio).toContain("Choose from library");
  });

  it("labels another angle as a separate generation action", () => {
    expect(studio).toContain("Additional generation");
    expect(studio).toContain("Another angle of the selected photo");
    expect(studio).toContain("Choose a view to generate one new matching photo.");
    expect(studio).toContain('aria-label="Generate an additional angle"');
  });

  it("presents generated photos as an interactive look gallery", () => {
    expect(studio).toContain('aria-label="Generated look gallery"');
    expect(studio).toContain("Look stack");
    expect(studio).toContain("look-gallery-card");
    expect(studio).toContain("batch[1]?.asset.id ?? front.id");
    expect(studio).toContain("onWheel={handleGalleryWheel}");
    expect(studio).toContain("onPointerDown={handleGalleryPointerDown}");
    expect(studio).toContain("Download all photos");
  });

  it("bulk-imports a product catalog from CSV into a reusable library, not straight into the look", () => {
    expect(studio).toContain("assets.importCatalogCsv(file)");
    expect(studio).toContain("Bulk import (CSV)");
    // The expected columns are spelled out next to the button, not just inside the
    // downloadable sample - a user shouldn't have to open a file to learn the format.
    expect(studio).toContain("Columns: url or imageUrl (one required per row), name (optional)");
    expect(studio).toContain('href="/try-on/catalog-sample.csv"');
    // Imports land in the product library; picking from it respects the same LOOK_SIZE cap
    // as a direct upload, so a catalog import can never overfill the active look.
    expect(studio).toContain('assets.list("product", "try_on")');
    expect(studio).toContain("products.length >= LOOK_SIZE");
    expect(studio).toContain("Choose from product library");
    expect(studio).toContain("Your product library");
  });

  it("shows complete photos and downloads the full set as one zip", () => {
    expect(styles).toMatch(/\.look-gallery-card img[\s\S]*?object-fit:\s*contain/);
    expect(studio).toContain('import JSZip from "jszip"');
    expect(studio).toContain('link.download = "look-photos.zip"');
    expect(studio).not.toContain("setTimeout(resolve, 400)");
    expect(studio).not.toContain("selected.label.toLowerCase()");
  });
});
