"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Asset,
  CreativeInput,
  TryOnAngle,
  Credits,
  Generation,
  ModelOption,
  PromptResult,
  VideoTemplate,
  NormalizedTemplateInputs,
  AppliedRecipe,
} from "@ugc/contracts";
import { getServices } from "@/services";
import { ServiceError } from "@/services/http";
import { estimateInput } from "@/services/estimate";
import { pollGeneration } from "@/services/poll-generation";
import { mediaUrlRefreshDelay } from "@/services/history-video";
import {
  prepareSubmission,
  submissionFailed,
  type PendingSubmission,
} from "@/services/submission";
const pendingKey = "ugc-pending-submission-v1";
const initial: CreativeInput = {
  inputAssets: {},
  templateId: "auto",
  brief: "",
  duration: 15,
  aspectRatio: "9:16",
  language: null,
};
export function useCreation() {
  const [draft, setDraft] = useState(initial),
    [assets, setAssets] = useState<Asset[]>([]),
    [templates, setTemplates] = useState<VideoTemplate[]>([]),
    [models, setModels] = useState<ModelOption[]>([]);
  const [model, setModel] = useState("auto"),
    [prompt, setPrompt] = useState<PromptResult | null>(null),
    [credits, setCredits] = useState<Credits | null>(null),
    [job, setJob] = useState<Generation | null>(null),
    [history, setHistory] = useState<Generation[]>([]);
  const [busy, setBusy] = useState<string | null>("loading"),
    [error, setError] = useState<string | null>(null),
    [loaded, setLoaded] = useState(false);
  const [promptStale, setPromptStale] = useState(false),
    [submissionUncertain, setSubmissionUncertain] = useState(false);
  // Look preview: a still image of everything worn together, before any video.
  const [tryOn, setTryOn] = useState<{
    result: Asset | null;
    open: boolean;
    dismissed: boolean;
  }>({ result: null, open: false, dismissed: false });
  // Recreate: the mechanism of a past video, reused for a new offer. Only the mechanism
  // carries over — the user supplies their own material and the director writes new text.
  const [recreate, setRecreate] = useState<{
    mechanism: string;
    templateId: string;
  } | null>(null);
  const version = useRef(0),
    submission = useRef<PendingSubmission | null>(null),
    locked = useRef(false);
  function savePending(value: PendingSubmission | null) {
    if (value) sessionStorage.setItem(pendingKey, JSON.stringify(value));
    else sessionStorage.removeItem(pendingKey);
    submission.current = value;
    setSubmissionUncertain(!!value);
  }
  const refresh = useCallback(async () => {
    const s = getServices();
    const [h, c] = await Promise.all([s.generations.list(), s.credits.get()]);
    setHistory(h.generations);
    setCredits((prev) => (prev ? { ...prev, balance: c.balance } : c));
  }, []);
  const load = useCallback(() => {
    const service = getServices();
    return Promise.all([
      service.templates.list(),
      service.models.list(),
      service.generations.list(),
      service.credits.get(),
    ])
      .then(([t, m, h, c]) => {
        try {
          const saved = sessionStorage.getItem(pendingKey);
          if (saved) {
            const pending = JSON.parse(saved) as PendingSubmission;
            if (pending.key && pending.input) {
              submission.current = pending;
              setSubmissionUncertain(true);
            }
          }
        } catch {
          /* Submission storage is validated before sending. */
        }
        setTemplates(t.templates);
        const selected = t.templates.find(
          (t) =>
            t.id ===
              new URLSearchParams(window.location.search).get("template") &&
            t.available,
        );
        if (selected) setDraft((d) => templateDraft(d, selected));
        const reused = h.generations.find(
          (g) =>
            g.id === new URLSearchParams(window.location.search).get("recreate"),
        );
        if (reused) startRecreate(reused);
        setModels(m.models);
        setHistory(h.generations);
        setCredits(c);
        setJob(
          h.generations.find((j) =>
            ["queued", "generating"].includes(j.status),
          ) || null,
        );
        setLoaded(true);
      })
      .catch((e) =>
        setError(
          e instanceof Error ? e.message : "Could not load the workspace.",
        ),
      )
      .finally(() => setBusy(null));
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  // A model photo plus at least two pieces is a look, not a single-product shot: that is
  // the moment the panel is useful, so it opens itself instead of waiting for a chat line.
  const lookPieces =
    (draft.inputAssets.productImageId ? 1 : 0) + (draft.inputAssets.items?.length || 0);
  const tryOnEligible = !!draft.inputAssets.personImageId && lookPieces >= 2;
  const lastPieces = useRef(lookPieces);
  useEffect(() => {
    // Changing the look is a new question, so a closed panel offers itself again.
    const changed = lastPieces.current !== lookPieces;
    lastPieces.current = lookPieces;
    setTryOn((t) => {
      const dismissed = changed ? false : t.dismissed;
      return tryOnEligible && !dismissed
        ? { ...t, dismissed, open: true }
        : { ...t, dismissed };
    });
  }, [tryOnEligible, lookPieces]);
  const jobId = job?.id,
    jobStatus = job?.status;
  const outputUrlExpiresAt = job?.outputAssets.find(
    (asset) => asset.role === "output_video",
  )?.urlExpiresAt;
  useEffect(() => {
    if (!jobId || !jobStatus || !["queued", "generating"].includes(jobStatus))
      return;
    return pollGeneration(
      getServices().generations,
      jobId,
      async (generation) => {
        setJob(generation);
        await refresh();
      },
      () =>
        setError(
          "Connection interrupted. Your generation is still saved; reconnecting…",
        ),
    );
  }, [jobId, jobStatus, refresh]);
  useEffect(() => {
    if (!jobId || jobStatus !== "completed" || !outputUrlExpiresAt) return;
    const delay = mediaUrlRefreshDelay(outputUrlExpiresAt);
    if (delay === null) return;
    const timer = window.setTimeout(() => {
      void getServices()
        .generations.get(jobId)
        .then(({ generation }) =>
          setJob((current) => (current?.id === jobId ? generation : current)),
        )
        .catch(() =>
          setError("Video access expired. Reopen it from Recent Creations."),
        );
    }, delay);
    return () => window.clearTimeout(timer);
  }, [jobId, jobStatus, outputUrlExpiresAt]);
  function invalidate() {
    version.current++;
    setJob((j) =>
      j && !["queued", "generating"].includes(j.status) ? null : j,
    );
    setPromptStale(true);
    setCredits((c) => (c ? { ...c, quote: null } : c));
  }
  const selectedTemplate = templates.find((t) => t.id === draft.templateId);
  const renderOnly = selectedTemplate?.templateType === "remotion";
  function selectTemplate(id: string) {
    if (submission.current) return;
    if (id === "auto") {
      invalidate();
      setPrompt(null);
      setDraft((d) => ({
        ...d,
        templateId: "auto",
        duration: 15,
        normalizedInputs: undefined,
      }));
      return;
    }
    const template = templates.find((t) => t.id === id);
    if (!template) return;
    invalidate();
    setPrompt(null);
    if (template.templateType === "remotion") setModel("auto");
    setDraft((d) => {
      const next = templateDraft(d, template);
      const available = models.find((m) => m.id === "auto")?.configurations;
      if (
        template.templateType !== "remotion" &&
        available?.length &&
        !available.some((c) => c.duration === next.duration)
      ) {
        next.duration = available[0].duration;
      }
      return next;
    });
  }
  async function uploadTemplateInput(
    file: File,
    key: string,
    mediaType: string,
  ) {
    if (locked.current || submission.current) return;
    locked.current = true;
    setBusy("upload-template");
    setError(null);
    try {
      const { asset } = await getServices().assets.upload(
        file,
        mediaType === "video" ? "source_video" : "product",
      );
      invalidate();
      setAssets((a) => [...a, asset]);
      setDraft((d) => ({
        ...d,
        normalizedInputs: { ...d.normalizedInputs, [key]: asset.id },
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  function update(patch: Partial<CreativeInput>) {
    if (submission.current) return;
    invalidate();
    setDraft((d) => ({ ...d, ...patch }));
  }
  function selectModel(value: string) {
    if (submission.current) return;
    invalidate();
    setModel(value);
  }
  async function upload(
    file: File,
    role: "product" | "person" | "source_video",
  ) {
    if (locked.current || submission.current) return;
    locked.current = true;
    setBusy(`upload-${role}`);
    setError(null);
    try {
      const { asset } = await getServices().assets.upload(file, role);
      const key =
        role === "product"
          ? "productImageId"
          : role === "person"
            ? "personImageId"
            : "sourceVideoId";
      // Look items share the "product" role, so replace only the asset this slot held
      // rather than every asset that happens to carry the same role.
      const replaced = draft.inputAssets[key];
      setAssets((a) => [...a.filter((x) => x.id !== replaced), asset]);
      invalidate();
      setDraft((d) => ({
        ...d,
        inputAssets: { ...d.inputAssets, [key]: asset.id },
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  // Extra pieces of one look. They upload as ordinary product images — same role, same
  // ownership path — and differ only by carrying a label in the request.
  async function addItem(file: File, label: string) {
    if (locked.current || submission.current) return;
    const named = label.trim();
    if (!named) return;
    locked.current = true;
    setBusy("upload-item");
    setError(null);
    try {
      const { asset } = await getServices().assets.upload(file, "product");
      invalidate();
      setAssets((a) => [...a, asset]);
      setDraft((d) => ({
        ...d,
        inputAssets: {
          ...d.inputAssets,
          items: [
            ...(d.inputAssets.items || []),
            { assetId: asset.id, label: named.slice(0, 40) },
          ],
        },
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  // One request and one state update for a whole look, so picking five files does not
  // flicker the busy flag five times or race five draft updates against each other.
  async function addItems(files: File[]) {
    if (locked.current || submission.current || !files.length) return;
    locked.current = true;
    setBusy("upload-item");
    setError(null);
    try {
      const { assets: uploaded } = await getServices().assets.uploadMany(files);
      invalidate();
      setAssets((a) => [...a, ...uploaded]);
      setDraft((d) => {
        const hero = d.inputAssets.productImageId || uploaded[0].id;
        return {
          ...d,
          inputAssets: {
            ...d.inputAssets,
            productImageId: hero,
            items: [
              ...(d.inputAssets.items || []),
              ...uploaded
                .filter((asset) => asset.id !== hero)
                .map((asset) => ({ assetId: asset.id, label: itemLabel(asset.fileName) })),
            ],
          },
        };
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  function renameItem(assetId: string, label: string) {
    if (submission.current) return;
    const named = label.trim().slice(0, 40);
    if (!named) return;
    invalidate();
    update({
      inputAssets: {
        ...draft.inputAssets,
        items: (draft.inputAssets.items || []).map((i) =>
          i.assetId === assetId ? { ...i, label: named } : i,
        ),
      },
    });
  }
  function removeItem(assetId: string) {
    if (submission.current) return;
    invalidate();
    setAssets((a) => a.filter((x) => x.id !== assetId));
    update({
      inputAssets: {
        ...draft.inputAssets,
        items: (draft.inputAssets.items || []).filter((i) => i.assetId !== assetId),
      },
    });
  }
  function remove(role: Asset["role"]) {
    if (submission.current) return;
    const key =
      role === "product"
        ? "productImageId"
        : role === "person"
          ? "personImageId"
          : "sourceVideoId";
    const next = { ...draft.inputAssets };
    const removed = next[key];
    delete next[key];
    // Only this slot's asset: other product-role assets are pieces of the look.
    setAssets((a) => a.filter((x) => x.id !== removed));
    update({ inputAssets: next });
  }
  async function resolveUrl(url: string) {
    if (locked.current || submission.current) return;
    const link = url.trim();
    if (!link) return;
    // Keep the link even when the page cannot be pre-fetched here. Shops like Zalando
    // block this request, but the director fetches the page itself and falls back to
    // research, so a failed preview must never discard the URL.
    update({ productUrl: link });
    locked.current = true;
    setBusy("url");
    setError(null);
    try {
      const { product, asset } = await getServices().products.resolve(link);
      if (asset && !draft.inputAssets.productImageId) {
        setAssets((current) => [
          ...current.filter((item) => item.role !== "product"),
          asset,
        ]);
        update({
          productUrl: product.url,
          inputAssets: { ...draft.inputAssets, productImageId: asset.id },
        });
      } else {
        update({ productUrl: product.url });
      }
    } catch {
      // Preview unavailable; the director still receives the link when it plans.
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  async function generatePrompt() {
    if (locked.current || submission.current) return;
    locked.current = true;
    setBusy("prompt");
    setError(null);
    setCredits((c) => (c ? { ...c, quote: null } : c));
    const v = version.current;
    try {
      const s = getServices(),
        p = await s.prompts.generate(draft);
      if (v !== version.current) return;
      setPrompt(p);
      setPromptStale(false);
      setJob((j) =>
        j && !["queued", "generating"].includes(j.status) ? null : j,
      );
      const c = await s.credits.get(estimateInput(draft, p.promptId, model));
      if (v === version.current) setCredits(c);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  // Auto mode runs the same creative director as the chat, just without the conversation:
  // the backend requires a non-empty message, and the real signal comes from the template,
  // assets and product page rather than from this sentence.
  async function tryOnPhoto(angle?: TryOnAngle["id"], baseAssetId?: string) {
    if (locked.current || submission.current) return;
    locked.current = true;
    setBusy("try-on");
    setError(null);
    try {
      const { asset } = await getServices().tryOn.preview({
        inputAssets: draft.inputAssets,
        aspectRatio: draft.aspectRatio,
        ...(angle ? { angle } : {}),
        ...(baseAssetId ? { baseAssetId } : {}),
        idempotencyKey: crypto.randomUUID(),
      });
      setTryOn((t) => ({ ...t, result: asset }));
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  // The past video supplies only its mechanism; the new offer's material and text are
  // the user's own, so the draft starts empty.
  function startRecreate(source: Generation) {
    if (!source.creativeMechanism || locked.current || submission.current) return;
    invalidate();
    setRecreate({
      mechanism: source.creativeMechanism,
      templateId: source.templateId,
    });
    setDraft({
      ...initial,
      templateId: source.templateId,
      duration: source.duration,
      aspectRatio: source.aspectRatio,
    });
    setPrompt(null);
    setError(null);
  }
  async function autoPlan() {
    if (locked.current || submission.current) return false;
    locked.current = true;
    setBusy("prompt");
    setError(null);
    const v = version.current;
    try {
      const chat = getServices().chat;
      const session = await chat.create();
      const {
        templateId,
        inputAssets,
        duration,
        aspectRatio,
        productUrl,
        brief,
        language,
      } = draft;
      const answered = await chat.send(session.id, {
        text: "Plan this video from the selected style and the supplied materials.",
        intent: "message",
        context: {
          templateId,
          inputAssets,
          duration,
          aspectRatio,
          productUrl,
          brief,
          ...(language ? { language } : {}),
          ...(recreate ? { preferredMechanism: recreate.mechanism } : {}),
        },
      });
      if (v !== version.current) return false;
      if (!answered.answer?.recipe) {
        setError(
          answered.answer?.clarificationQuestion ||
            "Add a product photo, a product URL or a brief so the director can plan.",
        );
        return false;
      }
      const applied = await chat.apply(session.id, {
        revision: answered.revision,
        creative: {
          ...draft,
          brief: answered.answer.recipe.concept || draft.brief,
        },
      });
      if (v !== version.current) return false;
      locked.current = false;
      await applyRecipe(applied);
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }
  async function applyRecipe(result: AppliedRecipe) {
    if (locked.current || submission.current) return;
    invalidate();
    setDraft(result.creative);
    setPrompt(result.prompt);
    setPromptStale(false);
    setModel("auto");
    setError(null);
    const v = version.current;
    setBusy("quote");
    try {
      const next = await getServices().credits.get(
        estimateInput(result.creative, result.prompt.promptId, "auto"),
      );
      if (v === version.current) setCredits(next);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }
  // Returns the fresh quote so a caller can use it immediately; React state is not
  // updated synchronously, so the submit path cannot read it back from `credits`.
  async function requote() {
    if ((!renderOnly && (!prompt || promptStale)) || submission.current)
      return null;
    setBusy("quote");
    const v = version.current;
    try {
      const next = await getServices().credits.get(
        estimateInput(draft, renderOnly ? undefined : prompt!.promptId, model),
      );
      if (v !== version.current) return null;
      setCredits(next);
      return next;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(null);
    }
  }
  async function generateVideo() {
    if (locked.current) return;
    if (!submission.current && !renderOnly && (!prompt || promptStale)) return;
    if (!submission.current && job?.status === "completed") return;
    locked.current = true;
    setBusy("submit");
    setError(null);
    try {
      if (!submission.current) {
        if (!renderOnly && !prompt) return;
        // Quote silently as part of submitting instead of making the user press twice.
        let quoted = credits;
        if (
          !quoted?.quote ||
          Date.parse(quoted.quote.expiresAt) <= Date.now()
        )
          quoted = await requote();
        if (!quoted?.quote) return;
        if (quoted.balance < quoted.quote.creditsEstimated) {
          setError(
            `This video needs ${quoted.quote.creditsEstimated} credits and you have ${quoted.balance}.`,
          );
          return;
        }
        const input = {
          ...draft,
          model,
          voice: "auto",
          quality: "auto",
          ...(!renderOnly && prompt
            ? { promptId: prompt.promptId, prompt: prompt.prompt }
            : {}),
          quoteId: quoted.quote.id,
        };
        savePending(prepareSubmission(null, input));
      }
      const pending = submission.current!;
      let generation: Generation;
      try {
        ({ generation } = await getServices().generations.create(
          pending.input,
          pending.key,
        ));
        if (
          !generation?.id ||
          ![
            "queued",
            "generating",
            "completed",
            "failed",
            "cancelled",
          ].includes(generation.status)
        )
          throw new Error("Invalid generation response.");
      } catch (e) {
        savePending(submissionFailed(pending, e));
        if (
          !submission.current &&
          e instanceof ServiceError &&
          e.code === "STALE_QUOTE"
        ) {
          setCredits((c) => (c ? { ...c, quote: null } : c));
          if (await requote())
            setError("Estimate refreshed. Review the cost and submit again.");
          return;
        }
        throw e;
      }
      savePending(null);
      setCredits((c) => (c ? { ...c, quote: null } : c));
      setJob(generation);
      await refresh();
    } catch (e) {
      setError(
        submission.current
          ? "Submission result is unknown. Check submission to safely recover the same request."
          : (e as Error).message,
      );
    } finally {
      locked.current = false;
      setBusy(null);
    }
  }

  async function cancel() {
    if (!job || submission.current || locked.current) return;
    setBusy("cancel");
    try {
      setJob((await getServices().generations.cancel(job.id)).generation);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }
  async function open(id: string) {
    try {
      setJob((await getServices().generations.get(id)).generation);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return {
    draft,
    assets,
    templates,
    models,
    model,
    prompt,
    promptStale,
    submissionUncertain,
    credits,
    job,
    history,
    busy,
    error,
    loaded,
    update,
    selectTemplate,
    selectedTemplate,
    renderOnly,
    uploadTemplateInput,
    selectModel,
    upload,
    remove,
    resolveUrl,
    generatePrompt,
    applyRecipe,
    addItem,
    addItems,
    removeItem,
    renameItem,
    autoPlan,
    tryOn: { ...tryOn, eligible: tryOnEligible, pieces: lookPieces },
    tryOnPhoto,
    closeTryOn: () => setTryOn((t) => ({ ...t, open: false, dismissed: true })),
    recreating: !!recreate,
    cancelRecreate: () => setRecreate(null),
    startRecreate,
    generateVideo,
    requote,
    cancel,
    open,
    reload: () => {
      setBusy("loading");
      setError(null);
      void load();
    },
    editPrompt: (text: string) => {
      if (!submission.current)
        setPrompt((p) => (p ? { ...p, prompt: text } : p));
    },
  };
}

export function itemLabel(fileName: string) {
  return fileName.replace(/\.[^.]+$/, "").slice(0, 40) || "item";
}

function templateDraft(
  draft: CreativeInput,
  template: VideoTemplate,
): CreativeInput {
  const normalizedInputs: NormalizedTemplateInputs = Object.fromEntries(
    Object.entries(template.inputSchema?.properties ?? {}).flatMap(
      ([key, p]) => (p.default !== undefined ? [[key, p.default]] : []),
    ),
  );
  return {
    ...draft,
    templateId: template.id,
    normalizedInputs:
      template.templateType === "remotion" ? normalizedInputs : undefined,
    duration:
      template.supportedDurations?.includes(draft.duration) !== false
        ? draft.duration
        : template.supportedDurations[0],
    aspectRatio:
      template.supportedAspectRatios?.includes(draft.aspectRatio) !== false
        ? draft.aspectRatio
        : template.supportedAspectRatios[0],
  };
}
