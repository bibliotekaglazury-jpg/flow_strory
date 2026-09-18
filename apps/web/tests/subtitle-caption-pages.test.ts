import { describe, expect, it } from "vitest";
import { captionPages, timedWords } from "../features/subtitles/subtitle-composition";

const cue = {
  id: "c1",
  startMs: 0,
  endMs: 4000,
  text: "Klienci znajdują konkurencję w Google i ChatGPT",
  words: [
    { id: "w1", text: "Klienci", startMs: 100, endMs: 600 },
    { id: "w2", text: "znajdują", startMs: 650, endMs: 1200 },
    { id: "w3", text: "konkurencję", startMs: 1250, endMs: 2000 },
    { id: "w4", text: "w", startMs: 2050, endMs: 2150 },
    { id: "w5", text: "Google", startMs: 2200, endMs: 2700 },
    { id: "w6", text: "i", startMs: 2750, endMs: 2850 },
    { id: "w7", text: "ChatGPT", startMs: 2900, endMs: 3800 },
  ],
};
// Stand-in for fillTextBox: a page "fits" while its words take at most 16 characters.
const fits = (words: string[]) => words.join(" ").length <= 16;

describe("caption pages", () => {
  it("splits vertical footage into short pages at word boundaries, keeping every word whole", () => {
    const pages = captionPages([cue], true, fits);
    expect(pages.length).toBeGreaterThan(1);
    expect(pages.flatMap((page) => page.words.map((word) => word.text))).toEqual(
      cue.words.map((word) => word.text),
    );
    for (const page of pages) expect(page.words.length === 1 || fits(page.words.map((w) => w.text))).toBe(true);
    // Pages tile the cue: first starts with the cue, each next starts at its first word.
    expect(pages[0].startMs).toBe(cue.startMs);
    expect(pages.at(-1)!.endMs).toBe(cue.endMs);
    for (let i = 1; i < pages.length; i++) {
      expect(pages[i].startMs).toBe(pages[i].words[0].startMs);
      expect(pages[i - 1].endMs).toBe(pages[i].startMs);
    }
  });

  it("keeps ordinary one-cue subtitles for horizontal footage", () => {
    const pages = captionPages([cue], false, fits);
    expect(pages).toHaveLength(1);
    expect(pages[0]).toMatchObject({ startMs: 0, endMs: 4000 });
  });

  it("gives an over-wide single word its own page instead of cutting it", () => {
    const long = { ...cue, text: "Supercalifragilisticexpialidocious ok", words: [] };
    const pages = captionPages([long], true, fits);
    expect(pages.map((page) => page.words.map((word) => word.text).join(" "))).toEqual([
      "Supercalifragilisticexpialidocious",
      "ok",
    ]);
  });

  it("paces rewritten text without timestamps across the cue span in order", () => {
    const words = timedWords({ ...cue, text: "one three fivefive", words: [] });
    expect(words.map((word) => word.text)).toEqual(["one", "three", "fivefive"]);
    expect(words[0].startMs).toBe(0);
    expect(words.at(-1)!.endMs).toBe(4000);
    for (let i = 1; i < words.length; i++) expect(words[i].startMs).toBe(words[i - 1].endMs);
  });
});
