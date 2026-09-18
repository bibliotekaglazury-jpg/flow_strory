import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const studio = readFileSync(
  new URL("../features/subtitles/subtitle-studio.tsx", import.meta.url),
  "utf8",
);
const composition = readFileSync(
  new URL("../features/subtitles/subtitle-composition.tsx", import.meta.url),
  "utf8",
);
const entry = readFileSync(
  new URL("../features/subtitles/subtitle-entry-screen.tsx", import.meta.url),
  "utf8",
);
const styles = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

describe("subtitle studio frontend", () => {
  it("uses one Remotion composition for the interactive preview", () => {
    expect(studio).toContain('from "@remotion/player"');
    expect(studio).toContain("SubtitleComposition");
    expect(composition).toContain("useCurrentFrame");
    expect(composition).toContain("OffthreadVideo");
  });

  it("offers only the approved vertical and horizontal formats", () => {
    expect(studio).toContain('"9:16"');
    expect(studio).toContain('"16:9"');
    expect(studio).not.toContain('"1:1"');
  });

  it("contains the approved transcript and styling tools", () => {
    for (const copy of [
      "Transcript",
      "Split",
      "Merge",
      "Caption style",
      "Modern",
      "Classic",
      "Impact",
      "Editorial",
      "Safe area",
      "Download video",
    ])
      expect(studio).toContain(copy);
  });

  it("keeps the full source frame visible in both preview formats", () => {
    expect(composition).toContain('objectFit: "contain"');
    expect(styles).toMatch(/\.subtitle-player[\s\S]*?object-fit:\s*contain/);
  });

  it("persists through the subtitle API instead of local demo state", () => {
    expect(studio).toContain('assets.upload(file, "source_video", undefined,');
    expect(studio).toContain("subtitleProjects.create(");
    expect(studio).toContain("services.update(projectId");
    expect(studio).toContain("subtitleProjects.export(");
    expect(studio).toContain("subtitleProjects.getExport(");
    expect(studio).toContain('"REVISION_CONFLICT"');
    expect(studio).toContain("AUTOSAVE_MS = 700");
    expect(studio).toContain("useSearchParams");
    expect(studio).not.toContain("simulateExport");
    expect(studio).not.toContain("initialCues");
  });

  it("previews the chosen video immediately and shows upload and transcription progress", () => {
    expect(studio).toContain("URL.createObjectURL(file)");
    expect(studio).toContain('"Uploading video…"');
    expect(studio).toContain('"Transcribing speech…"');
    expect(studio).toContain('role="progressbar"');
    expect(studio).toContain("Retry upload");
    const nextConfig = readFileSync(new URL("../next.config.ts", import.meta.url), "utf8");
    // The /api rewrite used to cut uploads off at 10MB, leaving "Uploading…" forever.
    expect(nextConfig).toContain("proxyClientMaxBodySize");
    const http = readFileSync(new URL("../services/http.ts", import.meta.url), "utf8");
    expect(http).toContain("xhr.upload.onprogress");
  });

  it("uses the approved light entry screen with a working upload and real video previews", () => {
    expect(entry).toContain("Your words, ready for every screen.");
    expect(entry).toContain("Recent subtitle projects");
    expect(entry).toContain("Open editor");
    expect(entry).toContain("Reels");
    expect(entry).toContain("Shorts");
    expect(entry).toContain("Stories");
    expect(entry).not.toContain(">Before<");
    expect(entry).not.toContain(">After<");
    expect(entry).toContain("/media/subtitle-studio-demo.mp4");
    expect(studio).toContain('fileInput.current?.click()');
    expect(studio).toContain("onFileSelected={(file) => void chooseVideo(file)}");
    expect(styles).toContain(".subtitle-entry-hero");
    expect(styles).toContain(".subtitle-format-showcase");
  });

  it("returns from the editor to the subtitle start screen and clears the loaded project", () => {
    expect(studio).toContain('<Link\n            href="/subtitles"\n            className="subtitle-back"');
    // The route stays mounted across Back (only ?project= changes), so the loaded project,
    // preview and export state must be cleared by hand or the old editor would just linger.
    expect(studio).toContain("function goToStart()");
    expect(studio).toContain("leavingProject.current = true");
    expect(studio).toContain("setProject(null)");
    expect(studio).toContain("setPendingUpload(null)");
  });

  it("drives time from player events and never swaps the video on a save", () => {
    expect(studio).toContain('addEventListener("timeupdate"');
    expect(studio).toContain('addEventListener("seeked"');
    expect(studio).not.toContain("setInterval(() => setFrame");
    expect(studio).toContain("current?.assetId === next.sourceAsset.id");
    expect(studio).toContain("instance.isPlaying()");
    // Scrubbing remembers whether it was playing and resumes on release.
    expect(studio).toContain("resumeAfterScrub.current = player.current?.isPlaying()");
    expect(studio).toContain("onPointerUp={endScrub}");
    expect(studio).toContain('event.code !== "Space"');
  });

  it("has responsive editor layouts for desktop and phone", () => {
    expect(styles).toContain(".subtitle-editor-grid");
    expect(styles).toMatch(/@media \(max-width: 1100px\)[\s\S]*?\.subtitle-editor-grid/);
    expect(styles).toMatch(/@media \(max-width: 720px\)[\s\S]*?\.subtitle-timeline/);
  });

  it("lists every subtitle project, not just the newest one, with single and bulk delete", () => {
    // The whole history is fetched and paginated, not just the most recent project.
    expect(entry).toContain("subtitleProjects.list()");
    expect(entry).toContain("cursor && (");
    expect(entry).toContain("Load more");
    // The old "View all" link pointed at /library, which never listed subtitle projects.
    expect(entry).not.toContain('href="/library"');
    // Individual delete on every row, plus a select-mode bulk bar.
    expect(entry).toContain("subtitleProjects.remove(project.id)");
    expect(entry).toContain("deleteSelected");
    expect(entry).toContain("window.confirm(");
    expect(entry).toContain("Delete selected");
    // In Select mode, clicking the video thumbnail toggles selection too, not just the
    // small checkbox, so there's a large click target for picking videos to delete.
    expect(entry).toContain("subtitle-recent-video-select");
    expect(entry).toMatch(/selectMode \?[\s\S]*?onClick={\(\) => toggleSelected\(project\.id\)}/);
  });

  it("shares a completed export through a revocable link, not a raw asset URL", () => {
    expect(studio).toContain("subtitleProjects.share(");
    expect(studio).toContain("subtitleProjects.unshare(");
    expect(studio).toContain("exportJob.shareToken");
    expect(studio).toContain("FacebookShareButton");
    expect(studio).toContain("WhatsappShareButton");
    expect(studio).toContain("TelegramShareButton");
    expect(studio).toContain("EmailShareButton");
    // Instagram/TikTok take a file, not a link: the native share sheet sends the actual video.
    expect(studio).toContain("navigator.canShare");
    expect(studio).toContain("navigator.share(");
    // Only a completed export can be shared; the button lives with Download, not Export.
    expect(studio).toMatch(/downloadUrl \?[\s\S]*?subtitle-share-anchor/);
  });
});
