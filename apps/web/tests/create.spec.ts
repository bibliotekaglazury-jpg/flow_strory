import { test, expect } from "@playwright/test";
import { mockApi } from "./mock-api";
test.beforeEach(async ({ page }) => {
  await mockApi(page);
});
test("Polish product/person chat to applied plan, generation and persisted history", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByLabel("Product image", { exact: true })).toBeEnabled();
  await page
    .getByLabel("Product image")
    .setInputFiles("tests/fixtures/product.png");
  await page
    .getByLabel("Person image", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await page
    .getByLabel("Message about your video")
    .fill(
      "Zrób naturalne 15-sekundowe UGC dla kremu do twarzy. Dziewczyna mówi po polsku.",
    );
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(page.getByText(/Polish.*Native audio/)).toBeVisible();
  await page
    .getByRole("button", { name: "Use this concept", exact: true })
    .click();
  const generate = page.getByRole("button", { name: /Generate Video/ });
  await expect(generate).toBeEnabled();
  const submitted = page.waitForRequest(
    (r) => r.url().endsWith("/api/generations") && r.method() === "POST",
  );
  await generate.click();
  const body = (await submitted).postDataJSON();
  expect(body.language).toBe("pl");
  expect(body.prompt).toContain("Spójrz na ten produkt");
  expect(body.inputAssets.personImageId).toBeTruthy();
  await expect(page.getByTestId("preview-status")).toContainText(
    /Queued|Generating/,
  );
  await expect(page.getByTestId("preview-status")).toContainText("Completed", {
    timeout: 60000,
  });
  await expect(
    page.getByRole("link", { name: "Download video" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Recent Creations" }),
  ).toBeVisible();
  await expect(page.getByTestId("history-item").first()).toBeVisible();
});
test("keyboard navigation and narrow viewport do not overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Create Your Video" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to creation" }),
  ).toBeFocused();
});
