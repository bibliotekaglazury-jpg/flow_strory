"use client";
import Link from "next/link";
import { creationTemplates } from "@/services/template-filters";
import { templateArtwork } from "@/services/template-visuals";
import {
  developerPreviewGeneration,
  type DeveloperGenerationPreviewState,
} from "@/services/developer-generation-preview";
import { mockMode } from "@/lib/auth";
import { Preview } from "./preview";
import { TemplateInputs } from "./template-inputs";
import { VideoChat } from "../chat/video-chat";
import { ChatModeSelector } from "../chat/chat-parts";
import { useRef, useState } from "react";
import {
  ArrowRight,
  ChevronDown,
  ImagePlus,
  Link2,
  Pencil,
  Plus,
  Upload,
  Video,
  X,
} from "lucide-react";
import { Button } from "@ugc/ui";
import type { Asset, AspectRatio, Duration } from "@ugc/contracts";
import { itemLabel, type useCreation } from "@/hooks/use-creation";
import { LOOK_SIZE } from "@ugc/contracts";
type Creation = ReturnType<typeof useCreation>;

// The dialogue's spoken language, not the site UI language — a separate, explicit
// decision so the director never has to guess it from a chat message or default to
// English when there is no real brief (as in Auto mode).
const VIDEO_LANGUAGES: { code: string | null; label: string; flag: string }[] = [
  { code: null, label: "Infer from the brief", flag: "✨" },
  { code: "en", label: "English", flag: "\u{1F1EC}\u{1F1E7}" },
  { code: "pl", label: "Polski", flag: "\u{1F1F5}\u{1F1F1}" },
  { code: "es", label: "Español", flag: "\u{1F1EA}\u{1F1F8}" },
  { code: "de", label: "Deutsch", flag: "\u{1F1E9}\u{1F1EA}" },
  { code: "fr", label: "Français", flag: "\u{1F1EB}\u{1F1F7}" },
  { code: "pt", label: "Português", flag: "\u{1F1F5}\u{1F1F9}" },
  { code: "zh", label: "中文", flag: "\u{1F1E8}\u{1F1F3}" },
];
function UploadField({
  title,
  role,
  asset,
  onUpload,
  onRemove,
  busy,
}: {
  title: string;
  role: "product" | "person" | "source_video";
  asset?: Asset;
  onUpload: (file: File, role: "product" | "person" | "source_video") => void;
  onRemove: () => void;
  busy: boolean;
}) {
  const image = role !== "source_video";
  return (
    <section className="upload-field">
      <h3>{title}</h3>
      <label className={`upload-target ${asset ? "has-asset" : ""}`}>
        {asset ? (
          image ? (
            <img src={asset.url} alt={asset.fileName} />
          ) : (
            <Video size={28} aria-hidden="true" />
          )
        ) : image ? (
          <ImagePlus size={26} aria-hidden="true" />
        ) : (
          <Video size={28} aria-hidden="true" />
        )}
        <input
          type="file"
          aria-label={
            role === "product"
              ? "Product image"
              : role === "person"
                ? "Person image"
                : "Existing video"
          }
          accept={
            image
              ? "image/png,image/jpeg,image/webp"
              : "video/mp4,video/quicktime,video/webm"
          }
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file, role);
            e.target.value = "";
          }}
        />
        <span>
          {asset ? "Replace" : image ? "Upload image" : "Upload video"}{" "}
          <Plus size={12} />
        </span>
      </label>
      <p>
        {image
          ? "PNG, JPG or WebP · max 10 MB"
          : "MP4, MOV or WebM · max 500 MB"}
      </p>
      {asset && (
        <button
          className="remove-asset"
          onClick={onRemove}
          aria-label={`Remove ${title}`}
        >
          <X size={12} /> Remove
        </button>
      )}
    </section>
  );
}
function ProductSlots({ c, busy }: { c: Creation; busy: boolean }) {
  const [editing, setEditing] = useState<string | null>(null);
  const items = c.draft.inputAssets.items || [];
  const hero = c.assets.find((a) => a.id === c.draft.inputAssets.productImageId);
  // The main product image is the first piece of the look, so LOOK_SIZE is the whole set.
  const filled = [
    ...(hero ? [{ asset: hero, label: null as string | null }] : []),
    ...items.map((item) => ({
      asset: c.assets.find((a) => a.id === item.assetId),
      label: item.label,
    })),
  ].filter((slot) => slot.asset);
  const empty = Math.max(0, LOOK_SIZE - filled.length);
  return (
    <section className="upload-field products-field">
      <h3>
        Products · {filled.length} of {LOOK_SIZE}
      </h3>
      <div className="product-slots">
        {filled.map(({ asset, label }) => (
          <div className="product-slot" key={asset!.id}>
            <div className="product-thumb">
              <img src={asset!.url} alt={label || "Product"} />
              <button
                type="button"
                className="slot-remove"
                disabled={busy}
                aria-label={`Remove ${label || "product"}`}
                onClick={() =>
                  label === null ? c.remove("product") : c.removeItem(asset!.id)
                }
              >
                <X size={11} />
              </button>
            </div>
            {label !== null &&
              (editing === asset!.id ? (
                <input
                  className="slot-label"
                  autoFocus
                  defaultValue={label}
                  maxLength={40}
                  disabled={busy}
                  onBlur={(e) => {
                    c.renameItem(asset!.id, e.target.value);
                    setEditing(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") e.currentTarget.blur();
                    if (e.key === "Escape") setEditing(null);
                  }}
                />
              ) : (
                <button
                  type="button"
                  className="slot-label"
                  disabled={busy}
                  onClick={() => setEditing(asset!.id)}
                >
                  <span>{label}</span>
                  <Pencil size={11} />
                </button>
              ))}
          </div>
        ))}
        {Array.from({ length: empty }).map((_, index) => (
          <label className="product-slot is-empty" key={`add-${index}`}>
            <input
              type="file"
              // Only the hero slot is "Product image": identical labels on five inputs
              // are ambiguous to a screen reader as much as to a test.
              aria-label={
                filled.length + index === 0 ? "Product image" : "Add another look item"
              }
              accept="image/png,image/jpeg,image/webp"
              multiple
              disabled={busy}
              onChange={(e) => {
                const picked = Array.from(e.target.files || []).slice(0, empty);
                // The first image fills the main product slot so existing single-product
                // behaviour is untouched; later ones become labelled look items.
                if (picked.length > 1) void c.addItems(picked);
                else if (picked.length === 1) {
                  if (!c.draft.inputAssets.productImageId)
                    void c.upload(picked[0], "product");
                  else void c.addItem(picked[0], itemLabel(picked[0].name));
                }
                e.target.value = "";
              }}
            />
            <span className="slot-plus">
              <Plus size={16} />
            </span>
            <span>Add item</span>
          </label>
        ))}
      </div>
      <p>Add up to {LOOK_SIZE} items shown together — pick several files at once.</p>
    </section>
  );
}
export function Workspace({ c }: { c: Creation }) {
  const [promptMode, setPromptMode] = useState<"chat" | "auto">("chat");
  const [chatWorking, setChatWorking] = useState(false);
  const [developerState, setDeveloperState] =
    useState<DeveloperGenerationPreviewState>("live");
  const [urlOpen, setUrlOpen] = useState(false),
    [url, setUrl] = useState(""),
    [advanced, setAdvanced] = useState(false);
  const urlTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const active = c.job && ["queued", "generating"].includes(c.job.status);
  const busy = !!c.busy;
  const retryNeedsQuote =
    !!c.prompt &&
    !c.promptStale &&
    !c.credits?.quote &&
    (c.job?.status === "failed" || c.job?.status === "cancelled");
  const uploadBusy = busy || !!active || c.submissionUncertain;
  // Auto mode plans through the director on the first click. It needs something real to
  // plan from, otherwise the turn is spent on a clarification question.
  const hasMaterial =
    !!c.draft.productUrl?.trim() ||
    !!c.draft.brief?.trim() ||
    Object.values(c.draft.inputAssets).some(Boolean);
  // A person with no product photo or link is a self-presentation, not a product ad.
  const personOnly =
    !!c.draft.inputAssets.personImageId &&
    !c.draft.inputAssets.productImageId &&
    !c.draft.inputAssets.items?.length &&
    !c.draft.productUrl?.trim();
  const autoPlanFirst =
    promptMode === "auto" &&
    !c.renderOnly &&
    !c.submissionUncertain &&
    hasMaterial &&
    (!c.prompt || c.promptStale);
  const availableDurations = c.models
    .find((m) => m.id === "auto")
    ?.configurations?.map((item) => item.duration);
  const step = c.job
    ? 4
    : c.prompt
      ? 3
      : c.assets.length || c.draft.productUrl
        ? 2
        : 1;
  const previewJob = mockMode
    ? developerPreviewGeneration(developerState, c.job)
    : c.job;
  // Both modes show the loader; in chat mode it stays inside the preview block so the
  // conversation is not covered by the full-stage overlay.
  const planning = promptMode === "auto" ? c.busy === "prompt" : chatWorking;
  return (
    <section
      className="workspace"
      id="create"
      aria-labelledby="workspace-title"
    >
      <div className="workspace-heading">
        <h2 id="workspace-title">Create Your Video</h2>
        <span className="quiet-caption">
          Your next story starts here <ArrowRight size={14} />
        </span>
      </div>
      {c.recreating && (
        <p className="recreate-banner">
          Reusing the structure of your earlier video. Upload your own product and
          the script will be written for it.
          <button type="button" onClick={c.cancelRecreate}>
            Start fresh instead
          </button>
        </p>
      )}
      <ol className="steps" aria-label="Creation progress">
        {[
          "Input",
          "Style",
          c.renderOnly ? "Estimate" : "Prompt",
          "Generate",
        ].map((label, i) => (
          <li key={label} aria-current={step === i + 1 ? "step" : undefined}>
            <span className={step >= i + 1 ? "step-active" : ""}>{i + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      <fieldset className="style-field">
        <legend>
          Recommended
          <Link className="style-view-all" href="/templates">
            View all templates <ArrowRight size={13} />
          </Link>
        </legend>
        <div className="segments" aria-label="Style">
          <button
            type="button"
            aria-pressed={c.draft.templateId === "auto"}
            disabled={uploadBusy}
            onClick={() => c.selectTemplate("auto")}
          >
            Auto
          </button>
        </div>
        <div className="style-options">
          {creationTemplates(c.templates, c.draft.templateId).map((t) => {
            const artwork = templateArtwork(t);
            return (
              <button
                type="button"
                key={t.id}
                aria-pressed={c.draft.templateId === t.id}
                disabled={
                  busy || !!active || c.submissionUncertain || !t.available
                }
                onClick={() => c.selectTemplate(t.id)}
                className="style-option"
              >
                {artwork ? (
                  <img src={artwork} alt="" />
                ) : (
                  <span className="image-placeholder" />
                )}
                <span>{t.name}</span>
                <small>{t.description}</small>
              </button>
            );
          })}
        </div>
        {personOnly &&
          !["auto", "self_presentation"].includes(c.draft.templateId) && (
            <p className="style-hint" role="status">
              Only a person photo and no product: this is a self-presentation.
              <button
                type="button"
                disabled={busy || !!active || c.submissionUncertain}
                onClick={() => c.selectTemplate("self_presentation")}
              >
                Use Self-presentation
              </button>
            </p>
          )}
      </fieldset>
      {!c.renderOnly && (
        <>
          <div className="upload-grid">
            <ProductSlots c={c} busy={uploadBusy} />
            {(
              [
                ["Person (optional)", "person"],
                ["Or start with a video", "source_video"],
              ] as const
            ).map(([title, role]) => (
              <UploadField
                key={role}
                title={title}
                role={role}
                asset={c.assets.find((a) => a.role === role)}
                onUpload={c.upload}
                onRemove={() => c.remove(role)}
                busy={uploadBusy}
              />
            ))}
          </div>
          <div className="url-controls">
            <button
              className="text-button"
              onClick={() => setUrlOpen(!urlOpen)}
              aria-expanded={urlOpen}
            >
              <Link2 size={13} />
              {c.draft.productUrl
                ? "Product URL added"
                : "Or add a product URL"}
            </button>
            {c.draft.productUrl && (
              <button
                className="text-button"
                disabled={busy}
                onClick={() => {
                  c.update({ productUrl: undefined });
                  setUrl("");
                }}
              >
                Remove URL
              </button>
            )}
          </div>
          {urlOpen && (
            <form className="url-form" onSubmit={(e) => e.preventDefault()}>
              <label className="sr-only" htmlFor="product-url">
                Product URL
              </label>
              <input
                id="product-url"
                type="url"
                placeholder="https://your-store.com/product"
                value={url}
                disabled={uploadBusy}
                onChange={(e) => {
                  const next = e.target.value;
                  setUrl(next);
                  // Kept as soon as it looks like a real link and replaced whenever a new
                  // one is pasted over it; nothing reaches the director until Send or an
                  // Auto generate. Debounced so typing a URL by hand does not fetch the
                  // page once per keystroke.
                  clearTimeout(urlTimer.current);
                  if (!next.trim()) {
                    c.update({ productUrl: undefined });
                    return;
                  }
                  if (/^https?:\/\/\S+\.\S/i.test(next.trim()))
                    urlTimer.current = setTimeout(
                      () => void c.resolveUrl(next),
                      500,
                    );
                }}
              />
            </form>
          )}
        </>
      )}
      <div className="creation-process-stage">
        {c.renderOnly ? (
          <>
          <p className="render-note">
            {c.selectedTemplate?.name} · Customize the template, then review
            your estimate.
          </p>
          <TemplateInputs c={c} disabled={uploadBusy} />
          <div className="prompt-action">
            <button
              className="text-button"
              disabled={uploadBusy}
              onClick={() => void c.requote()}
            >
              {c.busy === "quote" ? "Estimating…" : "Get estimate"}
            </button>
            <span>
              {c.credits?.quote
                ? `${c.credits.quote.creditsEstimated} credits`
                : "Review the cost before generating"}
            </span>
          </div>
          </>
        ) : (
          <>
          <ChatModeSelector
            mode={promptMode}
            onChange={setPromptMode}
            disabled={uploadBusy}
          />
          <div hidden={promptMode !== "chat"}>
            <VideoChat
              draft={c.draft}
              disabled={uploadBusy}
              onApply={c.applyRecipe}
              onWorking={setChatWorking}
            />
          </div>
          </>
        )}
        {mockMode && (
          <fieldset className="developer-preview-controls">
          <legend>Developer preview</legend>
          <div className="segments">
            {(["live", "queued", "generating", "completed", "failed"] as const).map(
              (state) => (
                <button
                  type="button"
                  key={state}
                  aria-pressed={developerState === state}
                  onClick={() => setDeveloperState(state)}
                >
                  {state[0].toUpperCase() + state.slice(1)}
                </button>
              ),
            )}
          </div>
          <small>Visual test only · no job, credits or history changes</small>
          </fieldset>
        )}
        <Preview
          placement="workspace"
          job={previewJob}
          templates={c.templates}
          planning={planning}
        />
        {c.prompt && (
          <div className="prompt-editor">
          <label className="field-label" htmlFor="production-prompt">
            Production prompt
          </label>
          <textarea
            id="production-prompt"
            value={c.prompt.prompt}
            onChange={(e) => c.editPrompt(e.target.value)}
            disabled={busy || !!active || c.submissionUncertain}
            rows={4}
          />
          </div>
        )}
      </div>
      <div className="settings-row">
        <fieldset>
          <legend>Duration</legend>
          <div className="segments">
            {(
              c.selectedTemplate?.supportedDurations ??
              ([15, 20, 30] as Duration[])
            )
              .filter(
                (d) =>
                  c.renderOnly ||
                  !availableDurations?.length ||
                  availableDurations.includes(d),
              )
              .map((d) => (
                <button
                  disabled={busy || !!active || c.submissionUncertain}
                  type="button"
                  key={d}
                  aria-pressed={c.draft.duration === d}
                  onClick={() => c.update({ duration: d })}
                >
                  {d}s
                </button>
              ))}
          </div>
        </fieldset>
        <fieldset>
          <legend>Aspect ratio</legend>
          <div className="segments">
            {(
              c.selectedTemplate?.supportedAspectRatios ??
              (["9:16", "1:1", "16:9"] as AspectRatio[])
            ).map((r) => (
              <button
                disabled={busy || !!active || c.submissionUncertain}
                type="button"
                key={r}
                aria-pressed={c.draft.aspectRatio === r}
                onClick={() => c.update({ aspectRatio: r })}
              >
                {r}
              </button>
            ))}
          </div>
        </fieldset>
        {!c.renderOnly && (
          <fieldset>
            <legend>Spoken language</legend>
            <div className="segments">
              {VIDEO_LANGUAGES.map(({ code, label, flag }) => (
                <button
                  disabled={busy || !!active || c.submissionUncertain}
                  type="button"
                  key={code ?? "auto"}
                  aria-pressed={(c.draft.language ?? null) === code}
                  onClick={() => c.update({ language: code })}
                  title={label}
                >
                  {flag} {code ? code.toUpperCase() : "Auto"}
                </button>
              ))}
            </div>
          </fieldset>
        )}
        {!c.renderOnly && (
          <button
            className="advanced-toggle"
            type="button"
            aria-expanded={advanced}
            aria-controls="advanced"
            onClick={() => setAdvanced(!advanced)}
          >
            Advanced options <ChevronDown size={12} />
          </button>
        )}
        <Button
          variant="primary"
          className="generate"
          disabled={
            busy ||
            (!c.submissionUncertain &&
              (!!active ||
                c.job?.status === "completed" ||
                // Auto mode plans on the first click, so it does not need a prompt yet.
                (!c.renderOnly &&
                  !autoPlanFirst &&
                  (c.promptStale || !c.prompt?.prompt.trim())) ||
                (!!c.credits?.quote &&
                  c.credits.balance < c.credits.quote.creditsEstimated)))
          }
          onClick={() => (autoPlanFirst ? void c.autoPlan() : c.generateVideo())}
        >
          <span>
            {c.busy === "submit"
              ? "Submitting…"
              : c.busy === "prompt"
                ? "Planning…"
                : c.submissionUncertain
                  ? "Check submission"
                  : autoPlanFirst
                    ? "Plan and estimate"
                    : retryNeedsQuote
                      ? "Refresh estimate"
                      : "Generate Video"}
          </span>
          <ArrowRight size={15} />
          {(c.submissionUncertain || c.credits?.quote) && (
            <small>
              {c.submissionUncertain
                ? "Recover safely"
                : `${c.credits!.quote!.creditsEstimated} credits`}
            </small>
          )}
        </Button>
      </div>
      {advanced && !c.renderOnly && (
        <div className="advanced-settings" id="advanced">
          <label>
            Model
            <select
              value={c.model}
              disabled={busy || !!active || c.submissionUncertain}
              onChange={(e) => c.selectModel(e.target.value)}
            >
              {c.models.map((m) => (
                <option key={m.id} value={m.id} disabled={!m.available}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {c.busy?.startsWith("upload") && (
        <p role="status" className="form-note">
          <Upload size={14} /> Uploading your asset…
        </p>
      )}
      {c.error && (
        <p role="alert" className="form-error">
          {c.error}
        </p>
      )}
      {!c.loaded && !busy && (
        <Button onClick={c.reload}>Retry loading workspace</Button>
      )}
    </section>
  );
}
