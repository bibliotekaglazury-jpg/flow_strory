"use client";

import { Player, type PlayerRef } from "@remotion/player";
import type {
  SubtitleExport,
  SubtitleProject,
  SubtitleProjectUpdate,
} from "@ugc/contracts";
import {
  ArrowLeft,
  Check,
  Copy,
  Download,
  Maximize,
  Merge,
  Pause,
  Pencil,
  Play,
  Redo2,
  RotateCcw,
  Scissors,
  Send,
  Share2,
  Sparkles,
  Trash2,
  Undo2,
  Upload,
  Volume2,
  X as XIconClose,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  EmailIcon,
  EmailShareButton,
  FacebookIcon,
  FacebookShareButton,
  LinkedinIcon,
  LinkedinShareButton,
  TelegramIcon,
  TelegramShareButton,
  WhatsappIcon,
  WhatsappShareButton,
  XIcon,
  XShareButton,
} from "react-share";
import { getServices } from "@/services";
import {
  createHistory,
  mergeCue,
  pushHistory,
  redoHistory,
  retimeText,
  splitCue,
  undoHistory,
  type SubtitleCue,
} from "./editor-state";
import {
  SubtitleComposition,
  type SubtitlePosition,
  type SubtitlePreset,
  type SubtitleSize,
} from "./subtitle-composition";
import { SubtitleEntryScreen } from "./subtitle-entry-screen";

type Ratio = "9:16" | "16:9";

const FPS = 30;
// Edits save this long after the last change; the server stays the source of truth.
const AUTOSAVE_MS = 700;

const presets: { id: SubtitlePreset; label: string; sample: string }[] = [
  { id: "modern", label: "Modern", sample: "The quick brown fox jumps over" },
  { id: "classic", label: "Classic", sample: "The quick brown fox jumps over" },
  { id: "impact", label: "Impact", sample: "THE QUICK BROWN FOX JUMPS OVER" },
  { id: "editorial", label: "Editorial", sample: "The quick brown fox jumps over" },
];

function formatTime(ms: number) {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong. Try again.";
}

function codeOf(error: unknown) {
  return (error as { code?: string } | null)?.code;
}

function snapshotKey(value: Omit<SubtitleProjectUpdate, "revision">) {
  const { style } = value;
  return JSON.stringify({
    aspectRatio: value.aspectRatio,
    cues: value.cues,
    style: {
      preset: style.preset,
      position: style.position,
      size: style.size,
      safeArea: style.safeArea,
      textColor: style.textColor,
      highlightColor: style.highlightColor,
    },
  });
}

export function SubtitleStudio() {
  const router = useRouter();
  const requestedId = useSearchParams().get("project");
  const player = useRef<PlayerRef>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [project, setProject] = useState<SubtitleProject | null>(null);
  const [loadFailed, setLoadFailed] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  // The chosen file plays locally at once; upload and transcription run behind it.
  const [pendingUpload, setPendingUpload] = useState<{
    url: string;
    fileName: string;
    durationMs: number;
    width: number | null;
    height: number | null;
    progress: number;
    failed: boolean;
  } | null>(null);
  const lastFile = useRef<File | null>(null);
  const leavingProject = useRef(false);
  const [history, setHistory] = useState(() => createHistory([]));
  const [selectedId, setSelectedId] = useState("");
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  // One URL per source file for the whole session. The API signs a new link on every read,
  // and swapping it reloaded the video on each poll and autosave: the preview flickered,
  // jumped back to 0 and stopped. It is replaced only for a different file or a dead link.
  const [media, setMedia] = useState<{
    assetId: string;
    url: string;
    width: number | null;
    height: number | null;
  } | null>(null);
  const localUrls = useRef<string[]>([]);
  const [ratio, setRatio] = useState<Ratio>("9:16");
  const [preset, setPreset] = useState<SubtitlePreset>("modern");
  const [position, setPosition] = useState<SubtitlePosition>("bottom");
  const [size, setSize] = useState<SubtitleSize>("medium");
  const [safeArea, setSafeArea] = useState(true);
  const [textColor, setTextColor] = useState("#FFFFFF");
  const [highlightColor, setHighlightColor] = useState("#C9FF27");
  const [saveFailed, setSaveFailed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [conflictDraft, setConflictDraft] = useState<SubtitleProjectUpdate | null>(null);
  const [exportJob, setExportJob] = useState<SubtitleExport | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [shareBusy, setShareBusy] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const [editedSinceExport, setEditedSinceExport] = useState(false);
  const revision = useRef(0);
  // Mirrored in state for rendering the save label; the ref serves async save callbacks.
  const savedKey = useRef("");
  const [confirmedKey, setConfirmedKey] = useState("");
  const saves = useRef<Promise<void>>(Promise.resolve());
  const exportPoll = useRef(2000);

  const cues = history.present;
  const editing = project?.status === "ready" && !pendingUpload;
  const durationMs = Math.max(1000, pendingUpload?.durationMs ?? project?.durationMs ?? 10000);
  const durationInFrames = Math.max(1, Math.round((durationMs / 1000) * FPS));
  const selectedIndex = Math.max(0, cues.findIndex((cue) => cue.id === selectedId));
  const selected = cues[selectedIndex];
  const nowMs = frame * (1000 / FPS);
  const activeId = cues.find((cue) => nowMs >= cue.startMs && nowMs < cue.endMs)?.id;
  const style = useMemo(
    () => ({ preset, position, size, safeArea, textColor, highlightColor }),
    [preset, position, size, safeArea, textColor, highlightColor],
  );
  const draft = useMemo(() => ({ aspectRatio: ratio, cues, style }), [ratio, cues, style]);
  const draftKey = useMemo(() => snapshotKey(draft), [draft]);
  const emptyCue = cues.some((cue) => !cue.text.trim());
  const pending = editing && draftKey !== confirmedKey;
  const exporting = exportJob?.status === "queued" || exportJob?.status === "rendering";
  const downloadUrl =
    exportJob?.status === "completed" && !editedSinceExport ? exportJob.outputAsset?.url : undefined;

  // While a new video uploads, the old project's captions must not play over it.
  const shownCues = useMemo(() => (pendingUpload ? [] : cues), [pendingUpload, cues]);
  const inputProps = useMemo(
    () => ({
      sourceUrl: pendingUpload?.url ?? media?.url ?? "",
      cues: shownCues,
      ...style,
      muted: false,
      // Orientation of the uploaded file decides the caption layout, never the export frame.
      sourceWidth: pendingUpload?.width ?? media?.width ?? null,
      sourceHeight: pendingUpload?.height ?? media?.height ?? null,
    }),
    [pendingUpload?.url, pendingUpload?.width, pendingUpload?.height, media, shownCues, style],
  );

  const adoptSource = useCallback((next: SubtitleProject, force = false) => {
    setMedia((current) =>
      !force && current?.assetId === next.sourceAsset.id
        ? current
        : {
            assetId: next.sourceAsset.id,
            url: next.sourceAsset.url,
            width: next.sourceAsset.width,
            height: next.sourceAsset.height,
          },
    );
  }, []);

  const apply = useCallback((next: SubtitleProject) => {
    setProject(next);
    adoptSource(next);
    revision.current = next.revision;
    savedKey.current = snapshotKey(next);
    setConfirmedKey(savedKey.current);
    setRatio(next.aspectRatio);
    setPreset(next.style.preset);
    setPosition(next.style.position);
    setSize(next.style.size);
    setSafeArea(next.style.safeArea);
    setTextColor(next.style.textColor);
    setHighlightColor(next.style.highlightColor);
    setHistory(createHistory(next.cues));
    setSelectedId((current) =>
      next.cues.some((cue) => cue.id === current) ? current : (next.cues[0]?.id ?? ""),
    );
    setExportJob(next.latestExport);
    setSaveFailed(false);
  }, [adoptSource]);

  // Reopen the project named in the URL, so a reload never loses work.
  useEffect(() => {
    // Back was just clicked: the URL hasn't caught up to the cleared state yet on this render.
    // Without this guard the still-stale requestedId would immediately re-fetch and re-apply
    // the very project Back just cleared, and Back would visibly do nothing.
    if (leavingProject.current) {
      if (!requestedId) leavingProject.current = false;
      return;
    }
    if (!requestedId || project?.id === requestedId) return;
    let active = true;
    getServices()
      .subtitleProjects.get(requestedId)
      .then(({ project: loaded }) => {
        if (active) apply(loaded);
      })
      .catch((error) => {
        if (!active) return;
        setLoadFailed(requestedId);
        setNotice(messageOf(error));
      });
    return () => {
      active = false;
    };
  }, [requestedId, project?.id, apply]);

  const workspaceVisible = !!project || !!pendingUpload;
  // Space plays and pauses anywhere in the studio, like any video editor. It is left alone while
  // typing in a caption or form field, where a space has to stay a space.
  useEffect(() => {
    if (!workspaceVisible) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.code !== "Space" || event.repeat || event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("textarea, select, [contenteditable='true'], input:not([type='range']):not([type='checkbox'])")) return;
      event.preventDefault();
      player.current?.toggle();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [workspaceVisible]);
  const projectId = project?.id;
  // Time, play and pause come from the player itself, not a 100 ms timer that re-rendered the
  // whole studio and let our own "playing" flag disagree with what the player was doing.
  useEffect(() => {
    const instance = player.current;
    if (!workspaceVisible || !instance) return;
    const onTime = ({ detail }: { detail: { frame: number } }) => setFrame(detail.frame);
    const onPlay = () => setPlaying(true);
    const onStop = () => setPlaying(false);
    const onError = () => {
      // A signed link can expire mid-session; fetch a fresh one and continue from here.
      if (!projectId) return;
      const resumeAt = instance.getCurrentFrame();
      getServices()
        .subtitleProjects.get(projectId)
        .then(({ project: fresh }) => {
          adoptSource(fresh, true);
          window.setTimeout(() => player.current?.seekTo(resumeAt), 0);
        })
        .catch((error) => setNotice(messageOf(error)));
    };
    instance.addEventListener("timeupdate", onTime);
    instance.addEventListener("seeked", onTime);
    instance.addEventListener("play", onPlay);
    instance.addEventListener("pause", onStop);
    instance.addEventListener("ended", onStop);
    instance.addEventListener("error", onError);
    return () => {
      instance.removeEventListener("timeupdate", onTime);
      instance.removeEventListener("seeked", onTime);
      instance.removeEventListener("play", onPlay);
      instance.removeEventListener("pause", onStop);
      instance.removeEventListener("ended", onStop);
      instance.removeEventListener("error", onError);
    };
  }, [workspaceVisible, projectId, adoptSource]);

  useEffect(() => {
    const urls = localUrls.current;
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  // Transcription runs on the server; poll until the transcript (or its failure) arrives.
  useEffect(() => {
    if (!project || project.status !== "transcribing") return;
    const timer = window.setTimeout(() => {
      getServices()
        .subtitleProjects.get(project.id)
        .then(({ project: next }) => (next.status === "transcribing" ? setProject(next) : apply(next)))
        .catch((error) => {
          setNotice(messageOf(error));
          setProject((current) => (current ? { ...current } : current));
        });
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [project, apply]);

  // Debounced autosave. Saves run one at a time and always send the last confirmed
  // revision; a stale revision reloads the server copy and offers the draft back.
  useEffect(() => {
    if (!project || project.status !== "ready" || draftKey === confirmedKey || emptyCue) return;
    const projectId = project.id;
    const body = draft;
    const key = draftKey;
    const timer = window.setTimeout(() => {
      saves.current = saves.current.then(async () => {
        if (key === savedKey.current) return;
        const services = getServices().subtitleProjects;
        try {
          const { project: saved } = await services.update(projectId, { ...body, revision: revision.current });
          revision.current = saved.revision;
          savedKey.current = key;
          setConfirmedKey(key);
          setSaveFailed(false);
          setEditedSinceExport(true);
          setProject(saved);
        } catch (error) {
          if (codeOf(error) !== "REVISION_CONFLICT") {
            setSaveFailed(true);
            setNotice(messageOf(error));
            return;
          }
          const { project: latest } = await services.get(projectId);
          apply(latest);
          setConflictDraft({ ...body, revision: latest.revision });
          setNotice("This project changed somewhere else. The latest saved version is loaded.");
        }
      });
    }, AUTOSAVE_MS);
    return () => window.clearTimeout(timer);
  }, [project, draft, draftKey, confirmedKey, emptyCue, apply]);

  // Exports render on the server; poll at the pace the API asks for until they finish.
  useEffect(() => {
    if (!project || !exportJob || (exportJob.status !== "queued" && exportJob.status !== "rendering")) return;
    const timer = window.setTimeout(() => {
      getServices()
        .subtitleProjects.getExport(project.id, exportJob.id)
        .then(({ export: next, pollAfterMs }) => {
          exportPoll.current = pollAfterMs ?? 2000;
          setExportJob({ ...next });
        })
        .catch((error) => setNotice(messageOf(error)));
    }, exportPoll.current);
    return () => window.clearTimeout(timer);
  }, [project, exportJob]);

  function commit(next: SubtitleCue[]) {
    setHistory((current) => pushHistory(current, next));
  }

  function seekFrame(target: number) {
    const instance = player.current;
    if (!instance) return;
    const next = Math.min(Math.max(0, Math.round(target)), durationInFrames - 1);
    const wasPlaying = instance.isPlaying();
    instance.seekTo(next);
    setFrame(next);
    // Picking a moment while the video plays continues playback from that moment.
    if (wasPlaying) instance.play();
  }

  // Remembers whether playback should continue once the user lets go of a scrub (slider or
  // waveform drag). Seeking mid-drag pauses the player, so asking isPlaying() on release is too late.
  const resumeAfterScrub = useRef(false);

  function startScrub() {
    resumeAfterScrub.current = player.current?.isPlaying() ?? false;
  }

  function endScrub() {
    if (resumeAfterScrub.current) player.current?.play();
    resumeAfterScrub.current = false;
  }

  function seekCue(cue: SubtitleCue) {
    setSelectedId(cue.id);
    seekFrame((cue.startMs / 1000) * FPS);
  }

  function seekFromPointer(event: React.PointerEvent<HTMLElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width));
    seekFrame(ratio * (durationInFrames - 1));
  }

  function handleSplit() {
    if (!selected) return;
    try {
      commit(splitCue(cues, selected.id, Math.round(nowMs)));
      setNotice(null);
    } catch (error) {
      setNotice(messageOf(error));
    }
  }

  function handleMerge() {
    if (!selected) return;
    try {
      commit(mergeCue(cues, selected.id));
      setNotice(null);
    } catch (error) {
      setNotice(messageOf(error));
    }
  }

  function updateText(id: string, text: string) {
    commit(cues.map((cue) => (cue.id === id ? retimeText(cue, text) : cue)));
  }

  function deleteCue(id: string) {
    if (cues.length === 1) return;
    const next = cues.filter((cue) => cue.id !== id);
    commit(next);
    if (selectedId === id) setSelectedId(next[0].id);
  }

  function restoreDraft() {
    if (!conflictDraft) return;
    commit(conflictDraft.cues);
    setRatio(conflictDraft.aspectRatio);
    setPreset(conflictDraft.style.preset);
    setPosition(conflictDraft.style.position);
    setSize(conflictDraft.style.size);
    setSafeArea(conflictDraft.style.safeArea);
    setTextColor(conflictDraft.style.textColor);
    setHighlightColor(conflictDraft.style.highlightColor);
    setConflictDraft(null);
    setNotice(null);
  }

  async function chooseVideo(file: File | undefined) {
    if (!file || uploading) return;
    lastFile.current = file;
    const url = URL.createObjectURL(file);
    localUrls.current.push(url);
    setPendingUpload({ url, fileName: file.name, durationMs: 10000, width: null, height: null, progress: 0, failed: false });
    const probe = document.createElement("video");
    probe.preload = "metadata";
    probe.onloadedmetadata = () => {
      const measured = Math.round(probe.duration * 1000);
      setPendingUpload((current) =>
        current?.url === url
          ? {
              ...current,
              durationMs: Number.isFinite(measured) && measured > 0 ? measured : current.durationMs,
              width: probe.videoWidth || null,
              height: probe.videoHeight || null,
            }
          : current,
      );
    };
    probe.src = url;
    player.current?.pause();
    player.current?.seekTo(0);
    setFrame(0);
    setUploading(true);
    setNotice(null);
    try {
      const services = getServices();
      const { asset } = await services.assets.upload(file, "source_video", undefined, (progress) =>
        setPendingUpload((current) => (current?.url === url ? { ...current, progress } : current)),
      );
      const { project: created } = await services.subtitleProjects.create(
        { sourceAssetId: asset.id, aspectRatio: ratio },
        crypto.randomUUID(),
      );
      apply(created);
      // Keep playing the local copy of this same file: switching to the stored copy would
      // reload the video and throw away the position the user is already watching.
      setMedia({
        assetId: created.sourceAsset.id,
        url,
        width: created.sourceAsset.width,
        height: created.sourceAsset.height,
      });
      setConflictDraft(null);
      setEditedSinceExport(false);
      setPendingUpload(null);
      router.replace(`/subtitles?project=${encodeURIComponent(created.id)}`, { scroll: false });
    } catch (error) {
      setPendingUpload((current) => (current?.url === url ? { ...current, failed: true } : current));
      setNotice(messageOf(error));
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function retryUpload() {
    if (lastFile.current) void chooseVideo(lastFile.current);
  }

  // Back leaves the editor entirely: this route stays mounted (only the ?project= query
  // changes), so the loaded project has to be cleared by hand or the editor would just sit
  // there showing the old video while the URL quietly changed underneath it.
  function goToStart() {
    leavingProject.current = true;
    setProject(null);
    setPendingUpload(null);
    setMedia(null);
    setExportJob(null);
    setShareOpen(false);
    setLoadFailed(null);
    setNotice(null);
    setConflictDraft(null);
    setHistory(createHistory([]));
    setSelectedId("");
    router.push("/subtitles");
  }

  async function startExport() {
    if (!project || !editing || exporting) return;
    // An export freezes the saved revision, so any save already on its way finishes first.
    await saves.current;
    if (draftKey !== savedKey.current) {
      setNotice("Your latest edits are still saving. Try downloading again in a moment.");
      return;
    }
    try {
      const { export: created } = await getServices().subtitleProjects.export(
        project.id,
        { revision: revision.current },
        crypto.randomUUID(),
      );
      exportPoll.current = 1000;
      setEditedSinceExport(false);
      setExportJob(created);
      setNotice(null);
    } catch (error) {
      setNotice(messageOf(error));
    }
  }

  const shareUrl =
    exportJob?.shareToken && typeof window !== "undefined"
      ? `${window.location.origin}/share/${exportJob.shareToken}`
      : null;

  async function createShareLink() {
    if (!project || !exportJob || shareBusy) return;
    setShareBusy(true);
    try {
      const { export: shared } = await getServices().subtitleProjects.share(project.id, exportJob.id);
      setExportJob(shared);
    } catch (error) {
      setNotice(messageOf(error));
    } finally {
      setShareBusy(false);
    }
  }

  async function revokeShareLink() {
    if (!project || !exportJob || shareBusy) return;
    setShareBusy(true);
    try {
      const { export: unshared } = await getServices().subtitleProjects.unshare(project.id, exportJob.id);
      setExportJob(unshared);
    } catch (error) {
      setNotice(messageOf(error));
    } finally {
      setShareBusy(false);
    }
  }

  async function copyShareLink() {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setShareCopied(true);
    setTimeout(() => setShareCopied(false), 2000);
  }

  async function downloadSrt() {
    if (!project || !exportJob) return;
    try {
      const { content, fileName } = await getServices().subtitleProjects.getSrt(project.id, exportJob.id);
      const blob = new Blob([content], { type: "application/x-subrip" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error) {
      setNotice(messageOf(error));
    }
  }

  async function sendVideoFile() {
    if (!downloadUrl) return;
    try {
      const response = await fetch(downloadUrl);
      const blob = await response.blob();
      const file = new File([blob], "video.mp4", { type: blob.type || "video/mp4" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: "Subtitled video" });
      } else if (navigator.share) {
        await navigator.share({ url: shareUrl ?? downloadUrl });
      }
    } catch {
      // The user cancelled the native share sheet, or the browser has no share target; not an error.
    }
  }

  const loading = !!requestedId && project?.id !== requestedId && loadFailed !== requestedId;
  const statusLabel = pendingUpload
    ? pendingUpload.failed
      ? "Upload failed"
      : `Uploading… ${pendingUpload.progress}%`
    : !project
    ? null
    : project.status === "transcribing"
      ? "Transcribing…"
      : project.status === "failed"
        ? "Transcription failed"
        : saveFailed
          ? "Not saved"
          : emptyCue
            ? "Captions cannot be empty"
            : pending
              ? "Saving…"
              : "Saved";
  const playerElement = useMemo(
    () => (
      <Player
        ref={player}
        component={SubtitleComposition}
        inputProps={inputProps}
        durationInFrames={durationInFrames}
        fps={FPS}
        compositionWidth={ratio === "9:16" ? 1080 : 1920}
        compositionHeight={ratio === "9:16" ? 1920 : 1080}
        className="subtitle-player"
        acknowledgeRemotionLicense
      />
    ),
    // Memoised so time updates re-render the controls, never the player and its video.
    [inputProps, durationInFrames, ratio],
  );
  // The button always reads "Download": what runs behind it is an implementation detail,
  // not a second concept the user has to understand. Bundling the renderer takes a while
  // before the first frame; "0%" there looked stuck, hence the unqualified "Preparing…" first.
  const exportLabel = exporting
    ? exportJob?.progress
      ? `Preparing video… ${exportJob.progress}%`
      : "Preparing video…"
    : exportJob?.status === "completed"
      ? "Download again"
      : "Download video";

  return (
    <div className={`subtitle-studio${!loading && !project && !pendingUpload ? " subtitle-studio-entry" : ""}`} id="create">
      <input
        ref={fileInput}
        hidden
        type="file"
        aria-label="Source video"
        accept="video/mp4,video/webm,video/quicktime"
        onChange={(event) => void chooseVideo(event.target.files?.[0])}
      />
      <header className="subtitle-header">
        <div className="subtitle-title-block">
          <Link
            href="/subtitles"
            className="subtitle-back"
            onClick={(event) => {
              event.preventDefault();
              goToStart();
            }}
          >
            <ArrowLeft size={17} /> Back
          </Link>
          <div className="subtitle-title-row">
            <h1>Subtitle Studio</h1>
            <p>Edit, perfect, and bring your message to life.</p>
          </div>
        </div>
      </header>

      {loading ? (
        <section className="subtitle-entry" aria-busy="true">
          <p>Loading your project…</p>
        </section>
      ) : !project && !pendingUpload ? (
        <SubtitleEntryScreen
          uploading={uploading}
          notice={notice}
          onUpload={() => fileInput.current?.click()}
          onFileSelected={(file) => void chooseVideo(file)}
        />
      ) : (
        <section className="subtitle-workspace" aria-label="Subtitle editor">
          <div className="subtitle-editor-grid" data-ratio={ratio}>
            <section className="subtitle-preview-panel" aria-label="Video preview">
              <div className="subtitle-source-bar">
                <div>
                  <strong>{pendingUpload?.fileName ?? project?.sourceAsset.fileName}</strong>
                  <span>{formatTime(durationMs)}</span>
                </div>
                <button type="button" disabled={uploading || exporting} onClick={() => fileInput.current?.click()}>
                  <Upload size={15} /> {uploading ? "Uploading…" : "Replace video"}
                </button>
              </div>
              <div className="subtitle-player-shell" data-ratio={ratio}>
                {playerElement}
              </div>
              <div className="subtitle-player-controls">
                <button type="button" aria-label={playing ? "Pause video" : "Play video"} onClick={() => player.current?.toggle()}>{playing ? <Pause size={18} /> : <Play size={18} />}</button>
                <span>{formatTime(nowMs)} / {formatTime(durationMs)}</span>
                <input aria-label="Video position" type="range" min={0} max={durationInFrames - 1} value={Math.min(frame, durationInFrames - 1)} onPointerDown={startScrub} onPointerUp={endScrub} onKeyDown={startScrub} onKeyUp={endScrub} onChange={(event) => seekFrame(Number(event.target.value))} />
                <Volume2 size={17} aria-hidden="true" />
                <button type="button" aria-label="Full screen preview" onClick={() => player.current?.requestFullscreen()}><Maximize size={17} /></button>
              </div>
              <div className="subtitle-output-bar" role="group" aria-label="Save, format and download">
                {statusLabel && (
                  <span className="subtitle-save-state" aria-live="polite"><Check size={15} /> {statusLabel}</span>
                )}
                <fieldset className="subtitle-ratio-switch">
                  <legend>Aspect ratio</legend>
                  {(["9:16", "16:9"] as Ratio[]).map((value) => (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={ratio === value}
                      disabled={uploading || (!!project && !editing)}
                      onClick={() => setRatio(value)}
                    >
                      {value}
                    </button>
                  ))}
                </fieldset>
                {downloadUrl ? (
                  <>
                    <a className="button button-primary subtitle-export" href={downloadUrl} download>
                      <Download size={17} /> Download video
                    </a>
                    <button type="button" className="button subtitle-download-srt" onClick={() => void downloadSrt()}>
                      <Download size={15} /> Download SRT
                    </button>
                    <div className="subtitle-share-anchor">
                      <button
                        className="button subtitle-share-toggle"
                        type="button"
                        aria-haspopup="dialog"
                        aria-expanded={shareOpen}
                        onClick={() => setShareOpen((open) => !open)}
                      >
                        <Share2 size={17} /> Share
                      </button>
                      {shareOpen && (
                        <div className="subtitle-share-panel" role="dialog" aria-label="Share this video">
                          <div className="subtitle-share-panel-head">
                            <span>Share this video</span>
                            <button type="button" aria-label="Close" onClick={() => setShareOpen(false)}>
                              <XIconClose size={15} />
                            </button>
                          </div>
                          {shareUrl ? (
                            <>
                              <div className="subtitle-share-link">
                                <input readOnly value={shareUrl} aria-label="Shareable link" onFocus={(e) => e.currentTarget.select()} />
                                <button type="button" onClick={() => void copyShareLink()}>
                                  <Copy size={14} /> {shareCopied ? "Copied" : "Copy"}
                                </button>
                              </div>
                              <div className="subtitle-share-icons">
                                <FacebookShareButton url={shareUrl}><FacebookIcon size={32} round /></FacebookShareButton>
                                <XShareButton url={shareUrl}><XIcon size={32} round /></XShareButton>
                                <TelegramShareButton url={shareUrl}><TelegramIcon size={32} round /></TelegramShareButton>
                                <WhatsappShareButton url={shareUrl}><WhatsappIcon size={32} round /></WhatsappShareButton>
                                <LinkedinShareButton url={shareUrl}><LinkedinIcon size={32} round /></LinkedinShareButton>
                                <EmailShareButton url={shareUrl}><EmailIcon size={32} round /></EmailShareButton>
                              </div>
                              {typeof navigator !== "undefined" && !!navigator.share && (
                                <button type="button" className="subtitle-share-native" onClick={() => void sendVideoFile()}>
                                  <Send size={15} /> Send video file…
                                </button>
                              )}
                              <button type="button" className="subtitle-share-revoke" onClick={() => void revokeShareLink()} disabled={shareBusy}>
                                Revoke link
                              </button>
                            </>
                          ) : (
                            <button type="button" className="button button-primary" onClick={() => void createShareLink()} disabled={shareBusy}>
                              {shareBusy ? "Creating link…" : "Create shareable link"}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <button
                    className="button button-primary subtitle-export"
                    type="button"
                    onClick={() => void startExport()}
                    disabled={!editing || exporting || emptyCue || !cues.length}
                  >
                    <Upload size={17} /> {exportLabel}
                  </button>
                )}
              </div>
            </section>

            <section className="subtitle-inspector" aria-label="Transcript and caption style">
              <div className="subtitle-inspector-heading">
                <h2>Transcript</h2>
                <div>
                  <button type="button" onClick={handleSplit} disabled={!editing || !selected} title="Split the selected caption in two at the playhead. Move the playhead inside the caption first; each part must stay at least 0.25 s."><Scissors size={15} /> Split</button>
                  <button type="button" onClick={handleMerge} disabled={!editing || selectedIndex >= cues.length - 1} title={selectedIndex >= cues.length - 1 ? "The last caption has nothing after it to merge with." : "Join the selected caption with the next one."}><Merge size={15} /> Merge</button>
                </div>
              </div>
              {notice && (
                <p className="subtitle-notice" role="alert">
                  {notice}{" "}
                  {conflictDraft && (
                    <button type="button" onClick={restoreDraft}><RotateCcw size={14} /> Restore my edits</button>
                  )}
                </p>
              )}
              {exportJob?.status === "failed" && (
                <p className="subtitle-notice" role="alert">
                  {exportJob.error?.message ?? "The video could not be prepared."}{" "}
                  {exportJob.error?.retryable && (
                    <button type="button" onClick={() => void startExport()}>Retry</button>
                  )}
                </p>
              )}
              {(pendingUpload || project?.status === "transcribing") && (
                <div className="subtitle-status" role="status" aria-live="polite">
                  <ol className="subtitle-status-steps">
                    <li data-state={pendingUpload ? "active" : "done"}>1. Upload</li>
                    <li data-state={pendingUpload ? "todo" : "active"}>2. Transcribe</li>
                    <li data-state="todo">3. Edit captions</li>
                  </ol>
                  <div className="subtitle-status-label">
                    <span>
                      {pendingUpload
                        ? pendingUpload.failed
                          ? "Upload failed"
                          : "Uploading video…"
                        : "Transcribing speech…"}
                    </span>
                    {pendingUpload && !pendingUpload.failed && <span>{pendingUpload.progress}%</span>}
                  </div>
                  {pendingUpload?.failed ? (
                    <button type="button" className="subtitle-status-retry" onClick={retryUpload}>
                      <RotateCcw size={14} /> Retry upload
                    </button>
                  ) : (
                    <div
                      className="subtitle-status-bar"
                      role="progressbar"
                      aria-label={pendingUpload ? "Upload progress" : "Transcription in progress"}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={pendingUpload ? pendingUpload.progress : undefined}
                      data-indeterminate={!pendingUpload}
                      style={{ "--progress": `${pendingUpload?.progress ?? 0}%` } as React.CSSProperties}
                    >
                      <span />
                    </div>
                  )}
                  <small>
                    {pendingUpload
                      ? "Your video already plays in the preview while it uploads."
                      : durationMs > 5 * 60 * 1000
                        ? `A ${Math.round(durationMs / 60000)}-minute video is transcribed in parts, about a minute per part. You can leave this page.`
                        : "Captions appear here as soon as the transcript is ready. You can leave this page."}
                  </small>
                </div>
              )}
              {project?.status === "failed" && !pendingUpload && (
                <p className="subtitle-notice" role="alert">
                  {project.error?.message ?? "This video could not be transcribed."}{" "}
                  <button type="button" onClick={() => fileInput.current?.click()}>Upload another video</button>
                </p>
              )}
              {editing && !cues.length && (
                <p className="subtitle-transcribing">No speech was found in this video.</p>
              )}
              <div className="subtitle-transcript">
                {shownCues.map((cue) => (
                  <div key={cue.id} className="subtitle-cue" data-selected={selectedId === cue.id} data-active={activeId === cue.id} onClick={() => seekCue(cue)}>
                    <button type="button" className="subtitle-cue-time" aria-label={`Seek to ${formatTime(cue.startMs)}`}>{formatTime(cue.startMs)} – {formatTime(cue.endMs)}</button>
                    <textarea id={`caption-${cue.id}`} aria-label={`Caption at ${formatTime(cue.startMs)}`} value={cue.text} rows={2} disabled={!editing} onFocus={() => setSelectedId(cue.id)} onChange={(event) => updateText(cue.id, event.target.value)} />
                    <div className="subtitle-cue-actions">
                      <button type="button" aria-label={`Edit caption at ${formatTime(cue.startMs)}`} disabled={!editing} onClick={(event) => {
                        event.stopPropagation();
                        document.getElementById(`caption-${cue.id}`)?.focus();
                      }}><Pencil size={14} /></button>
                      <button type="button" aria-label={`Delete caption at ${formatTime(cue.startMs)}`} disabled={!editing || cues.length === 1} onClick={(event) => {
                        event.stopPropagation();
                        deleteCue(cue.id);
                      }}><Trash2 size={14} /></button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="subtitle-style-section">
                <h2>Caption style</h2>
                <div className="subtitle-presets">
                  {presets.map((item) => (
                    <button key={item.id} type="button" data-preset={item.id} aria-pressed={preset === item.id} disabled={!editing} onClick={() => setPreset(item.id)}>
                      <span>
                        {item.id === "modern" ? (
                          <>The quick brown<br /><mark>fox jumps over</mark></>
                        ) : item.sample}
                      </span>
                      <small>{item.label}</small>
                    </button>
                  ))}
                </div>
                <div className="subtitle-style-controls">
                  <label>Caption position<select value={position} disabled={!editing} onChange={(event) => setPosition(event.target.value as SubtitlePosition)}><option value="bottom">Bottom center</option><option value="center">Center</option><option value="top">Top center</option></select></label>
                  <label>Caption size<select value={size} disabled={!editing} onChange={(event) => setSize(event.target.value as SubtitleSize)}><option value="small">Small</option><option value="medium">Medium</option><option value="large">Large</option></select></label>
                  <label className="subtitle-color">Text<input aria-label="Text color" type="color" value={textColor} disabled={!editing} onChange={(event) => setTextColor(event.target.value.toUpperCase())} /></label>
                  <label className="subtitle-color">Highlight<input aria-label="Highlight color" type="color" value={highlightColor} disabled={!editing} onChange={(event) => setHighlightColor(event.target.value.toUpperCase())} /></label>
                  <label className="subtitle-safe">Safe area<input type="checkbox" checked={safeArea} disabled={!editing} onChange={(event) => setSafeArea(event.target.checked)} /><span aria-hidden="true" /></label>
                </div>
              </div>
            </section>
          </div>

          <section className="subtitle-timeline" aria-label="Caption timeline">
            <div className="subtitle-timeline-tools">
              <span>Timeline</span>
              <button type="button" aria-label="Undo" disabled={!editing || !history.past.length} onClick={() => setHistory((value) => undoHistory(value))}><Undo2 size={15} /></button>
              <button type="button" aria-label="Redo" disabled={!editing || !history.future.length} onClick={() => setHistory((value) => redoHistory(value))}><Redo2 size={15} /></button>
              <span className="subtitle-timeline-hint"><Sparkles size={14} /> Scroll or click a caption to seek</span>
            </div>
            {/* Pointer shortcut for the same seek the "Video position" slider offers keyboard users. */}
            <div className="subtitle-waveform" aria-hidden="true" onPointerDown={(event) => { startScrub(); seekFromPointer(event); }} onPointerMove={(event) => { if (event.buttons === 1) seekFromPointer(event); }} onPointerUp={endScrub} onPointerLeave={(event) => { if (event.buttons === 1) endScrub(); }}>{Array.from({ length: 92 }, (_, index) => <i key={index} style={{ height: `${22 + ((index * 17) % 54)}%` }} />)}<span style={{ left: `${Math.min(100, (frame / durationInFrames) * 100)}%` }} /></div>
            <div className="subtitle-track" onPointerDown={(event) => { if (event.target === event.currentTarget) seekFromPointer(event); }}>
              {shownCues.map((cue) => (
                <button key={cue.id} type="button" aria-pressed={selectedId === cue.id} onClick={() => seekCue(cue)} style={{ left: `${(cue.startMs / durationMs) * 100}%`, width: `${((cue.endMs - cue.startMs) / durationMs) * 100}%` }}>{cue.text}</button>
              ))}
            </div>
          </section>
        </section>
      )}
    </div>
  );
}
