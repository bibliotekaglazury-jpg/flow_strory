import { describe, expect, it, vi } from "vitest";
import {
  mediaUrlRefreshDelay,
  toggleVideoSound,
} from "../services/history-video";

describe("toggleVideoSound", () => {
  it("unmutes the media element immediately and keeps it playing", () => {
    const play = vi.fn().mockResolvedValue(undefined);
    const media = {
      muted: true,
      volume: 0,
      play,
    };

    expect(toggleVideoSound(media, true)).toBe(false);
    expect(media.muted).toBe(false);
    expect(media.volume).toBe(1);
    expect(play).toHaveBeenCalledOnce();
  });
});

describe("mediaUrlRefreshDelay", () => {
  it("refreshes a signed media URL before it expires", () => {
    expect(
      mediaUrlRefreshDelay("2026-09-12T01:15:00.000Z", Date.parse("2026-09-12T01:00:00.000Z")),
    ).toBe(840_000);
  });

  it("refreshes immediately when the signed URL is already near expiry", () => {
    expect(
      mediaUrlRefreshDelay("2026-09-12T01:00:20.000Z", Date.parse("2026-09-12T01:00:00.000Z")),
    ).toBe(0);
  });
});
