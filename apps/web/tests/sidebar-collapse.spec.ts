import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("sidebar collapses by button and stays open after icon hover", async ({
  page,
}) => {
  await page.goto("/");

  const sidebar = page.getByTestId("sidebar");
  const toggle = page.getByRole("button", { name: "Collapse sidebar" });
  const silverRibbon = sidebar.getByTestId("sidebar-silver-ribbon");

  await expect(sidebar).toHaveAttribute("data-state", "expanded");
  await expect(silverRibbon).toBeVisible();
  await toggle.click();
  await expect(sidebar).toHaveAttribute("data-state", "collapsed");
  await expect(silverRibbon).toBeHidden();
  await expect(sidebar.getByText("Templates", { exact: true })).toBeHidden();

  await sidebar.getByRole("link", { name: "Templates" }).hover();
  await expect(sidebar).toHaveAttribute("data-state", "expanded");
  await expect(sidebar.getByText("Templates", { exact: true })).toBeVisible();

  await page.locator("main").hover();
  await expect(sidebar).toHaveAttribute("data-state", "expanded");
  await page.getByRole("button", { name: "Collapse sidebar" }).click();
  await expect(sidebar).toHaveAttribute("data-state", "collapsed");
});
