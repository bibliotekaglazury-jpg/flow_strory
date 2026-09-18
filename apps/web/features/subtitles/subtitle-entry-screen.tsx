"use client";

import type { SubtitleProjectSummary } from "@ugc/contracts";
import { ArrowRight, Check, Square, SquareCheck, Trash2, Upload, Video } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getServices } from "@/services";

const DEMO_VIDEO = "/media/subtitle-studio-demo.mp4";

function formatDuration(durationMs: number) {
  const seconds = Math.max(0, Math.round(durationMs / 1000));
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function projectVideo(project: SubtitleProjectSummary) {
  return project.latestExport?.status === "completed" && project.latestExport.outputAsset?.url
    ? project.latestExport.outputAsset.url
    : project.sourceAsset.url;
}

export function SubtitleEntryScreen({
  uploading,
  notice,
  onUpload,
  onFileSelected,
}: {
  uploading: boolean;
  notice: string | null;
  onUpload: () => void;
  onFileSelected: (file: File) => void;
}) {
  const [projects, setProjects] = useState<SubtitleProjectSummary[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getServices()
      .subtitleProjects.list()
      .then(({ projects: page, nextCursor }) => {
        if (!active) return;
        setProjects(page);
        setCursor(nextCursor);
      })
      .catch(() => {
        // Upload stays available when history cannot be loaded.
        if (active) setProjects([]);
      });
    return () => {
      active = false;
    };
  }, []);

  async function loadMore() {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const { projects: page, nextCursor } = await getServices().subtitleProjects.list(cursor);
      setProjects((current) => [...(current ?? []), ...page]);
      setCursor(nextCursor);
    } catch {
      // The list already loaded stays usable; the user can just try Load more again.
    } finally {
      setLoadingMore(false);
    }
  }

  function toggleSelected(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function deleteOne(project: SubtitleProjectSummary) {
    const label = project.sourceAsset.fileName || "this video";
    if (!window.confirm(`Delete "${label}"? This can't be undone.`)) return;
    setError(null);
    setBusy((current) => new Set(current).add(project.id));
    try {
      await getServices().subtitleProjects.remove(project.id);
      setProjects((current) => (current ?? []).filter((item) => item.id !== project.id));
      setSelected((current) => {
        if (!current.has(project.id)) return current;
        const next = new Set(current);
        next.delete(project.id);
        return next;
      });
    } catch {
      setError("Couldn't delete that video. Try again.");
    } finally {
      setBusy((current) => {
        const next = new Set(current);
        next.delete(project.id);
        return next;
      });
    }
  }

  async function deleteSelected() {
    const ids = [...selected];
    if (!ids.length) return;
    if (!window.confirm(`Delete ${ids.length} video${ids.length === 1 ? "" : "s"}? This can't be undone.`))
      return;
    setError(null);
    setBusy((current) => {
      const next = new Set(current);
      for (const id of ids) next.add(id);
      return next;
    });
    const results = await Promise.allSettled(ids.map((id) => getServices().subtitleProjects.remove(id)));
    const removed = new Set(ids.filter((_, index) => results[index].status === "fulfilled"));
    setProjects((current) => (current ?? []).filter((item) => !removed.has(item.id)));
    setSelected((current) => new Set([...current].filter((id) => !removed.has(id))));
    setBusy((current) => {
      const next = new Set(current);
      for (const id of ids) next.delete(id);
      return next;
    });
    if (removed.size < ids.length) setError("Some videos couldn't be deleted. Try again.");
  }

  const list = projects ?? [];

  return (
    <section className="subtitle-entry-page" aria-label="Start a subtitle project">
      <div className="subtitle-entry-hero">
        <div className="subtitle-entry-copy">
          <span className="subtitle-entry-eyebrow">GET STARTED</span>
          <h2>Your words, ready for every screen.</h2>
          <p>
            Upload a video to create accurate captions with timestamps, edit every line,
            and download a ready-to-share video.
          </p>

          <div
            className="subtitle-upload-zone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const file = event.dataTransfer.files[0];
              if (file) onFileSelected(file);
            }}
          >
            <Video size={38} strokeWidth={1.45} aria-hidden="true" />
            <strong>Drag and drop a video file here</strong>
            <span>MP4, MOV or WebM · up to 60 minutes and 500 MB</span>
            <button
              className="button button-primary"
              type="button"
              disabled={uploading}
              onClick={onUpload}
            >
              <Upload size={17} /> {uploading ? "Uploading…" : "Upload video"}
            </button>
          </div>

          <ul className="subtitle-entry-benefits" aria-label="What you get">
            <li><Check size={13} /> Automatic timestamps</li>
            <li><Check size={13} /> Editable transcript</li>
            <li><Check size={13} /> Video and SRT ready</li>
          </ul>
          {notice && <p className="subtitle-notice" role="alert">{notice}</p>}
        </div>

        <div className="subtitle-proof">
          <p>One video. Your style. Every screen.</p>
          <svg viewBox="0 0 88 42" aria-hidden="true">
            <path d="M4 5c29 0 52 9 69 27" />
            <path d="m65 29 9 4-2-10" />
          </svg>
          <div className="subtitle-format-showcase" aria-label="Subtitle style examples">
            <article data-format="reels">
              <video src={DEMO_VIDEO} muted autoPlay loop playsInline preload="metadata" />
              <span>Great ideas <mark>deserve</mark> to be heard.</span>
              <small>Reels</small>
            </article>
            <article data-format="shorts">
              <video src={DEMO_VIDEO} muted autoPlay loop playsInline preload="metadata" />
              <span><mark>Make it clear.</mark><br />Make it memorable.</span>
              <small>Shorts</small>
            </article>
            <article data-format="stories">
              <video src={DEMO_VIDEO} muted autoPlay loop playsInline preload="metadata" />
              <span>Words that<br /><mark>move with you.</mark></span>
              <small>Stories</small>
            </article>
          </div>
        </div>
      </div>

      <div className="subtitle-recent">
        <div className="subtitle-recent-heading">
          <h2>Recent subtitle projects</h2>
          {list.length > 0 && (
            <button
              type="button"
              className="subtitle-select-toggle"
              onClick={() => {
                setSelectMode((current) => !current);
                setSelected(new Set());
              }}
            >
              {selectMode ? "Done" : "Select"}
            </button>
          )}
        </div>

        {error && <p className="subtitle-notice" role="alert">{error}</p>}

        {selectMode && (
          <div className="subtitle-bulk-bar" role="group" aria-label="Bulk actions">
            <span>{selected.size} selected</span>
            <button
              type="button"
              className="subtitle-bulk-delete"
              onClick={() => void deleteSelected()}
              disabled={!selected.size}
            >
              <Trash2 size={14} /> Delete selected
            </button>
          </div>
        )}

        {projects === null ? null : list.length > 0 ? (
          <>
            <div className="subtitle-recent-list">
              {list.map((project) => (
                <article key={project.id} className="subtitle-recent-project" data-busy={busy.has(project.id)}>
                  {selectMode && (
                    <button
                      type="button"
                      className="subtitle-select-checkbox"
                      aria-pressed={selected.has(project.id)}
                      aria-label={selected.has(project.id) ? "Deselect video" : "Select video"}
                      onClick={() => toggleSelected(project.id)}
                    >
                      {selected.has(project.id) ? <SquareCheck size={20} /> : <Square size={20} />}
                    </button>
                  )}
                  {selectMode ? (
                    <button
                      type="button"
                      className="subtitle-recent-video subtitle-recent-video-select"
                      aria-pressed={selected.has(project.id)}
                      aria-label={selected.has(project.id) ? "Deselect video" : "Select video"}
                      onClick={() => toggleSelected(project.id)}
                    >
                      <video src={projectVideo(project)} muted autoPlay loop playsInline preload="metadata" />
                      <span><mark>Ready</mark> for every screen.</span>
                      <small>{formatDuration(project.durationMs)}</small>
                    </button>
                  ) : (
                    <div className="subtitle-recent-video">
                      <video src={projectVideo(project)} muted autoPlay loop playsInline preload="metadata" />
                      <span><mark>Ready</mark> for every screen.</span>
                      <small>{formatDuration(project.durationMs)}</small>
                    </div>
                  )}
                  <div className="subtitle-recent-info">
                    <strong>{project.sourceAsset.fileName || "Subtitled video"}</strong>
                    <span>{project.aspectRatio} · {formatDate(project.updatedAt)}</span>
                  </div>
                  <div className="subtitle-recent-project-actions">
                    <Link href={`/subtitles?project=${encodeURIComponent(project.id)}`}>
                      Open editor <ArrowRight size={16} />
                    </Link>
                    <button
                      type="button"
                      className="subtitle-delete-one"
                      aria-label="Delete this video"
                      title="Delete this video"
                      onClick={() => void deleteOne(project)}
                      disabled={busy.has(project.id)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
            {cursor && (
              <button type="button" className="subtitle-load-more" onClick={() => void loadMore()} disabled={loadingMore}>
                {loadingMore ? "Loading…" : "Load more"}
              </button>
            )}
          </>
        ) : (
          <article className="subtitle-recent-project" data-example="true">
            <div className="subtitle-recent-video">
              <video src={DEMO_VIDEO} muted autoPlay loop playsInline preload="metadata" />
              <span><mark>Ready</mark> for every screen.</span>
              <small>00:15</small>
            </div>
            <div className="subtitle-recent-info">
              <strong>Captioned video example</strong>
              <span>Your projects will appear here automatically.</span>
            </div>
            <button type="button" onClick={onUpload} disabled={uploading}>
              Upload your video <ArrowRight size={16} />
            </button>
          </article>
        )}
      </div>
    </section>
  );
}
