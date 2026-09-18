import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { mockApi } from "./mock-api";

test("hero gallery pauses rotation on hover while its videos keep playing", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");

  const gallery = page.getByRole("region", { name: "Video inspiration" });
  await expect(gallery).toBeVisible();
  const firstVideo = gallery.locator("video").first();
  await expect
    .poll(() =>
      firstVideo.evaluate((video) => !(video as HTMLVideoElement).paused),
    )
    .toBe(true);

  const source = await firstVideo.getAttribute("src");
  await gallery.hover();
  await page.waitForTimeout(7000);
  await expect(firstVideo).toHaveAttribute("src", source!);
  await expect
    .poll(() =>
      firstVideo.evaluate((video) => !(video as HTMLVideoElement).paused),
    )
    .toBe(true);

  await page.mouse.move(0, 0);
  await expect
    .poll(() => firstVideo.getAttribute("src"), { timeout: 8000 })
    .not.toBe(source);

  await mkdir("../../docs/verification/showcase-autoplay", { recursive: true });
  await page.screenshot({
    path: "../../docs/verification/showcase-autoplay/desktop-1440.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(gallery).toBeVisible();
  await expect(page.locator("html")).toHaveJSProperty("scrollWidth", 390);
  await page.screenshot({
    path: "../../docs/verification/showcase-autoplay/mobile-390.png",
    fullPage: true,
  });
});
