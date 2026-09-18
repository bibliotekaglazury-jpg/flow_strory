"use client";

import { Shirt, Sparkles, X } from "lucide-react";
import type { TryOnAngle } from "@ugc/contracts";
import type { useCreation } from "@/hooks/use-creation";

type Creation = ReturnType<typeof useCreation>;

const ANGLES: TryOnAngle[] = [
  { id: "front", label: "Front" },
  { id: "three_quarter", label: "¾" },
  { id: "back", label: "Back" },
  { id: "detail", label: "Detail" },
];

export function TryOnPanel({ c, onVideo }: { c: Creation; onVideo: () => void }) {
  if (!c.tryOn.open) return null;
  const busy = c.busy === "try-on";
  const photo = c.tryOn.result;
  return (
    <section className="try-on-panel" aria-labelledby="try-on-title">
      <div className="try-on-head">
        <h3 id="try-on-title">
          <Shirt size={15} aria-hidden="true" /> Try-on
        </h3>
        <button type="button" onClick={c.closeTryOn} aria-label="Close try-on">
          <X size={14} />
        </button>
      </div>
      <p className="try-on-hint">
        {c.tryOn.pieces} pieces on your model, worn together. Check the look before
        spending a video on it.
      </p>
      <div className="try-on-stage" data-busy={busy || undefined}>
        {photo ? (
          <img src={photo.url} alt="Your model wearing the look" />
        ) : (
          <span className="try-on-empty">
            {busy ? "Dressing your model…" : "No preview yet"}
          </span>
        )}
      </div>
      <button
        className="button button-primary try-on-generate"
        type="button"
        disabled={busy || !!c.busy}
        onClick={() => void c.tryOnPhoto()}
      >
        <Sparkles size={14} /> {photo ? "Try again" : "Generate preview photo"}
      </button>
      {photo && (
        <>
          <div className="try-on-angles" role="group" aria-label="Another angle">
            {ANGLES.map((angle) => (
              <button
                key={angle.id}
                type="button"
                disabled={busy || !!c.busy}
                onClick={() => void c.tryOnPhoto(angle.id, photo.id)}
              >
                {angle.label}
              </button>
            ))}
          </div>
          <button
            className="button button-secondary"
            type="button"
            disabled={!!c.busy}
            onClick={onVideo}
          >
            Generate video with this look
          </button>
        </>
      )}
    </section>
  );
}
