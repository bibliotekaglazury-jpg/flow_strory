import { test, expect } from "@playwright/test";
import { mockApi } from "./mock-api";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("a whole look uploads at once and opens the try-on panel by itself", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByLabel("Product image").first()).toBeEnabled();

  // Several pieces in one pick, the way a shop owner actually has them on disk.
  await page
    .getByLabel("Product image")
    .first()
    .setInputFiles([
      "tests/fixtures/product.png",
      "tests/fixtures/product.png",
      "tests/fixtures/product.png",
    ]);
  await expect(page.getByRole("heading", { name: /Products · 3 of 5/ })).toBeVisible();

  // No chat instruction: the panel offers itself once a model joins the look.
  await expect(page.getByRole("heading", { name: "Try-on" })).toBeHidden();
  await page
    .getByLabel("Person image", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await expect(page.getByRole("heading", { name: "Try-on" })).toBeVisible();

  const preview = page.waitForRequest(
    (r) => r.url().endsWith("/api/try-on") && r.method() === "POST",
  );
  await page.getByRole("button", { name: "Generate preview photo" }).click();
  const body = (await preview).postDataJSON();
  expect(body.inputAssets.items).toHaveLength(2);
  expect(body.inputAssets.personImageId).toBeTruthy();
  expect(body.idempotencyKey).toBeTruthy();

  await expect(page.getByAltText("Your model wearing the look")).toBeVisible();

  // Angles re-shoot the approved preview rather than starting over.
  const again = page.waitForRequest(
    (r) => r.url().endsWith("/api/try-on") && r.method() === "POST",
  );
  await page.getByRole("button", { name: "Back", exact: true }).click();
  const second = (await again).postDataJSON();
  expect(second.angle).toBe("back");
  expect(second.baseAssetId).toBeTruthy();

  await page.getByRole("button", { name: "Close try-on" }).click();
  await expect(page.getByRole("heading", { name: "Try-on" })).toBeHidden();
});
