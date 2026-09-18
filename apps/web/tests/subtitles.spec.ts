import { expect, test } from "@playwright/test";

test("subtitle studio uploads, transcribes, autosaves, switches ratio and exports", async ({
  page,
}) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("console", (message) => {
    const source = message.location().url;
    if (message.type() === "error" && !source.endsWith("/favicon.ico")) {
      browserErrors.push(message.text());
    }
  });
  await page.goto("/subtitles");

  await expect(page.getByRole("heading", { name: "Subtitle Studio" })).toBeVisible();
  // Save state, format and export sit under the player, so they appear once there is a video.
  await expect(page.getByRole("button", { name: "Download video" })).toHaveCount(0);
  await page.getByLabel("Source video").setInputFiles("public/media/create-preview.mp4");
  // The chosen video plays in the preview right away, with a live status for each stage.
  await expect(page.locator(".subtitle-player-shell video")).toHaveCount(1);
  await expect(page.getByText(/Uploading video…|Transcribing speech…/).first()).toBeVisible();
  await expect(page.getByText("Transcribing speech…")).toBeVisible();

  // The project id is in the URL, so a reload resumes the same project.
  await expect(page).toHaveURL(/\/subtitles\?project=/);
  const firstCaption = page.getByRole("textbox", { name: "Caption at 00:00" });
  await expect(firstCaption).toBeVisible();
  await firstCaption.fill("A cleaner caption for the product story.");
  await expect(page.getByText("Saving…")).toBeVisible();
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("textbox", { name: "Caption at 00:00" })).toBeVisible();

  await page.getByRole("button", { name: "Editorial" }).click();
  await expect(page.getByRole("button", { name: "Editorial" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByRole("button", { name: "16:9" }).click();
  await expect(page.locator(".subtitle-editor-grid")).toHaveAttribute("data-ratio", "16:9");
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Download video" }).click();
  await expect(page.getByRole("button", { name: /Preparing video/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Download video" })).toBeVisible();

  // The "Video and SRT ready" promise on the entry screen backs a real download.
  const srtDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download SRT" }).click();
  expect((await srtDownload).suggestedFilename()).toMatch(/\.srt$/);

  // Sharing opens a link, and that link resolves publicly to just the video, not the editor.
  await page.getByRole("button", { name: "Share" }).click();
  await page.getByRole("button", { name: "Create shareable link" }).click();
  const shareInput = page.getByLabel("Shareable link");
  await expect(shareInput).toBeVisible();
  const shareUrl = await shareInput.inputValue();
  expect(shareUrl).toMatch(/\/share\//);

  const sharePage = await page.context().newPage();
  await sharePage.goto(shareUrl);
  await expect(sharePage.locator("video")).toBeVisible();
  await expect(sharePage.getByRole("heading", { name: "Subtitle Studio" })).toHaveCount(0);
  await sharePage.close();

  // Revoking makes the same link stop resolving.
  await page.getByRole("button", { name: "Revoke link" }).click();
  await expect(page.getByRole("button", { name: "Create shareable link" })).toBeVisible();
  const revokedPage = await page.context().newPage();
  const response = await revokedPage.goto(shareUrl);
  await expect(revokedPage.getByText(/unavailable/i)).toBeVisible();
  void response;
  await revokedPage.close();

  expect(browserErrors).toEqual([]);
});

test("editing keeps the same video loaded and the timeline seeks where you click", async ({
  page,
}) => {
  await page.goto("/subtitles");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/subtitles");
  await page.getByLabel("Source video").setInputFiles("public/media/create-preview.mp4");
  const caption = page.getByRole("textbox", { name: "Caption at 00:00" });
  await expect(caption).toBeVisible();
  const video = page.locator(".subtitle-player-shell video");
  const position = page.getByLabel("Video position");
  const source = await video.evaluate((element: HTMLVideoElement) => element.currentSrc);

  // Every save returns a newly signed link; the player must keep the video it already has.
  await caption.fill("Edited while watching.");
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();
  await caption.fill("Edited twice while watching.");
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();
  expect(await video.evaluate((element: HTMLVideoElement) => element.currentSrc)).toBe(source);

  // A caption block on the timeline sits at its real time and seeks there.
  const third = page.locator(".subtitle-track button").nth(2);
  await third.click();
  await expect.poll(async () => Number(await position.inputValue())).toBe(120);

  // Space plays and pauses from anywhere except text fields.
  await page.locator(".subtitle-waveform").hover();
  await page.keyboard.press("Space");
  await expect(page.getByRole("button", { name: "Pause video" })).toBeVisible();
  await page.keyboard.press("Space");
  await expect(page.getByRole("button", { name: "Play video" })).toBeVisible();

  // Clicking the waveform seeks to that point of the video.
  const waveform = page.locator(".subtitle-waveform");
  const box = await waveform.boundingBox();
  if (!box) throw new Error("waveform not rendered");
  await page.mouse.click(box.x + box.width * 0.75, box.y + box.height / 2);
  await expect.poll(async () => Number(await position.inputValue())).toBeGreaterThan(200);
});

test("Back returns to the start screen, and the history lists, single- and bulk-deletes projects", async ({
  page,
}) => {
  page.on("dialog", (dialog) => void dialog.accept());
  await page.goto("/subtitles");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/subtitles");

  // Upload the first project, then Back: this same route stays mounted (only ?project=
  // changes), so Back must actively clear the loaded project, not just change the URL.
  await page.getByLabel("Source video").setInputFiles("public/media/create-preview.mp4");
  await expect(page.getByRole("textbox", { name: "Caption at 00:00" })).toBeVisible();
  await page.getByRole("link", { name: "Back" }).click();
  await expect(page).toHaveURL(/\/subtitles$/);
  await expect(page.getByText("Your words, ready for every screen.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Caption at 00:00" })).toHaveCount(0);

  const items = page.locator(".subtitle-recent-project:not([data-example])");
  await expect(items).toHaveCount(1);

  // A second project, so single delete and bulk delete are both exercised for real.
  await page.getByLabel("Source video").setInputFiles("public/media/create-preview.mp4");
  await expect(page.getByRole("textbox", { name: "Caption at 00:00" })).toBeVisible();
  await page.getByRole("link", { name: "Back" }).click();
  await expect(items).toHaveCount(2);

  // Individual delete removes just the one row.
  await items.first().getByLabel("Delete this video").click();
  await expect(items).toHaveCount(1);

  // Bulk delete via Select mode: clicking the video thumbnail selects it too, not just
  // the small checkbox.
  await page.getByRole("button", { name: "Select" }).click();
  await page.locator(".subtitle-recent-video-select").click();
  await expect(page.locator('.subtitle-recent-video-select[aria-pressed="true"]')).toBeVisible();
  await page.getByRole("button", { name: "Delete selected" }).click();
  await expect(items).toHaveCount(0);
  await expect(page.getByText("Captioned video example")).toBeVisible();
});

test("subtitle studio fits a phone viewport without horizontal page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/subtitles");

  await expect(page.getByRole("heading", { name: "Subtitle Studio" })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
