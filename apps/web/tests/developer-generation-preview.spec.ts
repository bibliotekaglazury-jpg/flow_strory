import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { mockApi } from "./mock-api";

// These controls only exist in a mock-mode build, which the rest of the suite cannot
// use: with in-process mocks the app never issues the HTTP calls other specs assert on.
test.skip(
  process.env.PLAYWRIGHT_MOCK_MODE !== "1",
  "Needs a NEXT_PUBLIC_USE_MOCK_API=true build; run with PLAYWRIGHT_MOCK_MODE=1",
);
test("developer can preview generation states without submitting a job", async ({
  page,
}) => {
  await mockApi(page);
  const submissions: string[] = [];
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      request.url().endsWith("/api/generations")
    )
      submissions.push(request.url());
  });

  await page.goto("/");
  const controls = page.getByRole("group", { name: "Developer preview" });
  await expect(controls).toBeVisible();

  await controls.getByRole("button", { name: "Queued" }).click();
  await expect(page.getByTestId("preview-status")).toHaveText(
    "Generating your video…",
  );
  await controls.getByRole("button", { name: "Generating" }).click();
  await expect(page.getByTestId("preview-status")).toHaveText(
    "Generating your video…",
  );
  await expect(
    page.getByText("Usually takes a few minutes. You can leave this page."),
  ).toHaveCount(0);
  await expect(page.getByTestId("workspace-result").locator(".preview-top")).toHaveCount(0);
  // The loader lives in the video frame now, not in a full-stage overlay.
  await expect(page.locator(".creation-process-overlay")).toHaveCount(0);
  await expect(
    page.getByTestId("workspace-result").locator(".preview-frame"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Cancel generation" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Generation progress")).toHaveCount(0);
  await expect(page.locator(".play-disc")).toHaveCount(0);
  await expect(page.locator(".fluid-loader-frame")).toBeVisible();
  await expect(
    page.frameLocator(".fluid-loader-frame").locator("canvas"),
  ).toBeVisible();
  await mkdir("../../docs/verification/developer-generation-preview", {
    recursive: true,
  });
  await page.screenshot({
    path: "../../docs/verification/developer-generation-preview/generating-1440.png",
    fullPage: true,
  });
  await controls.getByRole("button", { name: "Failed" }).click();
  await expect(
    page.getByTestId("workspace-result").getByRole("alert"),
  ).toContainText("Developer preview");
  await controls.getByRole("button", { name: "Completed" }).click();
  await expect(page.getByLabel("Generated video")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(controls).toBeVisible();
  await page.screenshot({
    path: "../../docs/verification/developer-generation-preview/completed-390.png",
    fullPage: true,
  });
  expect(submissions).toEqual([]);
});
