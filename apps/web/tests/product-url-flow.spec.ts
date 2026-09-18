import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api";

test("resolved URL image becomes product reference before chat apply", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Or add a product URL" }).click();
  // The URL is captured on paste now; there is no separate "Use URL" button.
  await page.getByLabel("Product URL").fill("https://shop.example/product");
  // The resolved page image lands in the first product slot.
  await expect(page.locator(".product-slot img").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Use URL" })).toHaveCount(0);

  const sent = page.waitForRequest((request) => request.url().endsWith("/messages") && request.method() === "POST");
  await page.getByLabel("Message about your video").fill("Zrób UGC po polsku");
  await page.getByRole("button", { name: "Send →" }).click();
  expect((await sent).postDataJSON().context.inputAssets.productImageId).toBeTruthy();
  await page.getByRole("button", { name: "Use this concept" }).click();
  await expect(page.getByText("Applied. Review your prompt and estimate below.")).toBeVisible();
});
