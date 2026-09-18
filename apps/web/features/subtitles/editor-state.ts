export interface SubtitleWord {
  id: string;
  text: string;
  startMs: number;
  endMs: number;
}

export interface SubtitleCue {
  id: string;
  startMs: number;
  endMs: number;
  text: string;
  words: SubtitleWord[];
}

export interface EditorHistory {
  past: SubtitleCue[][];
  present: SubtitleCue[];
  future: SubtitleCue[][];
}

const MIN_CUE_MS = 250;

function copy(cues: SubtitleCue[]) {
  return cues.map((cue) => ({
    ...cue,
    words: cue.words.map((word) => ({ ...word })),
  }));
}

export function validateCues(cues: SubtitleCue[], durationMs: number) {
  const errors: string[] = [];
  cues.forEach((cue, index) => {
    const number = index + 1;
    if (!cue.text.trim()) errors.push(`Cue ${number} cannot be empty.`);
    if (index > 0 && cue.startMs < cues[index - 1].endMs)
      errors.push(`Cue ${number} overlaps the previous cue.`);
    if (cue.endMs > durationMs)
      errors.push(`Cue ${number} ends after the video.`);
    if (cue.startMs < 0 || cue.endMs - cue.startMs < MIN_CUE_MS)
      errors.push(`Cue ${number} must be at least 250ms.`);
  });
  return errors;
}

/** Word timings for a cue after its text is edited. Correcting words in place (same number of
 * words) keeps every timestamp; rewriting the sentence drops them rather than guessing. */
export function retimeText(cue: SubtitleCue, text: string): SubtitleCue {
  const tokens = text.trim().split(/\s+/).filter(Boolean);
  const sameShape =
    cue.words.length > 0 &&
    tokens.length === cue.words.length &&
    cue.words.every((word) => !/\s/.test(word.text.trim()));
  return {
    ...cue,
    text,
    words: sameShape ? cue.words.map((word, index) => ({ ...word, text: tokens[index] })) : [],
  };
}

/** Where each word of an untimed cue falls, spread across the cue by word length. Used only to
 * decide which words land on either side of a split, never stored as a transcript timestamp. */
function pacedBoundaries(cue: SubtitleCue) {
  const tokens = cue.text.trim().split(/\s+/).filter(Boolean);
  const total = tokens.reduce((sum, token) => sum + token.length, 0) || 1;
  let cursor = cue.startMs;
  return tokens.map((token) => {
    const startMs = cursor;
    cursor += ((cue.endMs - cue.startMs) * token.length) / total;
    return { token, midMs: (startMs + cursor) / 2 };
  });
}

export function splitCue(
  cues: SubtitleCue[],
  selectedId: string,
  playheadMs: number,
) {
  const index = cues.findIndex((cue) => cue.id === selectedId);
  if (index < 0) throw new Error("Select a caption to split.");
  const cue = cues[index];
  if (
    playheadMs - cue.startMs < MIN_CUE_MS ||
    cue.endMs - playheadMs < MIN_CUE_MS
  )
    throw new Error("Each caption must be at least 250ms.");

  const beforeWords = cue.words.filter((word) => word.endMs <= playheadMs);
  const afterWords = cue.words.filter((word) => word.startMs >= playheadMs);
  // Without word timings the text used to be cut in half wherever the playhead was; split it
  // where the playhead actually falls instead, keeping at least one word on each side.
  const paced = pacedBoundaries(cue);
  const pacedSplit = Math.min(
    Math.max(1, paced.filter((word) => word.midMs < playheadMs).length),
    Math.max(1, paced.length - 1),
  );
  const beforeText = beforeWords.length
    ? beforeWords.map((word) => word.text).join(" ")
    : paced.slice(0, pacedSplit).map((word) => word.token).join(" ");
  const afterText = afterWords.length
    ? afterWords.map((word) => word.text).join(" ")
    : paced.slice(pacedSplit).map((word) => word.token).join(" ");

  return [
    ...copy(cues.slice(0, index)),
    { ...cue, endMs: playheadMs, text: beforeText, words: beforeWords },
    {
      ...cue,
      id: `${cue.id}-split-${playheadMs}`,
      startMs: playheadMs,
      text: afterText,
      words: afterWords,
    },
    ...copy(cues.slice(index + 1)),
  ];
}

export function mergeCue(cues: SubtitleCue[], selectedId: string) {
  const index = cues.findIndex((cue) => cue.id === selectedId);
  if (index < 0 || index === cues.length - 1)
    throw new Error("Select a caption with another caption after it.");
  const current = cues[index];
  const next = cues[index + 1];
  const merged: SubtitleCue = {
    ...current,
    endMs: next.endMs,
    text: `${current.text.trim()} ${next.text.trim()}`,
    words: [...current.words, ...next.words],
  };
  return [
    ...copy(cues.slice(0, index)),
    merged,
    ...copy(cues.slice(index + 2)),
  ];
}

export function createHistory(cues: SubtitleCue[]): EditorHistory {
  return { past: [], present: copy(cues), future: [] };
}

export function pushHistory(
  history: EditorHistory,
  next: SubtitleCue[],
): EditorHistory {
  return {
    past: [...history.past, copy(history.present)].slice(-50),
    present: copy(next),
    future: [],
  };
}

export function undoHistory(history: EditorHistory): EditorHistory {
  const previous = history.past.at(-1);
  if (!previous) return history;
  return {
    past: history.past.slice(0, -1),
    present: copy(previous),
    future: [copy(history.present), ...history.future],
  };
}

export function redoHistory(history: EditorHistory): EditorHistory {
  const next = history.future[0];
  if (!next) return history;
  return {
    past: [...history.past, copy(history.present)],
    present: copy(next),
    future: history.future.slice(1),
  };
}
