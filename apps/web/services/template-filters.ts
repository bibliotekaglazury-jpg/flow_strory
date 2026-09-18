import type { TemplateFilters, VideoTemplate } from "@ugc/contracts";
export const filterKeys = [
  "search",
  "category",
  "templateType",
  "aspectRatio",
  "duration",
  "inputType",
  "useCase",
  "featured",
  "enabled",
] as const;
export const slug = (s: string) =>
  s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
export function readFilters(params: URLSearchParams): TemplateFilters {
  return Object.fromEntries(
    filterKeys.flatMap((k) => (params.get(k) ? [[k, params.get(k)!]] : [])),
  );
}
export function filterQuery(filters: TemplateFilters) {
  return new URLSearchParams(
    Object.entries(filters)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();
}
export function templateInputTypes(t: VideoTemplate): Set<string> {
  const types = new Set<string>();
  for (const [field, p] of Object.entries(t.inputSchema?.properties ?? {})) {
    const name = field.toLowerCase();
    if (["producturl", "product_url"].includes(name)) types.add("product-url");
    else if (["productimage", "productimageid", "product_image"].includes(name))
      types.add("product-image");
    else if (
      [
        "personimage",
        "personimageid",
        "avatar",
        "person",
        "avatarimage",
      ].includes(name)
    )
      types.add("person-image");
    else if (/video/i.test(name + (p.mediaType ?? "") + (p.format ?? "")))
      types.add("existing-video");
    else if (/image/i.test(name + (p.mediaType ?? "") + (p.format ?? "")))
      types.add("images");
  }
  return types.size ? types : new Set(["text-only"]);
}
export function filterTemplates(
  templates: VideoTemplate[],
  filters: Omit<TemplateFilters, "enabled"> & {
    enabled?: TemplateFilters["enabled"] | null;
  },
) {
  const effectiveFilters = { ...filters, enabled: filters.enabled ?? true };
  return templates.filter((t) =>
    Object.entries(effectiveFilters).every(([key, value]) => {
      if (value === undefined || value === "") return true;
      const text = String(value);
      switch (key) {
        case "search":
          return [t.name, t.description, ...(t.tags ?? [])]
            .join(" ")
            .toLowerCase()
            .includes(text.toLowerCase());
        case "category":
          return slug(t.category ?? "UGC") === slug(text);
        case "templateType":
          return slug(t.templateType ?? "generative") === slug(text);
        case "aspectRatio":
          return (t.supportedAspectRatios ?? ["9:16", "1:1", "16:9"]).includes(
            value as never,
          );
        case "duration":
          return (t.supportedDurations ?? [15, 20, 30]).some((d) =>
            value === "up-to-15"
              ? d <= 15
              : value === "30-plus"
                ? d >= 30
                : d === Number(value),
          );
        case "inputType":
          return templateInputTypes(t).has(text);
        case "useCase":
          return (t.useCases ?? []).some((v) => slug(v) === slug(text));
        case "featured":
          return (t.featured ?? false) === (text === "true");
        case "enabled":
          return (t.enabled ?? t.available) === (text === "true");
        default:
          return true;
      }
    }),
  );
}
export function featuredTemplates(templates: VideoTemplate[]) {
  const featured = templates
    .filter((t) => t.featured && t.available)
    .sort(
      (a, b) =>
        Number(b.templateType === "generative") -
        Number(a.templateType === "generative"),
    );
  return (
    featured.length ? featured : templates.filter((t) => t.available)
  ).slice(0, 8);
}

export function creationTemplates(
  templates: VideoTemplate[],
  selectedId: string,
) {
  const generative = templates
    .filter(
      (t) => t.available && t.templateType === "generative",
    );
  const visible = (generative.length
    ? generative.slice(0, 9)
    : featuredTemplates(templates).slice(0, 7)
  ).slice();
  const selected = templates.find((t) => t.id === selectedId);
  if (selected && !visible.some((t) => t.id === selectedId)) {
    if (visible.length === (generative.length ? 9 : 7))
      visible[visible.length - 1] = selected;
    else visible.push(selected);
  }
  return visible;
}
