import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { mockApi } from "./mock-api";
for (const { ratio, width } of [
  { ratio: "9:16", width: 1440 },
  { ratio: "1:1", width: 1440 },
  { ratio: "16:9", width: 390 },
]) {
  test(`result below chat and ${ratio} reaches generation`, async ({
    page,
  }) => {
    await mockApi(page);
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/");
    const result = page.getByTestId("workspace-result");
    await expect(result.getByText("Your video", { exact: true })).toBeVisible();
    await page
      .getByLabel("Product image", { exact: true })
      .setInputFiles("tests/fixtures/product.png");
    await page.getByRole("button", { name: ratio, exact: true }).click();
    const sent = page.waitForRequest(
      (r) => r.url().endsWith("/messages") && r.method() === "POST",
    );
    await page
      .getByLabel("Message about your video")
      .fill("Zrób naturalne UGC dla kremu po polsku.");
    await page.getByRole("button", { name: "Send →", exact: true }).click();
    expect((await sent).postDataJSON().context.aspectRatio).toBe(ratio);
    await page
      .getByRole("button", { name: "Use this concept", exact: true })
      .click();
    const submission = page.waitForRequest(
      (r) => r.url().endsWith("/api/generations") && r.method() === "POST",
    );
    await page.getByRole("button", { name: /Generate Video/ }).click();
    expect((await submission).postDataJSON().aspectRatio).toBe(ratio);
    await expect(result.getByTestId("preview-status")).toContainText(
      /Queued|Generating/,
    );
    const composer = await page
      .getByLabel("Message about your video")
      .boundingBox();
    const position = await result.boundingBox();
    expect(position!.y).toBeGreaterThan(composer!.y + composer!.height);
    await expect(result.getByLabel("Generated video")).toBeVisible({
      timeout: 60000,
    });
    const frame = result.locator(".preview-frame");
    const box = await frame.boundingBox();
    const [w, h] = ratio.split(":").map(Number);
    expect(box!.width / box!.height).toBeCloseTo(w / h, 1);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    await mkdir("../../docs/verification/result-placement", {
      recursive: true,
    });
    await page.evaluate(() => {
      (document.activeElement as HTMLElement)?.blur();
      window.scrollTo({ top: 0, behavior: "instant" });
    });
    await page.waitForFunction(() => window.scrollY === 0);
    await page.screenshot({
      path: `../../docs/verification/result-placement/${ratio.replace(":", "x")}-${width}.png`,
      fullPage: true,
    });
  });
}
