import { test, expect, type Page } from "@playwright/test";
import { mockApi } from "./mock-api";
async function capture(page: Page, path: string) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path, fullPage: true });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("chat applies without generation, and a reload starts a clean conversation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByLabel("Product image", { exact: true })).toBeEnabled();
  await page
    .getByLabel("Product image", { exact: true })
    .setInputFiles("tests/fixtures/product.png");
  await expect(
    page.getByLabel("Prompt mode").getByRole("button", { name: "AI Chat", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByLabel("Message about your video")
    .fill("Show a creator demonstrating a shoe in daylight.");
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Use this concept", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Use this concept", exact: true })
    .click();
  await expect(page.getByLabel("Production prompt")).toContainText("shoe");
  await expect(
    page.getByRole("button", { name: /Generate Video/ }),
  ).toBeEnabled();
  await expect(page.getByTestId("history-item")).toHaveCount(0);
  await page.getByLabel("Prompt mode").getByRole("button", { name: "Auto", exact: true }).click();
  await page
    .getByLabel("Production prompt")
    .fill("A manually edited production prompt.");
  await page.getByLabel("Prompt mode").getByRole("button", { name: "AI Chat", exact: true }).click();
  // A reload is a fresh start: an old conversation must not silently steer a new video.
  await page.reload();
  await expect(page.getByLabel("Message about your video")).toBeEnabled();
  await expect(
    page.getByText("Demo concept ready.", { exact: false }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Use this concept", exact: true }),
  ).toHaveCount(0);
});

test("chat mobile layout and empty state", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByLabel("Message about your video")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("failed reply preserves editable message without generation", async ({
  page,
}) => {
  await page.route("**/api/chat/sessions/*/messages", (route) =>
    route.fulfill({
      status: 503,
      json: {
        error: {
          code: "CHAT_FAILED",
          message: "Reply unavailable. Try again.",
          retryable: true,
        },
        requestId: "test",
      },
    }),
  );
  await page.goto("/");
  await page
    .getByLabel("Message about your video")
    .fill("Keep this brief after a connection error.");
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Reply unavailable" }),
  ).toBeVisible();
  await expect(page.getByLabel("Message about your video")).toHaveValue(
    "Keep this brief after a connection error.",
  );
  await expect(page.getByTestId("history-item")).toHaveCount(0);
});

test("Auto mode has no chat composer or campaign brief block", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Prompt mode").getByRole("button", { name: "Auto", exact: true }).click();
  await expect(page.getByLabel("Message about your video")).toBeHidden();
  await expect(
    page.getByLabel("Describe your product or campaign"),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Generate Prompt", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Write the brief yourself here.", { exact: false }),
  ).toHaveCount(0);
  await page.getByLabel("Prompt mode").getByRole("button", { name: "AI Chat", exact: true }).click();
  await expect(page.getByLabel("Message about your video")).toBeVisible();
});

test("real-mode capabilities show only 15 seconds", async ({ page }) => {
  await page.route("**/api/models", (route) =>
    route.fulfill({
      json: {
        models: [
          {
            id: "auto",
            label: "Auto",
            available: true,
            unavailableReason: null,
            configurations: [
              {
                duration: 15,
                aspectRatio: "9:16",
                quality: null,
                resolution: "720p",
                supportsPersonImage: true,
                supportsSourceVideo: true,
              },
            ],
            voices: [{ id: "auto", label: "Auto" }],
          },
        ],
      },
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "15s", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "20s", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "30s", exact: true }),
  ).toHaveCount(0);
});

test("Auto plans a text-only service, and Change concept keeps the conversation", async ({ page }) => {
  const intents: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && /\/chat\/sessions\/[^/]+\/messages$/.test(new URL(request.url()).pathname))
      intents.push(request.postDataJSON().intent);
  });
  await page.goto("/");
  await expect(page.getByLabel("Style").getByRole("button", { name: "Auto", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByLabel("Message about your video").fill("Zrób reklamę kursu angielskiego dla dorosłych po polsku.");
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(page.getByRole("button", { name: "Use this concept", exact: true })).toBeEnabled();
  for (const label of ["Concept", "Hook", "Story", "Script", "Look"])
    await expect(page.locator(".recipe-summary dt").filter({ hasText: new RegExp(`^${label}$`) })).toBeVisible();
  await expect(page.locator(".recipe-summary")).not.toContainText(/creativeMechanism|candidate|Claude|stoppingPower/);
  await page.getByRole("button", { name: "Change concept", exact: true }).click();
  await expect(page.getByLabel("Message about your video")).toHaveValue("Change the concept: ");
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(page.getByRole("button", { name: "Use this concept", exact: true })).toBeEnabled();
  await page.getByLabel("Message about your video").fill("Keep this concept and soften the delivery.");
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(page.getByRole("button", { name: "Use this concept", exact: true })).toBeEnabled();
  expect(intents).toEqual(["message", "change_concept", "message"]);
  await page.getByRole("button", { name: "Use this concept", exact: true }).click();
  await expect(page.getByRole("button", { name: /Generate Video/ })).toBeEnabled();
  await expect(page.getByTestId("history-item")).toHaveCount(0);
  await expect(page.locator(".style-option").filter({ hasText: "UGC Review" })).toHaveAttribute("aria-pressed", "true");
});

test("quality failure keeps the accepted concept and Change concept intent for retry", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByLabel("Message about your video").fill("An English lesson for hesitant speakers.");
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(page.getByRole("button", { name: "Change concept", exact: true })).toBeEnabled();
  const previous = await page.locator(".recipe-summary").innerText();
  const intents: string[] = [];
  let release!: () => void;
  const replyReady = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/chat/sessions/*/messages", async (route) => {
    intents.push(route.request().postDataJSON().intent);
    await replyReady;
    await route.fulfill({ status: 422, json: { error: {
      code: "CREATIVE_QUALITY_LOW", message: "Could not produce a strong enough concept. Try a different direction.", retryable: true,
    }, requestId: "quality-test" } });
  });
  await page.getByRole("button", { name: "Change concept", exact: true }).click();
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(page.locator(".chat-thinking")).toBeVisible();
  await expect(page.getByLabel("Message about your video")).toBeDisabled();
  await capture(page, testInfo.outputPath("chat-loading-disabled.png"));
  release();
  await expect(page.getByRole("alert").filter({ hasText: "strong enough" })).toBeVisible();
  await expect(page.locator(".recipe-summary")).toHaveText(previous, { useInnerText: true });
  await capture(page, testInfo.outputPath("chat-quality-error.png"));
  await page.getByRole("button", { name: "Send →", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "strong enough" })).toBeVisible();
  expect(intents).toEqual(["change_concept", "change_concept"]);
  await expect(page.getByTestId("history-item")).toHaveCount(0);
});

for (const width of [1222, 390]) {
  test(`compact concept states at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1287 });
    await page.goto("/");
    await expect(page.getByLabel("Message about your video")).toBeEnabled();
    await capture(page, testInfo.outputPath(`chat-empty-${width}.png`));
    await page.getByLabel("Message about your video").fill("Show how an English lesson helps hesitant speakers start a conversation.");
    await page.getByRole("button", { name: "Send →", exact: true }).click();
    await expect(page.getByRole("button", { name: "Use this concept", exact: true })).toBeEnabled();
    await page.getByRole("button", { name: "Use this concept", exact: true }).focus();
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Change concept", exact: true })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await capture(page, testInfo.outputPath(`chat-concept-${width}.png`));
    await page.getByLabel("Prompt mode").getByRole("button", { name: "Auto", exact: true }).click();
    await expect(page.getByLabel("Message about your video")).toBeHidden();
    await capture(page, testInfo.outputPath(`chat-auto-${width}.png`));
  });
}
