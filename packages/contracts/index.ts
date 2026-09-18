export type * from "./chat";
export type * from "./subtitles";
export type Duration = number;
export type AspectRatio = "9:16" | "1:1" | "16:9";
export type GenerationStatus =
  | "queued"
  | "generating"
  | "completed"
  | "failed"
  | "cancelled";
export type AssetRole =
  | "product"
  | "person"
  | "source_video"
  | "output_video"
  | "thumbnail"
  | "tryon_photo";
export interface ApiError {
  code: string;
  message: string;
  retryable: boolean;
  fieldErrors?: Record<string, string[]>;
}
export interface Asset {
  id: string;
  role: AssetRole;
  kind: "image" | "video";
  mimeType: string;
  fileName: string;
  sizeBytes: number;
  url: string;
  urlExpiresAt: string | null;
  width: number | null;
  height: number | null;
  durationSeconds: number | null;
  createdAt: string;
}
/** Product images shown together as one look; mirrors LOOK_SIZE in the API schemas. */
export const LOOK_SIZE = 5;
export interface LookItem {
  assetId: string;
  label: string;
}
export interface InputAssets {
  productImageId?: string;
  personImageId?: string;
  sourceVideoId?: string;
  /** Extra pieces shown together with the main product, e.g. glasses plus a scarf. */
  items?: LookItem[];
}
export interface CreativeInput {
  language?: string | null;
  productUrl?: string;
  inputAssets: InputAssets;
  templateId: string;
  brief: string;
  normalizedInputs?: NormalizedTemplateInputs;
  duration: Duration;
  aspectRatio: AspectRatio;
}
export interface RenderSettings {
  model: string;
  voice: string;
  quality?: string;
  resolution?: string;
}
export interface PromptResult {
  promptId: string;
  prompt: string;
  inputFingerprint: string;
  createdAt: string;
}
export interface EstimateInput extends RenderSettings {
  templateId: string;
  duration: Duration;
  aspectRatio: AspectRatio;
  inputAssets: InputAssets;
  productUrl?: string;
  promptId?: string;
  normalizedInputs?: NormalizedTemplateInputs;
}
export interface GenerationInput extends CreativeInput, RenderSettings {
  promptId?: string;
  prompt?: string;
  quoteId: string;
}
export interface CreditQuote {
  id: string;
  creditsEstimated: number;
  expiresAt: string;
}
export interface Credits {
  balance: number;
  quote: CreditQuote | null;
  updatedAt: string;
}
export interface Generation {
  id: string;
  userId: string;
  templateId: string;
  model: string;
  provider: string | null;
  status: GenerationStatus;
  progress: number | null;
  prompt: string | null;
  normalizedInputs?: NormalizedTemplateInputs | null;
  creativeMechanism?: string | null;
  duration: Duration;
  aspectRatio: AspectRatio;
  inputAssets: Asset[];
  outputAssets: Asset[];
  creditsEstimated: number;
  creditsCharged: number;
  error: ApiError | null;
  createdAt: string;
  updatedAt: string;
}
export type NormalizedTemplateInputs = Record<
  string,
  string | number | boolean | string[]
>;
export interface TemplateInputProperty {
  type: "string" | "number" | "integer" | "boolean" | "array";
  title?: string;
  description?: string;
  default?: string | number | boolean | string[];
  enum?: string[];
  format?: string;
  mediaType?: "image" | "video";
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  minItems?: number;
  maxItems?: number;
  items?: { type: string; format?: string };
}
export interface TemplateInputSchema {
  type: "object";
  properties: Record<string, TemplateInputProperty>;
  required?: string[];
  additionalProperties?: boolean;
}
export interface TemplateFilters {
  search?: string;
  category?: string;
  templateType?: string;
  aspectRatio?: string;
  duration?: string;
  inputType?: string;
  useCase?: string;
  featured?: string | boolean;
  enabled?: string | boolean;
}
export interface VideoTemplate {
  id: string;
  name: string;
  description: string;
  slug?: string;
  version?: string;
  category?: string;
  templateType?: "generative" | "remotion";
  thumbnail?: string | null;
  previewVideo?: string | null;
  enabled?: boolean;
  featured?: boolean;
  tags?: string[];
  supportedAspectRatios?: AspectRatio[];
  supportedDurations?: number[];
  inputSchema?: TemplateInputSchema;
  useCases?: string[];
  thumbnailUrl: string | null;
  available: boolean;
  unavailableReason: string | null;
}
export interface ModelOption {
  id: string;
  label: string;
  available: boolean;
  unavailableReason: string | null;
  configurations: {
    duration: Duration;
    aspectRatio: AspectRatio;
    quality: string | null;
    resolution: string | null;
    supportsPersonImage: boolean;
    supportsSourceVideo: boolean;
  }[];
  voices: { id: string; label: string }[];
}
export interface Product {
  url: string;
  title: string;
  description: string;
  imageUrl: string | null;
}
export interface BillingSummary {
  plan: string;
  status: string;
  renewalDate: string | null;
  prices: { id: string; label: string }[];
}
export interface TryOnAngle {
  id: "front" | "three_quarter" | "back" | "detail";
  label: string;
}
// One value wider than the video AspectRatio: a still photo can use 4:5, video cannot.
export type PhotoAspectRatio = AspectRatio | "4:5";
export interface TryOnInput {
  inputAssets: InputAssets;
  aspectRatio: PhotoAspectRatio;
  angle?: TryOnAngle["id"];
  baseAssetId?: string;
  idempotencyKey: string;
  /** The project folder the photo is saved into, so it survives a reload. */
  projectId?: string;
}
export interface TryOnResult {
  asset: Asset;
  creditsCharged: number;
}
export type LookScene = "studio" | "lifestyle" | "outdoor" | "custom";
export interface LookProjectInput {
  inputAssets: InputAssets;
  scene: LookScene;
  aspectRatio: PhotoAspectRatio;
}
export interface LookPhoto {
  asset: Asset;
  label: string;
}
/** One try-on generation shown as a folder. */
export interface LookProjectSummary {
  id: string;
  scene: LookScene;
  aspectRatio: PhotoAspectRatio;
  photoCount: number;
  coverUrl: string | null;
  createdAt: string;
  updatedAt: string;
}
export interface LookProjectDetail {
  id: string;
  scene: LookScene;
  aspectRatio: PhotoAspectRatio;
  inputAssets: InputAssets;
  model: Asset | null;
  products: Asset[];
  photos: LookPhoto[];
  createdAt: string;
  updatedAt: string;
}
export interface Services {
  chat: import("./chat").ChatService;
  assets: {
    upload(
      file: File,
      role: "product" | "person" | "source_video",
      // Marks the module an upload came from, so that module can list only its own.
      source?: "try_on",
      /** Real upload progress, 0-100, for large files such as source videos. */
      onProgress?: (percent: number) => void,
    ): Promise<{ asset: Asset }>;
    uploadMany(files: File[]): Promise<{ assets: Asset[] }>;
    /** The user's own earlier model photos or catalog-imported products, newest first. */
    list(role: "person" | "product", source: "try_on"): Promise<{ assets: Asset[] }>;
    /** Bulk-populates the product library from a CSV of product pages or direct image URLs
     * (columns: url and/or imageUrl, optional name). A bad row is reported, not fatal. */
    importCatalogCsv(
      file: File,
    ): Promise<{ created: Asset[]; errors: { row: number; message: string }[] }>;
  };
  tryOn: { preview(input: TryOnInput): Promise<TryOnResult> };
  lookProjects: {
    create(input: LookProjectInput): Promise<{ project: LookProjectDetail }>;
    list(): Promise<{ projects: LookProjectSummary[] }>;
    get(id: string): Promise<{ project: LookProjectDetail }>;
    remove(id: string): Promise<void>;
  };
  subtitleProjects: import("./subtitles").SubtitleService;
  products: {
    resolve(url: string): Promise<{ product: Product; asset: Asset | null }>;
  };
  templates: {
    list(filters?: TemplateFilters): Promise<{ templates: VideoTemplate[] }>;
  };
  models: { list(): Promise<{ models: ModelOption[] }> };
  prompts: { generate(input: CreativeInput): Promise<PromptResult> };
  generations: {
    create(
      input: GenerationInput,
      key: string,
    ): Promise<{ generation: Generation }>;
    get(
      id: string,
    ): Promise<{ generation: Generation; pollAfterMs: number | null }>;
    list(
      cursor?: string,
    ): Promise<{ generations: Generation[]; nextCursor: string | null }>;
    cancel(id: string): Promise<{ generation: Generation }>;
    remove(id: string): Promise<void>;
  };
  credits: { get(estimate?: EstimateInput): Promise<Credits> };
  billing: {
    summary(): Promise<BillingSummary>;
    checkout(
      priceId: string,
    ): Promise<{ sessionId: string; checkoutUrl: string; expiresAt: string }>;
    portal(): Promise<{ portalUrl: string; expiresAt: string }>;
  };
}
