import React, { useEffect, useMemo, useRef, useState } from "react";
import { fillTextBox } from "@remotion/layout-utils";
import { AbsoluteFill, OffthreadVideo, getRemotionEnvironment, useCurrentFrame, useDelayRender, useVideoConfig } from "remotion";
import type { SubtitleCompositionProps, SubtitleCue, SubtitlePosition, SubtitleSize } from "./types";

// The body between the shared-composition markers is byte-identical to
// apps/web/features/subtitles/subtitle-composition.tsx (enforced by a web unit test), so the
// browser Player and the server export render the same captions.
// shared-composition:start
const positionStyles: Record<SubtitlePosition, React.CSSProperties> = {
  top: { justifyContent: "flex-start", paddingTop: "12%" },
  center: { justifyContent: "center" },
  bottom: { justifyContent: "flex-end", paddingBottom: "12%" },
};

const sizeStyles: Record<SubtitleSize, number> = {
  small: 48,
  medium: 64,
  large: 84,
};

// A vertical page holds at most this many lines; the next word that would not fit starts a page.
const VERTICAL_MAX_LINES = 2;

type TimedWord = { text: string; startMs: number; endMs: number };
export type CaptionPage = { id: string; startMs: number; endMs: number; words: TimedWord[] };

/** Word timings of a cue. Transcribed words keep their real timestamps; text the user rewrote
 * has none, so its span is shared out by word length. That is display pacing only. */
export function timedWords(cue: SubtitleCue): TimedWord[] {
  if (cue.words.length)
    return cue.words.map((word) => ({ text: word.text, startMs: word.startMs, endMs: word.endMs }));
  const spoken = cue.text.trim().split(/\s+/).filter(Boolean);
  const total = spoken.reduce((sum, word) => sum + word.length, 0) || 1;
  let cursor = cue.startMs;
  return spoken.map((word, index) => {
    const startMs = cursor;
    cursor =
      index === spoken.length - 1
        ? cue.endMs
        : cursor + ((cue.endMs - cue.startMs) * word.length) / total;
    return { text: word, startMs: Math.round(startMs), endMs: Math.round(cursor) };
  });
}

/** Vertical footage gets short pages: words join a page while it still fits the picture and a
 * word is never split. Horizontal footage keeps one ordinary subtitle per cue. */
export function captionPages(
  cues: SubtitleCue[],
  vertical: boolean,
  fits: (words: string[]) => boolean,
): CaptionPage[] {
  const pages: CaptionPage[] = [];
  for (const cue of cues) {
    const words = timedWords(cue);
    if (!vertical || words.length < 2) {
      pages.push({ id: cue.id, startMs: cue.startMs, endMs: cue.endMs, words });
      continue;
    }
    let pageStart = cue.startMs;
    let current: TimedWord[] = [];
    for (const word of words) {
      if (current.length && !fits([...current, word].map((item) => item.text))) {
        pages.push({ id: `${cue.id}-${pages.length}`, startMs: pageStart, endMs: word.startMs, words: current });
        pageStart = word.startMs;
        current = [];
      }
      current.push(word);
    }
    pages.push({ id: `${cue.id}-${pages.length}`, startMs: pageStart, endMs: cue.endMs, words: current });
  }
  return pages;
}

export function SubtitleComposition({
  sourceUrl,
  cues,
  preset,
  position,
  size,
  safeArea,
  textColor,
  highlightColor,
  muted = false,
  sourceWidth = null,
  sourceHeight = null,
}: SubtitleCompositionProps) {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const nowMs = (frame / fps) * 1000;
  // The layout follows the uploaded file: portrait footage gets short pages, anything else keeps
  // ordinary subtitles. Either way the text stays on the picture, never on letterbox bars.
  const vertical = !!sourceWidth && !!sourceHeight && sourceHeight > sourceWidth;
  const sourceRatio = sourceWidth && sourceHeight ? sourceWidth / sourceHeight : width / height;
  const pictureWidth = Math.min(width, height * sourceRatio);
  const pictureHeight = pictureWidth / sourceRatio;
  const fontSize = Math.round(sizeStyles[size] * Math.min(1, pictureWidth / 1080));
  const fontFamily =
    preset === "editorial" ? "Instrument Serif, Georgia, serif" : "Inter, Arial, sans-serif";
  const fontWeight = preset === "classic" || preset === "editorial" ? 500 : 800;
  const letterSpacing = preset === "impact" ? "0.015em" : "-0.02em";
  const textTransform = preset === "impact" ? "uppercase" : "none";
  const boxPadding = preset === "modern" ? fontSize * 0.72 : 0;
  // fillTextBox measures without letter-spacing, so the wider-tracked Impact style keeps a margin.
  const maxBoxWidth =
    pictureWidth * (safeArea ? 0.84 : 0.94) * (preset === "impact" ? 0.95 : 1) - boxPadding;

  // Pages are measured with the real caption font. A server render must not capture any frame
  // before that font is loaded and the pages are re-measured with it: frames taken earlier showed
  // one overflowing line. The hold is requested during the first render, before any capture.
  const { delayRender, continueRender } = useDelayRender();
  const primaryFont = preset === "editorial" ? '"Instrument Serif"' : "Inter";
  const fontKey = `${fontWeight} ${fontSize}px ${primaryFont}`;
  const [fontHold] = useState(() =>
    getRemotionEnvironment().isRendering ? delayRender("Loading caption fonts") : null,
  );
  const released = useRef(false);
  const [loadedFont, setLoadedFont] = useState<string | null>(null);
  const sampleText = useMemo(() => cues.map((cue) => cue.text).join(" ").slice(0, 2000) || "Aa", [cues]);
  useEffect(() => {
    let active = true;
    document.fonts
      .load(fontKey, sampleText)
      .catch(() => undefined)
      .then(() => document.fonts.ready)
      .then(() => {
        if (active) setLoadedFont(fontKey);
      });
    return () => {
      active = false;
    };
  }, [fontKey, sampleText]);
  useEffect(() => {
    // Runs after the re-measured pages are committed, so the released frame shows them.
    if (fontHold === null || released.current || loadedFont !== fontKey) return;
    released.current = true;
    continueRender(fontHold);
  }, [fontHold, loadedFont, fontKey, continueRender]);

  const pages = useMemo(() => {
    const fits = (texts: string[]) => {
      const box = fillTextBox({ maxBoxWidth, maxLines: VERTICAL_MAX_LINES });
      return texts.every(
        (text) =>
          !box.add({
            text: `${text} `,
            fontFamily,
            fontSize,
            fontWeight: String(fontWeight),
            textTransform,
          }).exceedsBox,
      );
    };
    return captionPages(cues, vertical, fits);
    // loadedFont is not read here, but a newly loaded font changes every measurement.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cues, vertical, loadedFont, maxBoxWidth, fontFamily, fontSize, fontWeight, textTransform]);

  const page = pages.find((item) => nowMs >= item.startMs && nowMs < item.endMs);
  const activeIndex = page
    ? page.words.findIndex((word) => nowMs >= word.startMs && nowMs < word.endMs)
    : -1;

  return (
    <AbsoluteFill style={{ backgroundColor: "#071117" }}>
      {sourceUrl ? (
        <OffthreadVideo
          src={sourceUrl}
          muted={muted}
          style={{ width: "100%", height: "100%", objectFit: "contain" }}
        />
      ) : null}
      <div
        data-caption-mode={vertical ? "vertical" : "horizontal"}
        style={{
          position: "absolute",
          left: (width - pictureWidth) / 2,
          top: (height - pictureHeight) / 2,
          width: pictureWidth,
          height: pictureHeight,
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          ...positionStyles[position],
          alignItems: "center",
          paddingInline: safeArea ? "8%" : "3%",
          pointerEvents: "none",
        }}
      >
        {page && (
          <div
            data-preset={preset}
            style={{
              boxSizing: "border-box",
              maxWidth: "100%",
              overflowWrap: "normal",
              // Even line lengths instead of one orphaned word on the last line.
              textWrap: "balance",
              textAlign: "center",
              color: textColor,
              fontFamily,
              fontSize,
              fontWeight,
              lineHeight: 1.12,
              letterSpacing,
              textTransform,
              textShadow:
                preset === "classic" || preset === "editorial"
                  ? "0 2px 8px rgba(0,0,0,.88), 0 0 2px rgba(0,0,0,.95)"
                  : "none",
            }}
          >
            {/* The background sits on an inline wrapper, so it hugs the rendered words even
                when a highlighted word or a late font swap changes their width. */}
            <span
              style={{
                background: preset === "modern" ? "rgba(5,10,14,.84)" : "transparent",
                borderRadius: preset === "modern" ? "0.22em" : 0,
                padding: preset === "modern" ? "0.2em 0.36em" : 0,
                boxDecorationBreak: "clone",
                WebkitBoxDecorationBreak: "clone",
              }}
            >
              {page.words.map((word, index) => {
                const active = index === activeIndex;
                return (
                  // A real space between words: adjacent spans with only a margin between them
                  // form one unbreakable run, so long captions never wrapped and ran off the frame.
                  <span key={`${page.id}-${index}`}>
                    {index > 0 ? " " : null}
                    <span
                      style={{
                        color: active && preset !== "impact" ? highlightColor : textColor,
                        background: active && preset === "impact" ? highlightColor : "transparent",
                        padding: active && preset === "impact" ? "0 .12em" : 0,
                      }}
                    >
                      {word.text}
                    </span>
                  </span>
                );
              })}
            </span>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
}
// shared-composition:end
