import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { mockApi } from "./mock-api";

test("Auto planning shows the fluid loader inside the video frame", async ({
  page,
}) => {
  await mockApi(page);
  let release!: () => void;
  const continuePlanning = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/chat/sessions/*/messages", async (route) => {
    await continuePlanning;
    await route.fallback();
  });

  await page.goto("/");
  await page
    .getByLabel("Product image")
    .setInputFiles("tests/fixtures/product.png");
  const autoMode = page
    .getByLabel("Prompt mode")
    .getByRole("button", { name: "Auto", exact: true });
  await expect(autoMode).toBeEnabled();
  await autoMode.click();
  await page.getByRole("button", { name: "Plan and estimate" }).click();

  const result = page.getByTestId("workspace-result");
  const frame = result.locator(".preview-frame");
  await expect(result.getByTestId("preview-status")).toHaveText(
    "Creating your concept…",
  );
  await expect(frame.locator(".fluid-loader-frame")).toBeVisible();
  await expect(
    page.getByText("Analysing your product and choosing a creative direction."),
  ).toHaveCount(0);
  await expect(result.locator(".preview-top")).toHaveCount(0);

  // The loader occupies the video's own frame, not the whole creation block: as a
  // full-stage overlay it stretched to the height of everything above it.
  await expect(page.locator(".creation-process-overlay")).toHaveCount(0);
  const stageBox = await page.locator(".creation-process-stage").boundingBox();
  const frameBox = await frame.boundingBox();
  expect(frameBox!.height).toBeLessThan(stageBox!.height);
  expect(frameBox!.height / frameBox!.width).toBeGreaterThan(1.5);

  await mkdir("../../docs/verification/auto-planning-loader", {
    recursive: true,
  });
  await page.screenshot({
    path: "../../docs/verification/auto-planning-loader/desktop-1440.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(frame.locator(".fluid-loader-frame")).toBeVisible();
  await page.screenshot({
    path: "../../docs/verification/auto-planning-loader/mobile-390.png",
    fullPage: true,
  });

  release();
  await expect(page.getByRole("button", { name: /Generate Video/ })).toBeEnabled();
  await expect(frame.locator(".fluid-loader-frame")).toHaveCount(0);
});
