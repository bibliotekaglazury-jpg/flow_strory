import { test, expect } from "@playwright/test";
import { mockApi } from "./mock-api";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("a person photo without a product suggests the self-presentation template", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".style-option", { hasText: "Product Demo" }).click();
  const hint = page.locator(".style-hint");
  await expect(hint).toBeHidden();

  await page
    .getByLabel("Person image", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await expect(hint).toContainText("self-presentation");

  await hint.getByRole("button", { name: "Use Self-presentation" }).click();
  await expect(
    page.locator(".style-option", { hasText: "Self-presentation" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(hint).toBeHidden();
});
