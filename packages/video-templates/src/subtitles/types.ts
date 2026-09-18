/** Serializable Subtitle Studio composition props: the browser Player and the server
 * renderer receive exactly this object, so preview and export cannot drift apart. */
export type SubtitlePreset = 'modern' | 'classic' | 'impact' | 'editorial';
export type SubtitlePosition = 'top' | 'center' | 'bottom';
export type SubtitleSize = 'small' | 'medium' | 'large';
export type SubtitleAspectRatio = '9:16' | '16:9';

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

// A type alias, not an interface: Remotion's Composition requires props assignable to
// Record<string, unknown>, which interfaces are not.
export type SubtitleCompositionProps = {
  sourceUrl: string;
  cues: SubtitleCue[];
  preset: SubtitlePreset;
  position: SubtitlePosition;
  size: SubtitleSize;
  safeArea: boolean;
  textColor: string;
  highlightColor: string;
  /** The browser preview may mute; an export keeps the source audio. */
  muted?: boolean;
  /** Frame size of the uploaded file; portrait footage switches captions to short pages. */
  sourceWidth?: number | null;
  sourceHeight?: number | null;
};

export const SUBTITLE_COMPOSITION_ID = 'SubtitleStudio';
export const SUBTITLE_FPS = 30;
export const subtitleDimensions: Record<SubtitleAspectRatio, {width: number; height: number}> = {
  '9:16': {width: 1080, height: 1920},
  '16:9': {width: 1920, height: 1080},
};
