import { Download, Play } from "lucide-react";
import type { Generation, VideoTemplate } from "@ugc/contracts";
import { mockMode } from "@/lib/auth";
import { FluidLoader } from "./fluid-loader";
export function Preview({
  job,
  templates,
  placement = "sidebar",
  planning = false,
}: {
  placement?: "sidebar" | "workspace";
  job: Generation | null;
  templates: VideoTemplate[];
  planning?: boolean;
}) {
  const output = job?.outputAssets.find((a) => a.role === "output_video");
  const template = templates.find((t) => t.id === job?.templateId);
  const active =
    planning || (job && ["queued", "generating"].includes(job.status));
  const status = job
    ? job.status[0].toUpperCase() + job.status.slice(1)
    : "Your video preview";
  const inline = placement === "workspace";
  const [w, h] = (job?.aspectRatio || "9:16").split(":").map(Number);
  if (inline && !job && !planning)
    return (
      <section
        className="workspace-result"
        aria-label="Video result"
        data-testid="workspace-result"
      >
        <h3>Your video</h3>
        <p className="result-hint">
          After you click Generate Video, progress and your finished video will
          appear here.
        </p>
      </section>
    );
  if (!inline && !job) return null;
  return (
    <aside
      className={inline ? "preview-column workspace-result" : "preview-column"}
      aria-label={inline ? "Video result" : "Example video"}
      data-testid={inline ? "workspace-result" : undefined}
    >
      {inline && <h3>Your video</h3>}
      <div
        className="preview-frame"
        style={{
          aspectRatio: job?.aspectRatio.replace(":", "/") || "9/16",
          ...(inline
            ? { maxWidth: `${(420 * w) / h}px`, minHeight: output ? 0 : 240 }
            : {}),
        }}
      >
        {!active && (
          <div className="preview-top">
            <span>{template?.name || "VIDEO PREVIEW"}</span>
            {job && <span>{job.duration}s</span>}
          </div>
        )}
        {output ? (
          <video
            controls
            playsInline
            preload="metadata"
            src={output.url}
            aria-label="Generated video"
          />
        ) : !job && !planning ? (
          <video
            controls
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            poster="/media/create-preview.webp"
            src="/media/create-preview.mp4"
            aria-label="Example product video"
          />
        ) : (
          <>
            {active && <FluidLoader />}
            <div
              className={`preview-empty${active ? " preview-empty-active" : ""}`}
            >
                {!active && (
                  <span className="play-disc">
                    <Play size={24} />
                  </span>
                )}
                <strong data-testid="preview-status">
                  {planning
                    ? "Creating your concept…"
                    : active
                      ? "Generating your video…"
                      : status}
                </strong>
                {!active && (
                  <p>
                    {job?.status === "failed"
                      ? "Your draft is saved. Review the error and try again."
                      : job?.status === "cancelled"
                        ? "The reservation has been released."
                        : "Add your product and brief to create your first video."}
                  </p>
                )}
            </div>
          </>
        )}
        {output && (
          <span className="preview-status" data-testid="preview-status">
            {status}
          </span>
        )}
        {job?.error && (
          <p role="alert" className="preview-error">
            {job.error.message}
          </p>
        )}
      </div>
      {(output || !active) && (
        <div className="preview-footer">
          {output ? (
          <a className="button button-secondary" href={output.url} download>
            <Download size={14} /> Download video
          </a>
          ) : (
            <span>Product in. Story out.</span>
          )}
        </div>
      )}
      {mockMode && (
        <p className="simulation-note">
          Demo mode · results are test footage, not AI output.
        </p>
      )}
    </aside>
  );
}
