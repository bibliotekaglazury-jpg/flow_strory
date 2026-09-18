import { describe, expect, it } from "vitest";
import {
  createHistory,
  mergeCue,
  pushHistory,
  redoHistory,
  retimeText,
  splitCue,
  undoHistory,
  validateCues,
  type SubtitleCue,
} from "../features/subtitles/editor-state";

const cues: SubtitleCue[] = [
  {
    id: "cue-1",
    startMs: 0,
    endMs: 4000,
    text: "This moisturizer keeps my skin hydrated all day.",
    words: [
      { id: "w-1", text: "This moisturizer keeps", startMs: 0, endMs: 1900 },
      { id: "w-2", text: "my skin hydrated all day.", startMs: 1900, endMs: 4000 },
    ],
  },
  {
    id: "cue-2",
    startMs: 4000,
    endMs: 8000,
    text: "It is lightweight and absorbs quickly.",
    words: [],
  },
];

describe("subtitle editor state", () => {
  it("splits the selected cue at the playhead and preserves ordered timing", () => {
    const result = splitCue(cues, "cue-1", 1900);
    expect(result).toHaveLength(3);
    expect(result.slice(0, 2).map(({ startMs, endMs, text }) => ({ startMs, endMs, text }))).toEqual([
      { startMs: 0, endMs: 1900, text: "This moisturizer keeps" },
      { startMs: 1900, endMs: 4000, text: "my skin hydrated all day." },
    ]);
    expect(validateCues(result, 8000)).toEqual([]);
  });

  it("splits an untimed cue where the playhead falls, not in the middle", () => {
    const untimed: SubtitleCue = {
      id: "cue-x",
      startMs: 0,
      endMs: 6000,
      text: "one two three four five six",
      words: [],
    };
    const [first, second] = splitCue([untimed], "cue-x", 1500);
    expect(first.text).toBe("one two");
    expect(second.text).toBe("three four five six");
    expect(first.endMs).toBe(1500);
  });

  it("keeps word timings when a word is corrected in place and drops them for a rewrite", () => {
    const timed: SubtitleCue = {
      id: "t",
      startMs: 0,
      endMs: 1000,
      text: "Klienci znajduja",
      words: [
        { id: "a", text: "Klienci", startMs: 0, endMs: 400 },
        { id: "b", text: "znajduja", startMs: 450, endMs: 1000 },
      ],
    };
    const corrected = retimeText(timed, "Klienci znajdują");
    expect(corrected.words.map((word) => [word.text, word.startMs, word.endMs])).toEqual([
      ["Klienci", 0, 400],
      ["znajdują", 450, 1000],
    ]);
    expect(retimeText(timed, "Nowi klienci szukają").words).toEqual([]);
  });

  it("refuses a split that would create a cue shorter than 250ms", () => {
    expect(() => splitCue(cues, "cue-1", 100)).toThrow("at least 250ms");
  });

  it("merges a cue with the next cue", () => {
    const result = mergeCue(cues, "cue-1");
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      startMs: 0,
      endMs: 8000,
      text: "This moisturizer keeps my skin hydrated all day. It is lightweight and absorbs quickly.",
    });
  });

  it("reports empty, overlapping and out-of-range cues", () => {
    expect(
      validateCues(
        [
          { ...cues[0], text: "", endMs: 5000 },
          { ...cues[1], startMs: 4500, endMs: 9000 },
        ],
        8000,
      ),
    ).toEqual([
      "Cue 1 cannot be empty.",
      "Cue 2 overlaps the previous cue.",
      "Cue 2 ends after the video.",
    ]);
  });

  it("moves backward and forward through browser-session edits", () => {
    const initial = createHistory(cues);
    const changed = cues.map((cue, index) =>
      index === 0 ? { ...cue, text: "Updated caption" } : cue,
    );
    const pushed = pushHistory(initial, changed);
    const undone = undoHistory(pushed);
    expect(undone.present[0].text).toBe(cues[0].text);
    const redone = redoHistory(undone);
    expect(redone.present[0].text).toBe("Updated caption");
  });
});
