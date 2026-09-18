"use client";

import {
  ArrowRight,
  Bell,
  Box,
  CheckCircle2,
  Circle,
  Coins,
  Download,
  Expand,
  FileUp,
  Folder,
  HelpCircle,
  Home,
  Image as ImageIcon,
  ImagePlus,
  Play,
  RectangleHorizontal,
  RectangleVertical,
  Square,
  Trash2,
  Trees,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent, PointerEvent, WheelEvent } from "react";
import JSZip from "jszip";
import {
  LOOK_SIZE,
  type Asset,
  type Generation,
  type InputAssets,
  type LookProjectSummary,
  type PhotoAspectRatio,
  type TryOnAngle,
} from "@ugc/contracts";
import { getServices } from "@/services";
import { estimateInput } from "@/services/estimate";
import { pollGeneration } from "@/services/poll-generation";

const productArtwork = [
  "/try-on/bluza.png",
  "/try-on/bag.png",
  "/try-on/boots.png",
];

const scenes = [
  ["studio", "Studio", Box, "a clean studio with neutral light"],
  ["lifestyle", "Lifestyle", Home, "a natural everyday lifestyle setting"],
  ["outdoor", "Outdoor", Trees, "a believable outdoor location in daylight"],
  ["custom", "Custom", ImageIcon, ""],
] as const;

const ratios = [
  ["9:16", "Reels, TikTok", RectangleVertical],
  ["1:1", "Product grid", Square],
  ["4:5", "Shop, ads", RectangleVertical],
  ["16:9", "YouTube, website", RectangleHorizontal],
] as const;

const ANGLES: TryOnAngle[] = [
  { id: "front", label: "Front" },
  { id: "three_quarter", label: "¾" },
  { id: "back", label: "Back" },
  { id: "detail", label: "Detail" },
];

type PhotoOutput = "hero" | "angles";
type Scene = (typeof scenes)[number][0];
type Busy =
  | "products"
  | "model"
  | "library"
  | "catalog"
  | "product-library"
  | "photos"
  | "video"
  | "project"
  | null;
type Result = { asset: Asset; label: string };
type Notice = { tone: "status" | "error"; text: string } | null;

function itemLabel(asset: Asset) {
  return asset.fileName.replace(/\.[^.]+$/, "").trim().slice(0, 40) || "item";
}

export function ProductLookStudio() {
  const [products, setProducts] = useState<Asset[]>([]);
  const [model, setModel] = useState<Asset | null>(null);
  // null while closed; the user's own earlier model photos while open.
  const [library, setLibrary] = useState<Asset[] | null>(null);
  // null while closed; catalog-imported products (and any other try-on product uploads) while open.
  const [productLibrary, setProductLibrary] = useState<Asset[] | null>(null);
  const [csvResult, setCsvResult] = useState<{ created: number; errors: { row: number; message: string }[] } | null>(
    null,
  );
  const [scene, setScene] = useState<Scene>("studio");
  const [ratio, setRatio] = useState<PhotoAspectRatio>("9:16");
  const [photoOutput, setPhotoOutput] = useState<PhotoOutput>("angles");
  const [results, setResults] = useState<Result[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Every generation is its own saved folder; this is the one whose photos are shown.
  const [projects, setProjects] = useState<LookProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [selectProjectsMode, setSelectProjectsMode] = useState(false);
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set());
  const [deletingProjects, setDeletingProjects] = useState<Set<string>>(new Set());
  const [video, setVideo] = useState<Generation | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const [downloadingAll, setDownloadingAll] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const productInput = useRef<HTMLInputElement>(null);
  const modelInput = useRef<HTMLInputElement>(null);
  const csvInput = useRef<HTMLInputElement>(null);
  const stopPolling = useRef<(() => void) | null>(null);
  const galleryPointerStart = useRef<{ x: number; y: number } | null>(null);
  const galleryWheelAt = useRef(0);

  useEffect(() => {
    const services = getServices();
    services.credits
      .get()
      .then((c) => setBalance(c.balance))
      .catch(() => setBalance(null));
    services.lookProjects
      .list()
      .then((r) => setProjects(r.projects))
      .catch(() => undefined);
    return () => stopPolling.current?.();
  }, []);

  const selected = results.find((r) => r.asset.id === selectedId) ?? results[0] ?? null;
  const selectedIndex = selected ? results.findIndex((r) => r.asset.id === selected.asset.id) : 0;
  const output = video?.outputAssets.find((a) => a.role === "output_video");
  const photosBlocked = !products.length || !model;
  const step = !products.length ? 0 : !model ? 1 : results.length || video ? 3 : 2;

  async function refreshBalance() {
    try {
      setBalance((await getServices().credits.get()).balance);
    } catch {
      /* The balance is informational; a failed refresh keeps the last value. */
    }
  }

  async function refreshProjects() {
    try {
      setProjects((await getServices().lookProjects.list()).projects);
    } catch {
      /* The folder list is reloaded on the next visit if this refresh fails. */
    }
  }

  function fail(error: unknown) {
    setNotice({ tone: "error", text: (error as Error).message });
  }

  function lookAssets(): InputAssets {
    const [hero, ...rest] = products;
    return {
      productImageId: hero?.id,
      items: rest.map((asset) => ({ assetId: asset.id, label: itemLabel(asset) })),
      ...(model ? { personImageId: model.id } : {}),
    };
  }

  async function addProducts(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []).slice(0, LOOK_SIZE - products.length);
    event.target.value = "";
    if (!files.length || busy) return;
    setBusy("products");
    setNotice(null);
    try {
      // Tagged as a try-on upload, same as a single model photo, so it survives a reload
      // through the product library (assets.list("product", "try_on")).
      const { assets } = await getServices().assets.uploadMany(files, "try_on");
      setProducts((current) => [...current, ...assets].slice(0, LOOK_SIZE));
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  }

  async function chooseModel(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || busy) return;
    setBusy("model");
    setNotice(null);
    try {
      // Tagged as a try-on upload: the library here lists only these, never Create uploads.
      const { asset } = await getServices().assets.upload(file, "person", "try_on");
      setModel(asset);
      setLibrary(null);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  }

  async function toggleLibrary() {
    if (library !== null) {
      setLibrary(null);
      return;
    }
    if (busy) return;
    setBusy("library");
    setNotice(null);
    try {
      setLibrary((await getServices().assets.list("person", "try_on")).assets);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  }

  function pickModel(asset: Asset) {
    setModel(asset);
    setLibrary(null);
    setNotice(null);
  }

  async function importCsv(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || busy) return;
    setBusy("catalog");
    setNotice(null);
    setCsvResult(null);
    try {
      const { created, errors } = await getServices().assets.importCatalogCsv(file);
      setCsvResult({ created: created.length, errors });
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  }

  async function toggleProductLibrary() {
    if (productLibrary !== null) {
      setProductLibrary(null);
      return;
    }
    if (busy) return;
    setBusy("product-library");
    setNotice(null);
    try {
      setProductLibrary((await getServices().assets.list("product", "try_on")).assets);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  }

  function pickProduct(asset: Asset) {
    if (products.some((item) => item.id === asset.id) || products.length >= LOOK_SIZE) return;
    setProducts((current) => [...current, asset]);
    setNotice(null);
  }

  function clearImports() {
    setProducts([]);
    setModel(null);
    setLibrary(null);
    setNotice(null);
    // The photos stay safe in their folder; the screen just starts a fresh look.
    setResults([]);
    setSelectedId(null);
    setProjectId(null);
  }

  async function shoot(project: string, angle?: TryOnAngle["id"], baseAssetId?: string) {
    const { asset } = await getServices().tryOn.preview({
      inputAssets: lookAssets(),
      aspectRatio: ratio,
      ...(angle ? { angle } : {}),
      ...(baseAssetId ? { baseAssetId } : {}),
      idempotencyKey: crypto.randomUUID(),
      projectId: project,
    });
    return asset;
  }

  async function generatePhotos() {
    if (photosBlocked || busy) return;
    setBusy("photos");
    setNotice({
      tone: "status",
      text: photoOutput === "angles" ? "Shooting the front view…" : "Shooting your hero photo…",
    });
    const batch: Result[] = [];
    try {
      // One generation, one folder: a second press starts a second project.
      const { project } = await getServices().lookProjects.create({
        inputAssets: lookAssets(),
        scene,
        aspectRatio: ratio,
      });
      setProjectId(project.id);
      setResults([]);
      const front = await shoot(project.id, photoOutput === "angles" ? "front" : undefined);
      batch.push({ asset: front, label: photoOutput === "angles" ? "Front" : "Hero" });
      setResults([...batch]);
      setSelectedId(front.id);
      if (photoOutput === "angles") {
        // Re-angle the approved front shot so all four show the same person and styling.
        for (const angle of ANGLES.slice(1)) {
          setNotice({ tone: "status", text: `Shooting the ${angle.label} view…` });
          batch.push({ asset: await shoot(project.id, angle.id, front.id), label: angle.label });
          setResults([...batch]);
        }
      }
      // Lead with the editorial three-quarter view when a full set is ready, so
      // the visible stack reads naturally as 01 → 02 → 03 like the approved mock.
      setSelectedId(batch[1]?.asset.id ?? front.id);
      setNotice(null);
    } catch (error) {
      fail(error);
    } finally {
      await Promise.all([refreshBalance(), refreshProjects()]);
      setBusy(null);
    }
  }

  async function downloadAll() {
    if (downloadingAll) return;
    setDownloadingAll(true);
    setNotice({ tone: "status", text: "Preparing all photos for download…" });
    try {
      const zip = new JSZip();
      await Promise.all(results.map(async ({ asset, label }, index) => {
        const response = await fetch(asset.url);
        if (!response.ok) throw new Error(`Could not download ${label}.`);
        const blob = await response.blob();
        const sourceExtension = asset.fileName.split(".").pop()?.toLowerCase();
        const extension = sourceExtension?.match(/^[a-z0-9]+$/) ? sourceExtension : "png";
        const safeLabel = label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "photo";
        zip.file(`${String(index + 1).padStart(2, "0")}-${safeLabel}.${extension}`, blob);
      }));
      const archive = await zip.generateAsync({ type: "blob" });
      const archiveUrl = URL.createObjectURL(archive);
      const link = document.createElement("a");
      link.href = archiveUrl;
      link.download = "look-photos.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(archiveUrl), 0);
      setNotice(null);
    } catch (error) {
      fail(error);
    } finally {
      setDownloadingAll(false);
    }
  }

  function moveGallery(direction: -1 | 1) {
    if (results.length < 2) return;
    const next = (selectedIndex + direction + results.length) % results.length;
    setSelectedId(results[next].asset.id);
  }

  function galleryOffset(index: number) {
    let offset = index - selectedIndex;
    const half = results.length / 2;
    if (offset > half) offset -= results.length;
    if (offset < -half) offset += results.length;
    return offset;
  }

  function handleGalleryWheel(event: WheelEvent<HTMLDivElement>) {
    const movement = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
    if (Math.abs(movement) < 12 || results.length < 2) return;
    event.preventDefault();
    const now = Date.now();
    if (now - galleryWheelAt.current < 320) return;
    galleryWheelAt.current = now;
    moveGallery(movement > 0 ? 1 : -1);
  }

  function handleGalleryPointerDown(event: PointerEvent<HTMLDivElement>) {
    galleryPointerStart.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handleGalleryPointerUp(event: PointerEvent<HTMLDivElement>) {
    const start = galleryPointerStart.current;
    galleryPointerStart.current = null;
    if (!start) return;
    const x = event.clientX - start.x;
    const y = event.clientY - start.y;
    if (Math.abs(x) > 44 && Math.abs(x) > Math.abs(y)) moveGallery(x < 0 ? 1 : -1);
  }

  function handleGalleryKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      moveGallery(1);
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveGallery(-1);
    }
  }

  async function anotherAngle(angle: TryOnAngle) {
    if (!selected || !projectId || busy) return;
    setBusy("photos");
    setNotice({ tone: "status", text: `Shooting the ${angle.label} view…` });
    try {
      const asset = await shoot(projectId, angle.id, selected.asset.id);
      setResults((current) => [...current, { asset, label: angle.label }]);
      setSelectedId(asset.id);
      setNotice(null);
    } catch (error) {
      fail(error);
    } finally {
      await Promise.all([refreshBalance(), refreshProjects()]);
      setBusy(null);
    }
  }

  function toggleProjectSelected(id: string) {
    setSelectedProjects((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function deleteProject(id: string) {
    if (!window.confirm("Delete this look? This can't be undone.")) return;
    setDeletingProjects((current) => new Set(current).add(id));
    try {
      await getServices().lookProjects.remove(id);
      setProjects((current) => current.filter((p) => p.id !== id));
      setSelectedProjects((current) => {
        if (!current.has(id)) return current;
        const next = new Set(current);
        next.delete(id);
        return next;
      });
      if (projectId === id) setProjectId(null);
    } catch (error) {
      fail(error);
    } finally {
      setDeletingProjects((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    }
  }

  async function deleteSelectedProjects() {
    const ids = [...selectedProjects];
    if (!ids.length) return;
    if (!window.confirm(`Delete ${ids.length} look${ids.length === 1 ? "" : "s"}? This can't be undone.`))
      return;
    setDeletingProjects((current) => {
      const next = new Set(current);
      for (const id of ids) next.add(id);
      return next;
    });
    const results = await Promise.allSettled(ids.map((id) => getServices().lookProjects.remove(id)));
    const removed = new Set(ids.filter((_, index) => results[index].status === "fulfilled"));
    setProjects((current) => current.filter((p) => !removed.has(p.id)));
    setSelectedProjects((current) => new Set([...current].filter((id) => !removed.has(id))));
    if (projectId && removed.has(projectId)) setProjectId(null);
    setDeletingProjects((current) => {
      const next = new Set(current);
      for (const id of ids) next.delete(id);
      return next;
    });
    if (removed.size < ids.length) setNotice({ tone: "error", text: "Some looks couldn't be deleted. Try again." });
  }

  async function openProject(id: string) {
    if (busy) return;
    setBusy("project");
    setNotice(null);
    try {
      const { project } = await getServices().lookProjects.get(id);
      setProjectId(project.id);
      setProducts(project.products);
      setModel(project.model);
      setScene(project.scene);
      setRatio(project.aspectRatio);
      setLibrary(null);
      setResults(project.photos.map(({ asset, label }) => ({ asset, label })));
      setSelectedId(project.photos[1]?.asset.id ?? project.photos[0]?.asset.id ?? null);
      setTimeout(
        () => document.getElementById("look-results")?.scrollIntoView({ behavior: "smooth", block: "start" }),
        0,
      );
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  }

  async function generateVideo() {
    if (!products.length || busy) return;
    if (ratio === "4:5") {
      setNotice({ tone: "error", text: "Video is available in 9:16, 1:1 or 16:9. Choose one of those frames." });
      return;
    }
    setBusy("video");
    setNotice({ tone: "status", text: "Planning your video…" });
    stopPolling.current?.();
    try {
      const services = getServices();
      const inputAssets = lookAssets();
      const setting = scenes.find(([id]) => id === scene)?.[3];
      const session = await services.chat.create();
      const answered = await services.chat.send(session.id, {
        text: "Create a product video that shows every supplied item clearly.",
        intent: "message",
        context: {
          templateId: "auto",
          inputAssets,
          duration: 15,
          aspectRatio: ratio,
          ...(setting ? { brief: `Scene: ${setting}.` } : {}),
        },
      });
      const recipe = answered.answer?.recipe;
      if (!recipe) {
        setNotice({
          tone: "error",
          text: answered.answer?.clarificationQuestion || "The director needs more to plan this video.",
        });
        return;
      }
      const applied = await services.chat.apply(session.id, {
        revision: answered.revision,
        creative: {
          templateId: "auto",
          inputAssets,
          duration: 15,
          aspectRatio: ratio,
          brief: recipe.concept,
        },
      });
      const quoted = await services.credits.get(
        estimateInput(applied.creative, applied.prompt.promptId, "auto"),
      );
      setBalance(quoted.balance);
      if (!quoted.quote) throw new Error("This video could not be priced. Please try again.");
      if (quoted.balance < quoted.quote.creditsEstimated) {
        setNotice({
          tone: "error",
          text: `This video needs ${quoted.quote.creditsEstimated} credits and you have ${quoted.balance}.`,
        });
        return;
      }
      const { generation } = await services.generations.create(
        {
          ...applied.creative,
          model: "auto",
          voice: "auto",
          quality: "auto",
          promptId: applied.prompt.promptId,
          prompt: applied.prompt.prompt,
          quoteId: quoted.quote.id,
        },
        crypto.randomUUID(),
      );
      setVideo(generation);
      setNotice(null);
      stopPolling.current = pollGeneration(
        services.generations,
        generation.id,
        async (job) => {
          setVideo(job);
          if (["completed", "failed", "cancelled"].includes(job.status)) {
            stopPolling.current?.();
            await refreshBalance();
          }
        },
        () => undefined,
      );
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="look-studio" id="create">
      <header className="look-studio-header">
        <div>
          <h1>Product Look Studio</h1>
          <p>Create beautiful product photos and videos. Your product. Your model. Your story.</p>
        </div>
        <div className="look-studio-utilities">
          <span className="look-credit">
            <Coins size={16} />
            {balance === null ? "—" : balance.toLocaleString()} credits
          </span>
          <button type="button" aria-label="Help"><HelpCircle size={18} /></button>
          <button type="button" aria-label="Notifications"><Bell size={18} /></button>
          <span className="look-avatar" aria-label="Account">F</span>
        </div>
      </header>

      <section className="look-intro" aria-labelledby="look-intro-title">
        <div className="look-intro-copy">
          <span>GET STARTED</span>
          <h2 id="look-intro-title">Turn your products<br />into <em>real looks</em></h2>
          <p>Upload your products, choose a model and scene, then generate photos or a video. Fast, easy and made for e-commerce.</p>
          <button type="button" className="look-watch"><span><Play size={16} fill="currentColor" /></span><strong>Watch how it works<small>2 min</small></strong></button>
        </div>
        <div className="look-story" aria-label="Three steps from products to video">
          <article>
            <div className="look-step-title"><b>1</b><span>Add products<br />and a model</span></div>
            <div className="look-step-products">
              <img src="/try-on/clothing-header.png" alt="Blazer, top, handbag, sunglasses and bracelet" />
              <button type="button" disabled={!!busy} onClick={() => productInput.current?.click()}><ImagePlus size={18} />Add your items</button>
            </div>
          </article>
          <ArrowRight className="look-story-arrow" size={20} />
          <article>
            <div className="look-step-title"><b>2</b><span>Generate photos from<br />multiple angles</span></div>
            <div className="look-angle-stack">
              <img src="/try-on/person.png" alt="Model preview" />
              <img src="/try-on/person.png" alt="" />
              <img src="/try-on/person.png" alt="" />
            </div>
          </article>
          <ArrowRight className="look-story-arrow" size={20} />
          <article>
            <div className="look-step-title"><b>3</b><span>Turn the best look<br />into a video</span></div>
            <div className="look-video-sample">
              <video src="/try-on/hero-video.mp4" aria-label="Generated fashion video preview" autoPlay loop muted playsInline preload="auto" />
            </div>
          </article>
        </div>
      </section>

      <section className="look-builder" aria-labelledby="look-builder-title">
        <div className="look-builder-heading">
          <h2 id="look-builder-title">Create Your Look</h2>
          <div className="look-progress" aria-label="Creation progress">
            {["Products", "Model (optional)", "Scene & Style", "Generate"].map((label, index) => (
              <span key={label} className={index === step ? "is-active" : ""} aria-current={index === step ? "step" : undefined}><b>{index + 1}</b>{label}</span>
            ))}
          </div>
        </div>

        <div className="look-builder-grid">
          <section className="look-input-card look-products-card">
            <div className="look-card-title"><strong>Products</strong><span>{products.length} / {LOOK_SIZE} items</span></div>
            <input ref={productInput} className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={addProducts} aria-label="Product images" />
            <div className="look-upload-visual" aria-hidden="true">
              {(products.length
                ? products.map((asset) => ({ key: asset.id, url: asset.url }))
                : productArtwork.map((url) => ({ key: url, url }))
              ).slice(0, 3).map(({ key, url }) => <img key={key} src={url} alt="" />)}
              <img className="look-add-art" src="/try-on/button.png" alt="" />
            </div>
            <strong>{products.length ? `${products.length} product${products.length === 1 ? "" : "s"} added` : "Add your products"}</strong>
            <p>Upload clothing, accessories or any product images</p>
            <button type="button" className="button button-primary" disabled={!!busy || products.length >= LOOK_SIZE} onClick={() => productInput.current?.click()}>
              <Upload size={15} />{busy === "products" ? "Uploading…" : "Upload products"}
            </button>
            {(products.length > 0 || model) && (
              <button type="button" className="button button-secondary look-clear" disabled={!!busy} onClick={clearImports}>
                <X size={15} />Clear imports
              </button>
            )}
            <small>PNG, JPG or WebP · max 10 MB each</small>

            <div className="look-catalog-import">
              <input ref={csvInput} className="sr-only" type="file" accept=".csv,text/csv" onChange={importCsv} aria-label="Catalog CSV" />
              <button type="button" className="button button-secondary" disabled={!!busy} onClick={() => csvInput.current?.click()}>
                <FileUp size={15} />{busy === "catalog" ? "Importing…" : "Bulk import (CSV)"}
              </button>
              <small className="look-catalog-format">
                Columns: url or imageUrl (one required per row), name (optional) · up to 30 rows
              </small>
              <a href="/try-on/catalog-sample.csv" download className="look-sample-link">Download sample CSV</a>
              {csvResult && (
                <p className="look-catalog-result" role="status">
                  {csvResult.created} added{csvResult.errors.length ? `, ${csvResult.errors.length} skipped` : ""}.
                  {csvResult.errors.length > 0 && (
                    <span className="look-catalog-errors">
                      {csvResult.errors.map((e) => ` Row ${e.row}: ${e.message}`).join(" ")}
                    </span>
                  )}
                </p>
              )}
              <button type="button" className="button button-secondary" disabled={!!busy} aria-expanded={productLibrary !== null} onClick={() => void toggleProductLibrary()}>
                <ImagePlus size={15} />{busy === "product-library" ? "Loading…" : "Choose from product library"}
              </button>
              {productLibrary !== null && (
                <div className="look-library" role="region" aria-label="Your product library">
                  <div className="look-library-head">
                    <strong>Your product library</strong>
                    <button type="button" aria-label="Close product library" onClick={() => setProductLibrary(null)}><X size={14} /></button>
                  </div>
                  {productLibrary.length ? (
                    <div className="look-library-grid">
                      {productLibrary.map((asset) => (
                        <button
                          key={asset.id}
                          type="button"
                          aria-pressed={products.some((item) => item.id === asset.id)}
                          aria-label={`Use ${asset.fileName}`}
                          disabled={products.length >= LOOK_SIZE && !products.some((item) => item.id === asset.id)}
                          onClick={() => pickProduct(asset)}
                        >
                          <img src={asset.url} alt="" />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p>No catalog products yet. Import a CSV and they will be here.</p>
                  )}
                </div>
              )}
            </div>
          </section>

          <section className="look-input-card look-model-card">
            <div className="look-card-title"><strong>Model <span>(optional)</span></strong></div>
            <input ref={modelInput} className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseModel} aria-label="Model photo" />
            <button type="button" className="look-model-visual" disabled={!!busy} onClick={() => modelInput.current?.click()} aria-label="Upload model photo">
              <img src={model?.url ?? "/try-on/person.png"} alt={model ? `Selected model: ${model.fileName}` : "Model upload example"} />
              <span><img src="/try-on/button.png" alt="" /></span>
            </button>
            <strong>{busy === "model" ? "Uploading…" : model ? "Replace model photo" : "Upload model photo"}</strong>
            <p>Photos need a model. A video can be made from products alone.</p>
            <button type="button" className="button button-secondary" disabled={!!busy} aria-expanded={library !== null} onClick={() => void toggleLibrary()}>
              <UserRound size={15} />{busy === "library" ? "Loading…" : "Choose from library"}
            </button>
            {library !== null && (
              <div className="look-library" role="region" aria-label="Your model photos">
                <div className="look-library-head">
                  <strong>Your model photos</strong>
                  <button type="button" aria-label="Close library" onClick={() => setLibrary(null)}><X size={14} /></button>
                </div>
                {library.length ? (
                  <div className="look-library-grid">
                    {library.map((asset) => (
                      <button key={asset.id} type="button" aria-pressed={model?.id === asset.id} aria-label={`Use ${asset.fileName}`} onClick={() => pickModel(asset)}>
                        <img src={asset.url} alt="" />
                      </button>
                    ))}
                  </div>
                ) : (
                  <p>No model photos yet. Upload one and it will be here next time.</p>
                )}
              </div>
            )}
          </section>

          <section className="look-input-card look-style-card">
            <div className="look-card-title"><strong>Scene &amp; Style</strong></div>
            <div className="look-scene-options">
              {scenes.map(([id, label, Icon]) => <button key={id} type="button" className={scene === id ? "is-selected" : ""} aria-pressed={scene === id} onClick={() => setScene(id)}><Icon size={19} strokeWidth={1.6} />{label}</button>)}
            </div>
            <fieldset>
              <legend>Aspect ratio</legend>
              <div className="look-ratio-options">
                {ratios.map(([id, label, Icon]) => <button key={id} type="button" className={ratio === id ? "is-selected" : ""} aria-pressed={ratio === id} onClick={() => setRatio(id)}><Icon size={19} strokeWidth={1.6} />{id}<small>{label}</small></button>)}
              </div>
            </fieldset>
          </section>

          <aside className="look-generate-card">
            <div className="look-card-title"><strong>Generate photos</strong></div>
            <div className="look-output-options" role="radiogroup" aria-label="Photo output">
              <button type="button" role="radio" aria-checked={photoOutput === "hero"} className={photoOutput === "hero" ? "is-selected" : ""} onClick={() => setPhotoOutput("hero")}>
                <ImageIcon size={18} />
                <span><strong>1 hero photo</strong><small>One polished key image</small></span>
              </button>
              <button type="button" role="radio" aria-checked={photoOutput === "angles"} className={photoOutput === "angles" ? "is-selected" : ""} onClick={() => setPhotoOutput("angles")}>
                <Expand size={18} />
                <span><strong>4 angles</strong><small>Front · ¾ · Back · Detail</small></span>
                <em>Recommended</em>
              </button>
            </div>
            <p className="look-output-summary">
              {products.length && !model
                ? "Add a model photo to generate photos."
                : photoOutput === "angles"
                  ? "A consistent set for product pages and social."
                  : "A single campaign-ready product image."}
            </p>
            <button type="button" className="button button-primary" disabled={photosBlocked || !!busy} onClick={() => void generatePhotos()}>
              {busy === "photos" ? "Generating…" : photoOutput === "angles" ? "Generate 4 photos" : "Generate hero photo"} <ArrowRight size={15} />
            </button>
            <div className="look-or"><span>OR</span></div>
            <button type="button" className="button button-secondary" disabled={!products.length || !!busy} onClick={() => void generateVideo()}>
              <Play size={15} />{busy === "video" ? "Planning…" : "Generate Video Instead"}
            </button>
            <p className="look-video-direct">Skip photos and create a 15-second video directly.</p>
            <div className="look-pro-tip"><HelpCircle size={20} /><span><strong>Pro tip</strong>Use high-quality product images for the best results.</span></div>
          </aside>
        </div>

        {notice && (
          <p className="look-demo-notice" data-tone={notice.tone} role={notice.tone === "error" ? "alert" : "status"}>
            {notice.text}
          </p>
        )}

        {results.length > 0 && (
          <section className="look-results" id="look-results" aria-labelledby="look-results-title">
            <div className="look-results-head">
              <div>
                <span>YOUR GENERATED LOOK</span>
                <strong id="look-results-title">Explore every angle</strong>
              </div>
              <span className="look-results-count">
                {results.length} ready
                {results.length > 1 && (
                  <button type="button" className="look-download-all" disabled={downloadingAll} aria-label={`Download all photos (${results.length})`} onClick={() => void downloadAll()}>
                    <Download size={15} />{downloadingAll ? "Preparing ZIP…" : "Download all photos"}
                  </button>
                )}
              </span>
            </div>
            <div className="look-gallery-layout">
              <aside className="look-stack" aria-label="Items used in this look">
                <div>
                  <strong>Look stack</strong>
                  <span>{products.length + (model ? 1 : 0)} pieces</span>
                </div>
                <div className="look-stack-list">
                  {model && (
                    <figure>
                      <img src={model.url} alt="Model used in this look" />
                      <figcaption>Model</figcaption>
                    </figure>
                  )}
                  {products.map((asset, index) => (
                    <figure key={asset.id}>
                      <img src={asset.url} alt={`${itemLabel(asset)} used in this look`} />
                      <figcaption>{itemLabel(asset) || `Item ${index + 1}`}</figcaption>
                    </figure>
                  ))}
                </div>
              </aside>

              <div
                className="look-gallery"
                role="region"
                aria-label="Generated look gallery"
                aria-roledescription="carousel"
                tabIndex={0}
                onWheel={handleGalleryWheel}
                onPointerDown={handleGalleryPointerDown}
                onPointerUp={handleGalleryPointerUp}
                onPointerCancel={() => { galleryPointerStart.current = null; }}
                onKeyDown={handleGalleryKeyDown}
              >
                <div className="look-gallery-stage">
                  {results.map(({ asset, label }, index) => {
                    const offset = galleryOffset(index);
                    const visible = Math.abs(offset) <= 2;
                    const isActive = index === selectedIndex;
                    return (
                      <button
                        key={asset.id}
                        type="button"
                        className="look-gallery-card"
                        data-offset={Math.max(-2, Math.min(2, offset))}
                        aria-current={isActive ? "true" : undefined}
                        aria-hidden={!visible}
                        tabIndex={visible ? 0 : -1}
                        onClick={() => setSelectedId(asset.id)}
                      >
                        <img src={asset.url} alt={`${label} view of the look`} draggable={false} />
                        <span className="look-gallery-label">
                          <b>{String(index + 1).padStart(2, "0")}</b>
                          <small>{label}</small>
                        </span>
                      </button>
                    );
                  })}
                </div>
                <div className="look-gallery-guide" aria-hidden="true">
                  <span>Scroll or drag to explore</span>
                  <div>{results.map((result, index) => <i key={result.asset.id} className={index === selectedIndex ? "is-active" : ""} />)}</div>
                  <b>{String(selectedIndex + 1).padStart(2, "0")} / {String(results.length).padStart(2, "0")}</b>
                </div>
              </div>
            </div>
            {selected && (
              <div className="look-result-actions">
                <div className="look-angle-generator">
                  <div className="look-angle-generator-copy">
                    <span><ImagePlus size={13} />Additional generation</span>
                    <strong>Another angle of the selected photo</strong>
                    <small>Choose a view to generate one new matching photo.</small>
                  </div>
                  <div role="group" aria-label="Generate an additional angle">
                    {ANGLES.map((angle) => (
                      <button key={angle.id} type="button" disabled={!!busy} onClick={() => void anotherAngle(angle)}>
                        <ImagePlus size={14} />{angle.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {video && (
          <section className="look-video-result" aria-labelledby="look-video-title">
            <div className="look-card-title">
              <strong id="look-video-title">Your video</strong>
              <span>{video.status}</span>
            </div>
            {output ? (
              <video src={output.url} controls playsInline preload="metadata" aria-label="Generated product video" />
            ) : video.status === "failed" || video.status === "cancelled" ? (
              <p role="alert">{video.error?.message || "The video could not be generated."}</p>
            ) : (
              <p role="status">Generating your video… this usually takes about three minutes. It will also appear in your Library.</p>
            )}
          </section>
        )}

        {projects.length > 0 && (
          <section className="look-projects" aria-labelledby="look-projects-title">
            <div className="look-card-title">
              <strong id="look-projects-title">Your looks</strong>
              <span>{projects.length} {projects.length === 1 ? "project" : "projects"}</span>
              <button
                type="button"
                className="look-select-toggle"
                onClick={() => {
                  setSelectProjectsMode((current) => !current);
                  setSelectedProjects(new Set());
                }}
              >
                {selectProjectsMode ? "Done" : "Select"}
              </button>
            </div>
            {selectProjectsMode && (
              <div className="look-bulk-bar" role="group" aria-label="Bulk actions">
                <span>{selectedProjects.size} selected</span>
                <button
                  type="button"
                  className="look-bulk-delete"
                  onClick={() => void deleteSelectedProjects()}
                  disabled={!selectedProjects.size}
                >
                  <Trash2 size={14} /> Delete selected
                </button>
              </div>
            )}
            <div className="look-projects-grid">
              {projects.map((project, index) => {
                const isSelected = selectedProjects.has(project.id);
                const isDeleting = deletingProjects.has(project.id);
                return (
                  <article key={project.id} className="look-project-card" data-busy={isDeleting}>
                    <button
                      type="button"
                      className={projectId === project.id ? "is-selected" : ""}
                      aria-pressed={selectProjectsMode ? isSelected : projectId === project.id}
                      disabled={!!busy || isDeleting}
                      onClick={() =>
                        selectProjectsMode ? toggleProjectSelected(project.id) : void openProject(project.id)
                      }
                    >
                      {project.coverUrl ? (
                        <img src={project.coverUrl} alt="" />
                      ) : (
                        <span className="look-project-empty"><Folder size={22} /></span>
                      )}
                      <strong>Look {projects.length - index}</strong>
                      <small>
                        {project.photoCount} photo{project.photoCount === 1 ? "" : "s"} · {new Date(project.createdAt).toLocaleDateString()}
                      </small>
                    </button>
                    {selectProjectsMode ? (
                      <span className="look-select-mark" aria-hidden="true">
                        {isSelected ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="look-project-delete"
                        aria-label="Delete this look"
                        title="Delete this look"
                        disabled={isDeleting}
                        onClick={() => void deleteProject(project.id)}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        )}
      </section>
    </main>
  );
}
