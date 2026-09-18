import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api";

test("hero gallery replaces the side rail and cycles autoplay videos", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");

  const hero = page.locator(".hero");
  const gallery = hero.getByRole("region", { name: "Video inspiration" });
  await expect(gallery).toBeVisible();
  await expect(
    page.getByRole("region", { name: "More example videos" }),
  ).toHaveCount(0);
  await expect(hero).toHaveCSS("background-image", /hero-background\.png/);

  const videos = gallery.locator("video");
  await expect(videos).toHaveCount(5);
  await expect(gallery).toContainText("of 16");
  await expect(videos.first()).toHaveAttribute("autoplay", "");
  await expect(videos.first()).toHaveAttribute("loop", "");
  await expect(videos.first()).not.toHaveAttribute("controls", "");
  await expect(gallery.locator(".hero-video-card").first()).not.toHaveCSS(
    "transform",
    "none",
  );

  const firstSource = await videos.first().getAttribute("src");
  await gallery.getByRole("button", { name: "Next videos" }).click();
  await expect(gallery.locator(".hero-video-track")).toHaveAttribute(
    "data-sliding",
    "true",
  );
  await expect
    .poll(() => videos.first().getAttribute("src"))
    .not.toBe(firstSource);
});
