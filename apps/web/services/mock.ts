import type {
  Services,
  Asset,
  CreativeInput,
  Generation,
  GenerationInput,
  EstimateInput,
  ModelOption,
  VideoTemplate,
  PromptResult,
  SubtitleExport,
  SubtitleProject,
  SubtitleProjectUpdate,
} from "@ugc/contracts";
import { filterTemplates } from "./template-filters";
import { ServiceError } from "./http";
import { createMockChat } from "./mock-chat";
const templateRows = [
  ["ugc_review", "UGC Review", "Authentic product stories"],
  ["product_unboxing", "Unboxing", "Show what’s inside"],
  ["problem_solution", "Problem → Solution", "Show the transformation"],
  ["product_demo", "Product Demo", "Show key features"],
  ["testimonial", "Testimonial", "Build trust"],
  ["trending_style", "Trending", "Use current styles"],
  ["hook_cta", "Hook → CTA", "Make the first seconds count"],
  ["before_after", "Before / After", "Let the difference speak"],
  ["self_presentation", "Self-presentation", "Present yourself to camera"],
];
export const mockTemplates: VideoTemplate[] = templateRows.map(
  ([id, name, description], i) => ({
    id,
    name,
    description,
    thumbnailUrl: [
      "/template-styles/ugc-review.webp",
      "/template-styles/product-unboxing.webp",
      "/template-styles/problem-solution.webp",
      "/template-styles/product-demo.webp",
      "/template-styles/testimonial.webp",
      "/template-styles/trending-style.webp",
      "/template-styles/hook-cta.webp",
      "/template-styles/before-after.webp",
      "/template-styles/testimonial.webp",
    ][i],
    available: true,
    unavailableReason: null,
    category: [
      "UGC",
      "Product",
      "Explainers",
      "Product",
      "Testimonials",
      "Social Ads",
      "Hooks",
      "Before / After",
      "Social Ads",
    ][i],
    templateType: "generative",
    featured: true,
    enabled: true,
    supportedDurations: [15, 20, 30],
    supportedAspectRatios: ["9:16", "1:1", "16:9"],
    tags: ["ugc"],
    useCases: [
      ["ugc", "organic-social"],
      ["product-showcase"],
      ["paid-ads"],
      ["product-showcase"],
      ["ugc", "paid-ads"],
      ["organic-social", "paid-ads"],
      ["paid-ads"],
      ["product-showcase"],
      ["paid-ads", "organic-social"],
    ][i],
    inputSchema: {
      type: "object",
      properties: {
        productUrl: { type: "string", format: "uri" },
        personImage: { type: "string", format: "asset-id", mediaType: "image" },
        sourceVideo: { type: "string", format: "asset-id", mediaType: "video" },
        productImage: {
          type: "string",
          format: "image-asset-id",
          mediaType: "image",
        },
      },
    },
  }),
);
const now = () => new Date().toISOString();
const uid = () => crypto.randomUUID();
const canonical = (value: unknown): string =>
  JSON.stringify(value, (_, v) =>
    v && typeof v === "object" && !Array.isArray(v)
      ? Object.fromEntries(
          Object.entries(v)
            .filter(([, x]) => x !== undefined)
            .sort(([a], [b]) => a.localeCompare(b)),
        )
      : v,
  );
const estimateOf = (x: EstimateInput): EstimateInput => ({
  templateId: x.templateId,
  duration: x.duration,
  aspectRatio: x.aspectRatio,
  inputAssets: x.inputAssets,
  productUrl: x.productUrl,
  promptId: x.promptId,
  model: x.model,
  voice: x.voice,
  quality: x.quality,
  resolution: x.resolution,
});
/** Demo captions for mock mode only: evenly spaced across the clip, never real timing. */
function mockSubtitleCues(durationMs: number): SubtitleProject["cues"] {
  const lines = [
    "This moisturizer keeps my skin hydrated all day.",
    "It’s lightweight and absorbs quickly.",
    "And gives my skin a healthy, natural glow.",
    "I use it every morning as part of my routine.",
    "And it’s honestly made such a difference.",
  ];
  const slot = Math.floor(durationMs / lines.length);
  return lines.map((text, index) => ({
    id: `mock-cue-${index + 1}`,
    startMs: index * slot,
    endMs: index === lines.length - 1 ? durationMs : (index + 1) * slot,
    text,
    words: [],
  }));
}

export function createMockServices(persist = false): Services {
  let jobs: Generation[] = [];
  let balance = 1240;
  const assets = new Map<string, Asset>(),
    prompts = new Map<string, { result: PromptResult; input: string }>(),
    quotes = new Map<
      string,
      { input: string; cost: number; expires: number }
    >(),
    keys = new Map<string, { id: string; input: string }>();
  if (persist && typeof window !== "undefined")
    try {
      const saved = JSON.parse(localStorage.getItem("ugc-mock-v1") || "null");
      if (saved) {
        jobs = saved.jobs;
        balance = saved.balance;
      }
    } catch {
      /* A corrupt development fixture resets to an empty history. */
    }
  const save = () => {
    if (persist)
      try {
        localStorage.setItem("ugc-mock-v1", JSON.stringify({ jobs, balance }));
      } catch {
        throw new ServiceError(
          "MOCK_STORAGE_FULL",
          "Demo storage is full. Clear demo browser data to continue.",
        );
      }
  };
  const fail = (code: string, message: string): never => {
    throw new ServiceError(code, message);
  };
  const validate = (x: CreativeInput) => {
    if (!x.brief.trim() || x.brief.length > 4000)
      fail("INVALID_BRIEF", "Add a campaign brief of up to 4,000 characters.");
    if (!mockTemplates.some((t) => t.id === x.templateId))
      fail("INVALID_TEMPLATE", "Select a template.");
    if (
      ![15, 20, 30].includes(x.duration) ||
      !["9:16", "1:1", "16:9"].includes(x.aspectRatio)
    )
      fail("INVALID_SETTINGS", "Choose supported video settings.");
  };
  const getJob = (id: string) =>
    jobs.find((j) => j.id === id) || fail("NOT_FOUND", "Generation not found.");
  const tick = (j: Generation) => {
    if (j.status !== "queued" && j.status !== "generating") return;
    const elapsed = Date.now() - Date.parse(j.createdAt);
    j.status =
      elapsed < 1800 ? "queued" : elapsed < 8000 ? "generating" : "completed";
    j.progress =
      j.status === "queued"
        ? null
        : j.status === "completed"
          ? 100
          : Math.min(95, Math.round(elapsed / 80));
    j.updatedAt = now();
    if (j.status === "completed") {
      j.creditsCharged = j.creditsEstimated;
      j.outputAssets = [
        {
          id: `output-${j.id}`,
          role: "output_video",
          kind: "video",
          mimeType: "video/mp4",
          fileName: "demo-generation.mp4",
          sizeBytes: 0,
          url: `/demo-${j.duration}-${j.aspectRatio.replace(":", "x")}.mp4`,
          urlExpiresAt: null,
          width:
            j.aspectRatio === "9:16"
              ? 360
              : j.aspectRatio === "1:1"
                ? 480
                : 640,
          height:
            j.aspectRatio === "9:16"
              ? 640
              : j.aspectRatio === "1:1"
                ? 480
                : 360,
          durationSeconds: j.duration,
          createdAt: now(),
        },
      ];
    }
    save();
  };
  // Try-on project folders live as long as this mock instance, like its assets.
  type MockLook = {
    id: string;
    createdAt: string;
    updatedAt: string;
    scene: import("@ugc/contracts").LookScene;
    aspectRatio: import("@ugc/contracts").PhotoAspectRatio;
    inputAssets: import("@ugc/contracts").InputAssets;
    photos: { assetId: string; label: string }[];
  };
  const looks = new Map<string, MockLook>();
  const subtitleProjects = new Map<string, SubtitleProject>();
  const subtitleCreateKeys = new Map<string, string>();
  const subtitleExportKeys = new Map<string, SubtitleExport>();
  const subtitleShareTokens = new Map<string, string>(); // token -> projectId
  // Deterministic async state: a project transcribes, then an export renders, on a short clock.
  const subtitleClock = new Map<string, number>();
  // Subtitle projects survive a reload in demo mode, like demo generations do. Blob URLs die
  // with the page, so a restored project falls back to the bundled demo clip.
  const demoClip = (asset: Asset): Asset =>
    asset.url.startsWith("blob:") ? { ...asset, url: "/media/create-preview.mp4" } : asset;
  if (persist && typeof window !== "undefined")
    try {
      const saved = JSON.parse(localStorage.getItem("ugc-mock-subtitles-v1") || "null");
      for (const project of saved?.projects ?? [])
        subtitleProjects.set(project.id, {
          ...project,
          sourceAsset: demoClip(project.sourceAsset),
          latestExport: project.latestExport?.outputAsset
            ? { ...project.latestExport, outputAsset: demoClip(project.latestExport.outputAsset) }
            : project.latestExport,
        });
      for (const [key, id] of saved?.createKeys ?? []) subtitleCreateKeys.set(key, id);
      for (const [key, value] of saved?.exportKeys ?? []) subtitleExportKeys.set(key, value);
      for (const [id, at] of saved?.clock ?? []) subtitleClock.set(id, at);
      for (const [token, id] of saved?.shareTokens ?? []) subtitleShareTokens.set(token, id);
    } catch {
      /* A corrupt demo fixture starts without subtitle projects. */
    }
  // The real API signs media links per response, so every read returns a different URL for the
  // same file. Mirror that here, or the studio's source-reload bugs never show up in demo mode.
  let signature = 0;
  const signed = (project: SubtitleProject): SubtitleProject => ({
    ...project,
    sourceAsset: {
      ...project.sourceAsset,
      url: `${project.sourceAsset.url.split("#")[0]}#signature=${++signature}`,
    },
  });
  const saveSubtitles = () => {
    if (!persist || typeof window === "undefined") return;
    try {
      localStorage.setItem(
        "ugc-mock-subtitles-v1",
        JSON.stringify({
          projects: [...subtitleProjects.values()],
          createKeys: [...subtitleCreateKeys.entries()],
          exportKeys: [...subtitleExportKeys.entries()],
          clock: [...subtitleClock.entries()],
          shareTokens: [...subtitleShareTokens.entries()],
        }),
      );
    } catch {
      throw new ServiceError(
        "MOCK_STORAGE_FULL",
        "Demo storage is full. Clear demo browser data to continue.",
      );
    }
  };
  const lookLabels: Record<string, string> = {
    front: "Front",
    three_quarter: "¾",
    back: "Back",
    detail: "Detail",
  };
  const lookDetail = (look: MockLook): import("@ugc/contracts").LookProjectDetail => {
    const pieces = [
      look.inputAssets.productImageId,
      ...(look.inputAssets.items || []).map((item) => item.assetId),
    ];
    return {
      id: look.id,
      scene: look.scene,
      aspectRatio: look.aspectRatio,
      inputAssets: look.inputAssets,
      model:
        (look.inputAssets.personImageId && assets.get(look.inputAssets.personImageId)) ||
        null,
      products: pieces
        .map((id) => (id ? assets.get(id) : undefined))
        .filter((asset): asset is Asset => !!asset),
      photos: look.photos.flatMap((photo) => {
        const asset = assets.get(photo.assetId);
        return asset ? [{ asset, label: photo.label }] : [];
      }),
      createdAt: look.createdAt,
      updatedAt: look.updatedAt,
    };
  };
  const services: Omit<Services, "chat"> = {
    assets: {
      async upload(file, role, source, onProgress) {
        const image = role !== "source_video";
        if (
          image &&
          !["image/png", "image/jpeg", "image/webp"].includes(file.type)
        )
          fail("INVALID_MEDIA", "Choose a PNG, JPG or WebP image.");
        if (
          !image &&
          !["video/mp4", "video/quicktime", "video/webm"].includes(file.type)
        )
          fail("INVALID_MEDIA", "Choose an MP4, MOV or WebM video.");
        if (file.size > (image ? 10 : 500) * 1024 * 1024)
          fail("ASSET_TOO_LARGE", "The file exceeds the upload limit.");
        const url = URL.createObjectURL(file);
        const asset: Asset = {
          id: uid(),
          role,
          kind: image ? "image" : "video",
          mimeType: file.type,
          fileName: file.name,
          sizeBytes: file.size,
          url,
          urlExpiresAt: null,
          width: null,
          height: null,
          durationSeconds: null,
          createdAt: now(),
        };
        if (source) Object.assign(asset, { source });
        if (!image && typeof document !== "undefined") {
          // Read the real length and frame size, like the API does with ffprobe; a guessed
          // 10 seconds made longer demo clips stop and rewind at the 10-second mark.
          const metadata = await new Promise<{ duration: number; width: number; height: number } | null>((resolve) => {
            const probe = document.createElement("video");
            const timer = setTimeout(() => resolve(null), 3000);
            probe.preload = "metadata";
            probe.onloadedmetadata = () => {
              clearTimeout(timer);
              resolve({ duration: probe.duration, width: probe.videoWidth, height: probe.videoHeight });
            };
            probe.onerror = () => {
              clearTimeout(timer);
              resolve(null);
            };
            probe.src = url;
          });
          if (metadata && Number.isFinite(metadata.duration))
            Object.assign(asset, {
              durationSeconds: metadata.duration,
              width: metadata.width || null,
              height: metadata.height || null,
            });
        }
        if (onProgress)
          for (const percent of [12, 38, 67, 91, 100]) {
            onProgress(percent);
            await new Promise((resolve) => setTimeout(resolve, 90));
          }
        assets.set(asset.id, asset);
        return { asset };
      },
      async uploadMany(files) {
        const uploaded = [];
        for (const file of files) uploaded.push((await this.upload(file, "product")).asset);
        return { assets: uploaded };
      },
      async list(role, source) {
        return {
          assets: [...assets.values()]
            .filter(
              (asset) =>
                asset.role === role &&
                (asset as Asset & { source?: string }).source === source,
            )
            .reverse(),
        };
      },
      async importCatalogCsv(file) {
        const text = await file.text();
        const lines = text.split(/\r?\n/).filter((line) => line.trim());
        const [headerLine, ...rows] = lines;
        if (!headerLine || !rows.length)
          fail("CATALOG_IMPORT_INVALID", "The CSV file has no rows.");
        if (rows.length > 30)
          fail("CATALOG_IMPORT_TOO_LARGE", "Import up to 30 rows at a time.");
        const headers = headerLine.split(",").map((h) => h.trim());
        const placeholders = ["/try-on/bluza.png", "/try-on/bag.png", "/try-on/boots.png"];
        const created: Asset[] = [];
        const errors: { row: number; message: string }[] = [];
        rows.forEach((line, index) => {
          const cells = line.split(",").map((c) => c.trim());
          const record = Object.fromEntries(headers.map((h, i) => [h, cells[i] ?? ""]));
          const url = record.url || record.imageUrl;
          if (!url) {
            errors.push({ row: index + 1, message: "Each row needs a url or an imageUrl." });
            return;
          }
          const asset: Asset = {
            id: uid(),
            role: "product",
            kind: "image",
            mimeType: "image/png",
            fileName: record.name || "catalog-product",
            sizeBytes: 1,
            url: placeholders[index % placeholders.length],
            urlExpiresAt: null,
            width: 800,
            height: 800,
            durationSeconds: null,
            createdAt: now(),
          };
          Object.assign(asset, { source: "try_on" });
          assets.set(asset.id, asset);
          created.push(asset);
        });
        return { created, errors };
      },
    },
    tryOn: {
      async preview({ inputAssets, angle, projectId }) {
        const look = projectId ? looks.get(projectId) : undefined;
        if (projectId && !look)
          fail("LOOK_PROJECT_NOT_FOUND", "That project is unavailable.");
        const pieces = [
          inputAssets.productImageId,
          ...(inputAssets.items || []).map((item) => item.assetId),
        ].filter(Boolean);
        if (!inputAssets.personImageId || !pieces.length)
          fail("PREVIEW_INPUT_MISSING", "Add a model photo and at least one product.");
        const source = assets.get(pieces[0] as string);
        const asset: Asset = {
          id: uid(),
          role: "tryon_photo",
          kind: "image",
          mimeType: "image/png",
          fileName: "look-preview.png",
          sizeBytes: 1024,
          url: source?.url || "",
          urlExpiresAt: null,
          width: null,
          height: null,
          durationSeconds: null,
          createdAt: now(),
        };
        assets.set(asset.id, asset);
        if (look) {
          look.photos.push({
            assetId: asset.id,
            label: (angle && lookLabels[angle]) || "Hero",
          });
          look.updatedAt = now();
        }
        return { asset, creditsCharged: 0 };
      },
    },
    lookProjects: {
      async create({ inputAssets, scene, aspectRatio }) {
        const ids = [
          inputAssets.productImageId,
          inputAssets.personImageId,
          ...(inputAssets.items || []).map((item) => item.assetId),
        ].filter((id): id is string => !!id);
        if (!ids.every((id) => assets.has(id)))
          fail("INVALID_ASSET", "Input asset is unavailable.");
        const look: MockLook = {
          id: uid(),
          createdAt: now(),
          updatedAt: now(),
          scene,
          aspectRatio,
          inputAssets,
          photos: [],
        };
        looks.set(look.id, look);
        return { project: lookDetail(look) };
      },
      async list() {
        return {
          projects: [...looks.values()]
            .filter((look) => look.photos.length)
            .reverse()
            .map((look) => ({
              id: look.id,
              scene: look.scene,
              aspectRatio: look.aspectRatio,
              photoCount: look.photos.length,
              coverUrl: assets.get(look.photos[0].assetId)?.url ?? null,
              createdAt: look.createdAt,
              updatedAt: look.updatedAt,
            })),
        };
      },
      async get(id) {
        const look = looks.get(id);
        if (!look) return fail("LOOK_PROJECT_NOT_FOUND", "That project is unavailable.");
        return { project: lookDetail(look) };
      },
      async remove(id) {
        if (!looks.has(id)) fail("LOOK_PROJECT_NOT_FOUND", "That project is unavailable.");
        looks.delete(id);
      },
    },
    subtitleProjects: {
      async create(input, key) {
        const existingId = subtitleCreateKeys.get(key);
        if (existingId) return { project: signed(subtitleProjects.get(existingId)!) };
        const sourceAsset = assets.get(input.sourceAssetId) ??
          fail("INVALID_ASSET", "Choose an uploaded video.");
        if (sourceAsset.kind !== "video")
          fail("INVALID_ASSET", "Choose an uploaded video.");
        const timestamp = now();
        const project: SubtitleProject = {
          id: uid(),
          sourceAsset,
          status: "transcribing",
          aspectRatio: input.aspectRatio,
          language: null,
          durationMs: Math.round((sourceAsset.durationSeconds ?? 10) * 1000),
          revision: 0,
          cues: [],
          style: {
            preset: "modern",
            position: "bottom",
            size: "medium",
            safeArea: true,
            textColor: "#FFFFFF",
            highlightColor: "#C9FF27",
          },
          latestExport: null,
          error: null,
          createdAt: timestamp,
          updatedAt: timestamp,
        };
        subtitleProjects.set(project.id, project);
        subtitleCreateKeys.set(key, project.id);
        subtitleClock.set(project.id, Date.now());
        saveSubtitles();
        return { project: signed(project) };
      },
      async list() {
        return {
          projects: [...subtitleProjects.values()].reverse().map((project) => ({
            id: project.id,
            sourceAsset: project.sourceAsset,
            status: project.status,
            aspectRatio: project.aspectRatio,
            durationMs: project.durationMs,
            latestExport: project.latestExport,
            createdAt: project.createdAt,
            updatedAt: project.updatedAt,
          })),
          nextCursor: null,
        };
      },
      async get(id) {
        let project = subtitleProjects.get(id) ??
          fail("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.");
        if (project.status === "transcribing" && Date.now() - (subtitleClock.get(id) ?? 0) >= 900) {
          project = {
            ...project,
            status: "ready",
            language: "en",
            cues: mockSubtitleCues(project.durationMs),
            updatedAt: now(),
          };
          subtitleProjects.set(id, project);
          saveSubtitles();
        }
        return { project: signed(project) };
      },
      async remove(id) {
        const project = subtitleProjects.get(id) ??
          fail("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.");
        subtitleProjects.delete(id);
        // The mock keeps exports in one flat map with no project reference beyond the
        // project's own latestExport pointer, so only that export (and its share link,
        // if live) can be cleaned up here. Real deletion cascades fully server-side.
        const latest = project.latestExport;
        if (latest) {
          if (latest.shareToken) subtitleShareTokens.delete(latest.shareToken);
          for (const [key, value] of subtitleExportKeys) if (value.id === latest.id) subtitleExportKeys.delete(key);
        }
        for (const [key, projectId] of subtitleCreateKeys) if (projectId === id) subtitleCreateKeys.delete(key);
        saveSubtitles();
      },
      async update(id, input: SubtitleProjectUpdate) {
        const project = subtitleProjects.get(id) ??
          fail("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.");
        if (input.revision !== project.revision)
          fail("REVISION_CONFLICT", "The project changed. Reload it before saving again.");
        const updated: SubtitleProject = {
          ...project,
          ...input,
          revision: project.revision + 1,
          updatedAt: now(),
        };
        subtitleProjects.set(id, updated);
        saveSubtitles();
        return { project: signed(updated) };
      },
      async export(id, input, key) {
        const project = subtitleProjects.get(id) ??
          fail("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.");
        const previous = subtitleExportKeys.get(key);
        if (previous) return { export: previous };
        if (input.revision !== project.revision)
          fail("REVISION_CONFLICT", "The project changed. Reload it before exporting again.");
        const timestamp = now();
        const created: SubtitleExport = {
          id: uid(),
          status: "queued",
          progress: null,
          outputAsset: null,
          error: null,
          shareToken: null,
          createdAt: timestamp,
          updatedAt: timestamp,
        };
        subtitleExportKeys.set(key, created);
        subtitleClock.set(created.id, Date.now());
        subtitleProjects.set(id, { ...project, latestExport: created });
        saveSubtitles();
        return { export: created };
      },
      async getExport(id, exportId) {
        const project = subtitleProjects.get(id) ??
          fail("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.");
        const entry = [...subtitleExportKeys.entries()].find(([, value]) => value.id === exportId) ??
          fail("SUBTITLE_EXPORT_NOT_FOUND", "That export is unavailable.");
        const elapsed = Date.now() - (subtitleClock.get(exportId) ?? 0);
        const next: SubtitleExport =
          elapsed < 500
            ? entry[1]
            : elapsed < 1400
              ? { ...entry[1], status: "rendering", progress: Math.round(((elapsed - 500) / 900) * 100), updatedAt: now() }
              : { ...entry[1], status: "completed", progress: 100, outputAsset: project.sourceAsset, updatedAt: now() };
        subtitleExportKeys.set(entry[0], next);
        subtitleProjects.set(id, { ...project, latestExport: next });
        saveSubtitles();
        const terminal = next.status === "completed" || next.status === "failed";
        return { export: next, pollAfterMs: terminal ? null : 400 };
      },
      async share(id, exportId) {
        const project = subtitleProjects.get(id) ??
          fail("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.");
        const entry = [...subtitleExportKeys.entries()].find(([, value]) => value.id === exportId) ??
          fail("SUBTITLE_EXPORT_NOT_FOUND", "That export is unavailable.");
        if (entry[1].status !== "completed")
          fail("EXPORT_NOT_READY", "This export has not finished rendering yet.");
        const token = entry[1].shareToken ?? uid();
        const shared: SubtitleExport = { ...entry[1], shareToken: token, updatedAt: now() };
        subtitleExportKeys.set(entry[0], shared);
        subtitleShareTokens.set(token, id);
        subtitleProjects.set(id, { ...project, latestExport: shared });
        saveSubtitles();
        return { export: shared };
      },
      async unshare(id, exportId) {
        const project = subtitleProjects.get(id) ??
          fail("SUBTITLE_PROJECT_NOT_FOUND", "That project is unavailable.");
        const entry = [...subtitleExportKeys.entries()].find(([, value]) => value.id === exportId) ??
          fail("SUBTITLE_EXPORT_NOT_FOUND", "That export is unavailable.");
        if (entry[1].shareToken) subtitleShareTokens.delete(entry[1].shareToken);
        const unshared: SubtitleExport = { ...entry[1], shareToken: null, updatedAt: now() };
        subtitleExportKeys.set(entry[0], unshared);
        subtitleProjects.set(id, { ...project, latestExport: unshared });
        saveSubtitles();
        return { export: unshared };
      },
      async getShared(token) {
        const projectId = subtitleShareTokens.get(token) ??
          fail("SHARE_NOT_FOUND", "This share link is unavailable.");
        const project = subtitleProjects.get(projectId) ??
          fail("SHARE_NOT_FOUND", "This share link is unavailable.");
        const entry = [...subtitleExportKeys.values()].find((value) => value.shareToken === token) ??
          fail("SHARE_NOT_FOUND", "This share link is unavailable.");
        // A real signed URL works from any tab; a demo blob URL only works in the tab that
        // created it, so the public viewer falls back to the bundled clip like a reload does.
        const outputAsset = entry.outputAsset ? demoClip(entry.outputAsset) : null;
        return { export: { id: entry.id, outputAsset, aspectRatio: project.aspectRatio } };
      },
    },
    products: {
      async resolve(url) {
        let u: URL;
        try {
          u = new URL(url);
        } catch {
          return fail("INVALID_URL", "Enter a valid HTTPS product URL.");
        }
        if (u.protocol !== "https:")
          fail("INVALID_URL", "Use an HTTPS product URL.");
        const asset: Asset = {
          id: crypto.randomUUID(),
          role: "product",
          kind: "image",
          mimeType: "image/webp",
          fileName: "product-page.webp",
          sizeBytes: 20,
          url: "/template-styles/ugc-review.webp",
          urlExpiresAt: null,
          width: 720,
          height: 900,
          durationSeconds: null,
          createdAt: now(),
        };
        assets.set(asset.id, asset);
        return {
          product: {
            url,
            title: u.hostname,
            description:
              "Demo URL recorded. Live mode resolves product information on the server.",
            imageUrl: null,
          },
          asset,
        };
      },
    },
    templates: {
      async list(filters = {}) {
        return { templates: filterTemplates(mockTemplates, filters) };
      },
    },
    models: {
      async list() {
        const model: ModelOption = {
          id: "auto",
          label: "Auto",
          available: true,
          unavailableReason: null,
          configurations: ([15, 20, 30] as const).flatMap((duration) =>
            (["9:16", "1:1", "16:9"] as const).map((aspectRatio) => ({
              duration,
              aspectRatio,
              quality: null,
              resolution: null,
              supportsPersonImage: true,
              supportsSourceVideo: true,
            })),
          ),
          voices: [{ id: "auto", label: "Auto" }],
        };
        return { models: [model] };
      },
    },
    prompts: {
      async generate(input) {
        validate(input);
        const name = mockTemplates.find((t) => t.id === input.templateId)!.name;
        const result = {
          promptId: uid(),
          prompt: `Create a ${input.duration}-second ${input.aspectRatio} ${name} video. ${input.brief.trim()}\nUse the supplied product as the visual reference${input.inputAssets.personImageId ? ", preserving the supplied person reference" : ""}${input.inputAssets.sourceVideoId ? ", using the source video as remake context" : ""}. Open with a clear hook, demonstrate the product naturally, and end with a concise call to action. Natural lighting, authentic delivery. Do not invent product claims.`,
          inputFingerprint: canonical(input),
          createdAt: now(),
        };
        prompts.set(result.promptId, { result, input: canonical(input) });
        return result;
      },
    },
    credits: {
      async get(estimate) {
        let quote = null;
        if (estimate) {
          if (
            mockTemplates.some(
              (t) =>
                t.id === estimate.templateId && t.templateType === "remotion",
            )
          )
            fail(
              "REAL_RENDER_REQUIRED",
              "Animated templates require the local API. Browser demo mode cannot render videos.",
            );
          if (!prompts.has(estimate.promptId ?? ""))
            fail("PROMPT_REQUIRED", "Generate a current prompt first.");
          const id = uid(),
            cost = Math.ceil(estimate.duration * 2.4),
            expires = Date.now() + 300000;
          quotes.set(id, {
            input: canonical(estimateOf(estimate)),
            cost,
            expires,
          });
          quote = {
            id,
            creditsEstimated: cost,
            expiresAt: new Date(expires).toISOString(),
          };
        }
        return { balance, quote, updatedAt: now() };
      },
    },
    generations: {
      async create(input: GenerationInput, key) {
        const existing = keys.get(key);
        if (existing) {
          if (existing.input !== canonical(input))
            fail(
              "IDEMPOTENCY_CONFLICT",
              "This request key was used for different inputs.",
            );
          return { generation: getJob(existing.id) };
        }
        if (
          mockTemplates.some(
            (t) => t.id === input.templateId && t.templateType === "remotion",
          )
        )
          fail(
            "REAL_RENDER_REQUIRED",
            "Animated templates require the local API.",
          );
        validate(input);
        const p = prompts.get(input.promptId ?? "");
        const creative = {
          language: input.language,
          productUrl: input.productUrl,
          inputAssets: input.inputAssets,
          templateId: input.templateId,
          brief: input.brief,
          duration: input.duration,
          aspectRatio: input.aspectRatio,
        };
        if (!p || p.input !== canonical(creative))
          fail("STALE_PROMPT", "Inputs changed. Generate a new prompt.");
        const q =
          quotes.get(input.quoteId) ??
          fail("STALE_QUOTE", "Refresh the estimate for these settings.");
        if (q.expires < Date.now() || q.input !== canonical(estimateOf(input)))
          fail("STALE_QUOTE", "Refresh the estimate for these settings.");
        if (balance < q.cost)
          fail("INSUFFICIENT_CREDITS", "Not enough demo credits.");
        if (!input.prompt?.trim())
          fail("PROMPT_REQUIRED", "Add a production prompt.");
        balance -= q.cost;
        const j: Generation = {
          id: uid(),
          userId: "demo-user",
          templateId: input.templateId,
          model: input.model,
          provider: null,
          status: "queued",
          progress: null,
          prompt: input.prompt ?? "",
          duration: input.duration,
          aspectRatio: input.aspectRatio,
          inputAssets: Object.values(input.inputAssets)
            .map((id) => assets.get(id))
            .filter((a): a is Asset => !!a)
            .map((a) => ({ ...a, url: "" })),
          outputAssets: [],
          creditsEstimated: q.cost,
          creditsCharged: 0,
          error: null,
          createdAt: now(),
          updatedAt: now(),
        };
        jobs.unshift(j);
        keys.set(key, { id: j.id, input: canonical(input) });
        save();
        return { generation: { ...j } };
      },
      async get(id) {
        const j = getJob(id);
        tick(j);
        return {
          generation: { ...j },
          pollAfterMs: ["queued", "generating"].includes(j.status) ? 800 : null,
        };
      },
      async list() {
        jobs.forEach(tick);
        return { generations: jobs.map((j) => ({ ...j })), nextCursor: null };
      },
      async cancel(id) {
        const j = getJob(id);
        if (j.status === "cancelled") return { generation: { ...j } };
        if (["completed", "failed"].includes(j.status))
          fail("ALREADY_TERMINAL", "This generation has already finished.");
        j.status = "cancelled";
        j.progress = null;
        j.updatedAt = now();
        balance += j.creditsEstimated;
        save();
        return { generation: { ...j } };
      },
      async remove(id) {
        const j = getJob(id);
        if (!["completed", "failed", "cancelled"].includes(j.status))
          fail("DELETE_UNAVAILABLE", "This generation is still in progress.");
        jobs = jobs.filter((item) => item.id !== id);
        save();
      },
    },
    billing: {
      async summary() {
        return {
          plan: "Demo",
          status: "simulation",
          renewalDate: null,
          prices: [],
        };
      },
      async checkout() {
        return fail("MOCK_BILLING", "Billing is disabled in demo mode.");
      },
      async portal() {
        return fail("MOCK_BILLING", "Billing is disabled in demo mode.");
      },
    },
  };
  return { ...services, chat: createMockChat(persist, services.prompts) };
}
