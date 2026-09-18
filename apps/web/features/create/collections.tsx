"use client";

import { type FocusEvent, useRef, useState } from "react";
import Link from "next/link";
import { featuredTemplates } from "@/services/template-filters";
import { templateArtwork } from "@/services/template-visuals";
import { toggleVideoSound } from "@/services/history-video";
import { recentCompletedVideos } from "@/services/history-filter";
import { ArrowRight, Clock3, RefreshCw, Square, SquareCheck, Trash2, Volume2, VolumeX } from "lucide-react";
import type { Generation, VideoTemplate } from "@ugc/contracts";
function outputVideo(generation: Generation) {
  return generation.outputAssets.find(
    (asset) => asset.role === "output_video" && asset.kind === "video" && asset.url,
  );
}

function HistoryVideoCard({
  generation,
  template,
  onOpen,
  onRecreate,
  selectMode,
  selected,
  onToggleSelect,
  onDelete,
  deleting,
}: {
  generation: Generation;
  template: VideoTemplate | undefined;
  onOpen: (id: string) => void;
  onRecreate: (generation: Generation) => void;
  selectMode: boolean;
  selected: boolean;
  onToggleSelect?: (id: string) => void;
  onDelete?: (generation: Generation) => void;
  deleting: boolean;
}) {
  const video = outputVideo(generation);
  const poster = generation.outputAssets.find((asset) => asset.role === "thumbnail");
  const cardRef = useRef<HTMLElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [muted, setMuted] = useState(true);

  if (!video) return null;

  const play = () => {
    const node = videoRef.current;
    if (!node) return;
    node.play().catch(() => undefined);
  };

  const pause = () => {
    const node = videoRef.current;
    if (!node) return;
    node.pause();
    node.currentTime = 0;
  };

  const pauseWhenFocusLeavesCard = (event: FocusEvent<HTMLElement>) => {
    if (event.relatedTarget instanceof Node && cardRef.current?.contains(event.relatedTarget)) {
      return;
    }
    pause();
  };

  const toggleSound = () => {
    const node = videoRef.current;
    if (!node) return;
    setMuted(toggleVideoSound(node, muted));
  };

  return (
    <article
      ref={cardRef}
      className="history-card"
      data-testid="history-item"
      data-busy={deleting}
      onMouseEnter={play}
      onMouseLeave={pause}
      onFocus={play}
      onBlur={pauseWhenFocusLeavesCard}
    >
      <button
        className="history-open"
        type="button"
        aria-pressed={selectMode ? selected : undefined}
        aria-label={
          selectMode ? (selected ? "Deselect video" : "Select video") : undefined
        }
        onClick={() =>
          selectMode ? onToggleSelect?.(generation.id) : onOpen(generation.id)
        }
      >
        <div className="history-video-frame">
          <video
            ref={videoRef}
            src={video.url}
            poster={poster?.url}
            muted={muted}
            loop
            playsInline
            preload="metadata"
          />
          <span className="history-duration">{generation.duration}s</span>
        </div>
      </button>
      {selectMode ? (
        <span className="history-select-mark" aria-hidden="true">
          {selected ? <SquareCheck size={16} /> : <Square size={16} />}
        </span>
      ) : (
        <>
          <button
            className="history-sound"
            type="button"
            aria-label={muted ? "Turn sound on" : "Turn sound off"}
            aria-pressed={!muted}
            onClick={toggleSound}
          >
            {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
          </button>
          {onDelete && (
            <button
              className="history-delete"
              type="button"
              aria-label="Delete this video"
              title="Delete this video"
              onClick={() => onDelete(generation)}
              disabled={deleting}
            >
              <Trash2 size={14} />
            </button>
          )}
        </>
      )}
      <div className="history-meta">
        <strong>{template?.name || "Video"}</strong>
        <span>{generation.status}</span>
      </div>
      {generation.creativeMechanism ? (
        <button
          className="history-recreate"
          type="button"
          onClick={() => onRecreate(generation)}
        >
          <RefreshCw size={14} /> Recreate with my product
        </button>
      ) : null}
      <time dateTime={generation.createdAt}>
        {new Date(generation.createdAt).toLocaleString()}
      </time>
    </article>
  );
}

export function Collections({
  templates,
  history,
  onTemplate,
  onOpen,
  onRecreate,
  onDelete,
}: {
  templates: VideoTemplate[];
  history: Generation[];
  onTemplate: (id: string) => void;
  onOpen: (id: string) => void;
  onRecreate: (generation: Generation) => void;
  /** Only the Library page passes this; the homepage teaser stays browse-only. */
  onDelete?: (ids: string[]) => Promise<void>;
}) {
  const displayedHistory = recentCompletedVideos(history);
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  function toggleSelected(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function deleteOne(generation: Generation) {
    if (!onDelete) return;
    if (!window.confirm("Delete this video? This can't be undone.")) return;
    setError(null);
    setBusy((current) => new Set(current).add(generation.id));
    try {
      await onDelete([generation.id]);
    } catch {
      setError("Couldn't delete that video. Try again.");
    } finally {
      setBusy((current) => {
        const next = new Set(current);
        next.delete(generation.id);
        return next;
      });
    }
  }

  async function deleteSelected() {
    if (!onDelete || !selected.size) return;
    const ids = [...selected];
    if (!window.confirm(`Delete ${ids.length} video${ids.length === 1 ? "" : "s"}? This can't be undone.`))
      return;
    setError(null);
    setBusy((current) => {
      const next = new Set(current);
      for (const id of ids) next.add(id);
      return next;
    });
    try {
      await onDelete(ids);
      setSelected(new Set());
    } catch {
      setError("Some videos couldn't be deleted. Try again.");
    } finally {
      setBusy((current) => {
        const next = new Set(current);
        for (const id of ids) next.delete(id);
        return next;
      });
    }
  }

  return (
    <div className="collections">
      <section id="templates">
        <div className="section-heading">
          <h2>Recommended</h2>
          <Link href="/templates">
            View all templates <ArrowRight size={16} />
          </Link>
        </div>
        <div className="template-gallery">
          {featuredTemplates(templates).map((t) => {
            const artwork = templateArtwork(t);
            return <button
              key={t.id}
              disabled={!t.available}
              onClick={() => {
                onTemplate(t.id);
                document
                  .getElementById("create")
                  ?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              {artwork ? (
                <img src={artwork} alt="" />
              ) : (
                <span className="image-placeholder" />
              )}
              <strong>{t.name}</strong>
              <span>{t.description}</span>
            </button>;
          })}
        </div>
      </section>
      <section id="history">
        <div className="section-heading">
          <h2>Recent Creations</h2>
          {onDelete && displayedHistory.length > 0 ? (
            <button
              type="button"
              className="history-select-toggle"
              onClick={() => {
                setSelectMode((current) => !current);
                setSelected(new Set());
              }}
            >
              {selectMode ? "Done" : "Select"}
            </button>
          ) : (
            <span className="quiet-caption">Your latest stories</span>
          )}
        </div>
        {error && (
          <p className="history-notice" role="alert">
            {error}
          </p>
        )}
        {selectMode && (
          <div className="history-bulk-bar" role="group" aria-label="Bulk actions">
            <span>{selected.size} selected</span>
            <button
              type="button"
              className="history-bulk-delete"
              onClick={() => void deleteSelected()}
              disabled={!selected.size}
            >
              <Trash2 size={14} /> Delete selected
            </button>
          </div>
        )}
        {displayedHistory.length ? (
          <div className="history-grid">
            {displayedHistory.map((generation) => (
              <HistoryVideoCard
                key={generation.id}
                generation={generation}
                template={templates.find((t) => t.id === generation.templateId)}
                onOpen={onOpen}
                onRecreate={onRecreate}
                selectMode={selectMode}
                selected={selected.has(generation.id)}
                onToggleSelect={toggleSelected}
                onDelete={onDelete ? deleteOne : undefined}
                deleting={busy.has(generation.id)}
              />
            ))}
          </div>
        ) : (
          <div className="history-empty">
            <Clock3 size={18} />
            <span>Completed videos will appear here.</span>
          </div>
        )}
      </section>
    </div>
  );
}
