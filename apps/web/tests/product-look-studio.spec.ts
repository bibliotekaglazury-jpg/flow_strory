import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import JSZip from "jszip";
import { mockApi } from "./mock-api";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("product look studio uploads, shoots a matching angle set and starts a video", async ({
  page,
}) => {
  await page.goto("/try-on");

  await page
    .getByLabel("Product images")
    .setInputFiles([
      "tests/fixtures/product.png",
      "tests/fixtures/product.png",
      "tests/fixtures/product.png",
    ]);
  await expect(page.getByText("3 / 5 items")).toBeVisible();

  // Photos need a model; the page says so instead of letting the request fail.
  const shootButton = page.getByRole("button", { name: /Generate 4 photos/ });
  await expect(shootButton).toBeDisabled();
  await expect(page.getByText("Add a model photo to generate photos.")).toBeVisible();

  // Nothing uploaded yet: the library says so instead of showing an empty box.
  const library = page.getByRole("button", { name: "Choose from library" });
  await library.click();
  await expect(page.getByText("No model photos yet.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Close library" }).click();

  await page
    .getByLabel("Model photo", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await expect(shootButton).toBeEnabled();

  // The photo just uploaded is now in the user's own library and can be picked again.
  await library.click();
  const earlier = page.getByRole("button", { name: /^Use / });
  await expect(earlier).toHaveCount(1);
  await earlier.click();
  await expect(page.getByRole("region", { name: "Your model photos" })).toBeHidden();
  await expect(shootButton).toBeEnabled();

  const shots: Record<string, unknown>[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith("/api/try-on") && r.method() === "POST")
      shots.push(r.postDataJSON());
  });
  await shootButton.click();
  await expect(page.getByText("4 ready")).toBeVisible();
  expect(shots).toHaveLength(4);
  expect(shots[0].angle).toBe("front");
  expect(shots[0].baseAssetId).toBeUndefined();
  // The other three re-shoot the approved front photo so the set shows one look.
  for (const shot of shots.slice(1)) expect(shot.baseAssetId).toBeTruthy();
  expect((shots[0].inputAssets as { items: unknown[] }).items).toHaveLength(2);

  await page.getByRole("button", { name: "Detail", exact: true }).click();
  await expect(page.getByText("5 ready")).toBeVisible();
  await expect(page.getByRole("link", { name: "Download", exact: true })).toHaveCount(0);

  // The full set is one ZIP, so Chrome never asks for multi-download permission.
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /Download all photos/ }).click();
  const archiveDownload = await download;
  expect(archiveDownload.suggestedFilename()).toBe("look-photos.zip");
  const archivePath = await archiveDownload.path();
  if (!archivePath) throw new Error("ZIP download has no local path");
  const archive = await JSZip.loadAsync(await readFile(archivePath));
  expect(Object.values(archive.files).filter((file) => !file.dir)).toHaveLength(5);

  // Video has no 4:5 frame.
  await page.getByRole("button", { name: /^4:5/ }).click();
  await page.getByRole("button", { name: "Generate Video Instead" }).click();
  await expect(page.locator(".look-demo-notice[data-tone='error']")).toContainText(
    "9:16, 1:1 or 16:9",
  );

  await page.getByRole("button", { name: /^9:16/ }).click();
  const created = page.waitForRequest(
    (r) => r.url().endsWith("/api/generations") && r.method() === "POST",
  );
  await page.getByRole("button", { name: "Generate Video Instead" }).click();
  const body = (await created).postDataJSON();
  expect(body.quoteId).toBeTruthy();
  expect(body.promptId).toBeTruthy();
  expect(body.aspectRatio).toBe("9:16");
  await expect(page.getByText("Your video", { exact: true })).toBeVisible();
});

test("each generation is a folder whose photos survive a page reload", async ({ page }) => {
  await page.goto("/try-on");
  await page.getByLabel("Product images").setInputFiles("tests/fixtures/product.png");
  await page
    .getByLabel("Model photo", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await page.getByRole("radio", { name: /1 hero photo/ }).click();
  const shoot = page.getByRole("button", { name: /Generate hero photo/ });

  // The result still appears right below, as before.
  await shoot.click();
  await expect(page.getByText("1 ready")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Look 1/ })).toBeVisible();

  // A second generation is a second folder.
  await shoot.click();
  await expect(page.getByRole("button", { name: /^Look 2/ })).toBeVisible();

  await page.reload();
  await expect(page.getByText("1 ready")).toBeHidden();
  await page.getByRole("button", { name: /^Look 1/ }).click();
  await expect(page.getByText("1 ready")).toBeVisible();
  await expect(page.getByAltText("Hero view of the look")).toBeVisible();
  // Opening a folder restores its model and products, so another angle can be shot.
  await expect(page.getByText("1 / 5 items")).toBeVisible();
  await expect(page.getByText("Replace model photo")).toBeVisible();
});

test("clearing imports lets a new set of products be loaded", async ({ page }) => {
  await page.goto("/try-on");
  await page
    .getByLabel("Product images")
    .setInputFiles(["tests/fixtures/product.png", "tests/fixtures/product.png"]);
  await page
    .getByLabel("Model photo", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await expect(page.getByText("2 / 5 items")).toBeVisible();

  const clear = page.getByRole("button", { name: "Clear imports" });
  await clear.click();
  await expect(page.getByText("0 / 5 items")).toBeVisible();
  await expect(page.getByText("Upload model photo", { exact: true })).toBeVisible();
  await expect(clear).toBeHidden();

  await page.getByLabel("Product images").setInputFiles("tests/fixtures/product.png");
  await expect(page.getByText("1 / 5 items")).toBeVisible();
});

test("bulk CSV import fills the product library, and picking from it fills the look", async ({
  page,
}) => {
  await page.goto("/try-on");

  await page.getByLabel("Catalog CSV").setInputFiles("tests/fixtures/catalog.csv");
  await expect(page.getByText("2 added, 1 skipped.")).toBeVisible();

  await page.getByRole("button", { name: "Choose from product library" }).click();
  await expect(page.getByText("Your product library")).toBeVisible();
  const items = page.locator('[aria-label="Your product library"] .look-library-grid button');
  await expect(items).toHaveCount(2);

  await items.first().click();
  await expect(page.getByText("1 / 5 items")).toBeVisible();
});

test("products uploaded via Upload products survive a reload through the product library", async ({
  page,
}) => {
  await page.goto("/try-on");

  await page
    .getByLabel("Product images")
    .setInputFiles(["tests/fixtures/product.png", "tests/fixtures/product.png"]);
  await expect(page.getByText("2 / 5 items")).toBeVisible();

  await page.reload();
  await page.getByRole("button", { name: "Choose from product library" }).click();
  await expect(page.getByText("Your product library")).toBeVisible();
  const items = page.locator('[aria-label="Your product library"] .look-library-grid button');
  await expect(items).toHaveCount(2);
});

test("product look studio does not overflow on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/try-on");
  await expect(page.getByRole("heading", { name: "Create Your Look" })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("generated photos move through the look gallery with the mouse wheel and drag", async ({ page }) => {
  await page.goto("/try-on");
  await page.getByLabel("Product images").setInputFiles("tests/fixtures/product.png");
  await page
    .getByLabel("Model photo", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await page.getByRole("button", { name: /Generate 4 photos/ }).click();

  const gallery = page.getByRole("region", { name: "Generated look gallery" });
  await expect(gallery).toBeVisible();
  await expect(gallery.locator(".look-gallery-card img").first()).toHaveCSS("object-fit", "contain");
  await expect(gallery.locator('[aria-current="true"]')).toContainText("02");
  await gallery.hover();
  await gallery.dispatchEvent("wheel", { deltaY: 500, bubbles: true, cancelable: true });
  await expect(gallery.locator('[aria-current="true"]')).toContainText("03");

  const box = await gallery.boundingBox();
  if (!box) throw new Error("Gallery has no visible bounds");
  await page.mouse.move(box.x + box.width * 0.62, box.y + box.height * 0.45);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.45, { steps: 8 });
  await page.mouse.up();
  await expect(gallery.locator('[aria-current="true"]')).toContainText("04");
});
