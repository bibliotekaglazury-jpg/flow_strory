type SoundMedia = Pick<HTMLVideoElement, "muted" | "volume" | "play">;

const MEDIA_URL_REFRESH_HEADROOM_MS = 60_000;

export function toggleVideoSound(media: SoundMedia, isMuted: boolean) {
  const nextMuted = !isMuted;
  media.muted = nextMuted;
  media.volume = 1;
  media.play().catch(() => undefined);
  return nextMuted;
}

export function mediaUrlRefreshDelay(expiresAt: string, now = Date.now()) {
  const expiry = Date.parse(expiresAt);
  if (Number.isNaN(expiry)) return null;
  return Math.max(0, expiry - now - MEDIA_URL_REFRESH_HEADROOM_MS);
}
