"use client";

import type { SubtitleSharedExport } from "@ugc/contracts";
import { Download } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getServices } from "@/services";
import { ServiceError } from "@/services/http";

/** Public, unauthenticated viewer for a revocable share link. Anyone with the URL lands here
 * directly, without the editor, the owner's project list, or any credential. */
export function SharedSubtitleVideo({ token }: { token: string }) {
  const [state, setState] = useState<
    { status: "loading" } | { status: "ready"; export: SubtitleSharedExport } | { status: "error"; message: string }
  >({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    getServices()
      .subtitleProjects.getShared(token)
      .then(({ export: shared }) => {
        if (!cancelled) setState({ status: "ready", export: shared });
      })
      .catch((error) => {
        if (cancelled) return;
        const message =
          error instanceof ServiceError
            ? "This share link is unavailable. It may have been revoked."
            : "This share link could not be loaded.";
        setState({ status: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="shared-video-page">
      {state.status === "loading" && <p className="shared-video-status">Loading video…</p>}
      {state.status === "error" && <p className="shared-video-status">{state.message}</p>}
      {state.status === "ready" && (
        <div className="shared-video-card" data-ratio={state.export.aspectRatio}>
          {state.export.outputAsset ? (
            <video
              className="shared-video-player"
              src={state.export.outputAsset.url}
              controls
              autoPlay
              playsInline
            />
          ) : (
            <p className="shared-video-status">This video is unavailable.</p>
          )}
          {state.export.outputAsset && (
            <a className="button button-primary" href={state.export.outputAsset.url} download>
              <Download size={17} /> Download
            </a>
          )}
        </div>
      )}
      <Link className="shared-video-brand" href="/subtitles">
        Made with Subtitle Studio
      </Link>
    </div>
  );
}
