"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Shell } from "@/components/shell";
import { templateArtwork } from "@/services/template-visuals";
import { getServices } from "@/services";
import { filterQuery, readFilters, slug } from "@/services/template-filters";
import type { TemplateFilters, VideoTemplate } from "@ugc/contracts";
export function TemplateCatalog() {
  const params = useSearchParams(),
    router = useRouter();
  const query = params.toString(),
    filters = readFilters(new URLSearchParams(query));
  const [rows, setRows] = useState<VideoTemplate[]>([]);
  const [resultKey, setResultKey] = useState<string | null>(null),
    [error, setError] = useState<string | null>(null),
    [retry, setRetry] = useState(0);
  useEffect(() => {
    let live = true;
    getServices()
      .templates.list(readFilters(new URLSearchParams(query)))
      .then((r) => {
        if (live) {
          setRows([...r.templates].sort((a, b) =>
            Number(Boolean(b.featured)) - Number(Boolean(a.featured)) ||
            Number(b.templateType === "generative") -
              Number(a.templateType === "generative"),
          ));
          setError(null);
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setResultKey(query + retry);
      });
    return () => {
      live = false;
    };
  }, [query, retry]);
  const loading = resultKey !== query + retry;
  const update = (patch: TemplateFilters) => {
    const next = filterQuery({ ...filters, ...patch });
    router.push(`/templates${next ? `?${next}` : ""}`, { scroll: false });
  };
  const categories = [
    "UGC",
    "Product",
    "Social Ads",
    "Hooks",
    "Testimonials",
    "E-commerce",
    "Promos",
    "Branding",
    "Explainers",
    "Before / After",
    "Lifestyle",
    "SaaS",
    "Data / Metrics",
    "Other",
  ];
  const useCases = [
    "organic-social",
    "paid-ads",
    "product-showcase",
    "ugc",
    "branding",
  ];
  const controls: {
    key: keyof TemplateFilters;
    label: string;
    options: [string, string][];
  }[] = [
    {
      key: "templateType",
      label: "Type",
      options: [
        ["generative", "AI Generated"],
        ["remotion", "Render Template"],
      ],
    },
    {
      key: "aspectRatio",
      label: "Format",
      options: ["9:16", "1:1", "16:9"].map((v) => [v, v]),
    },
    {
      key: "duration",
      label: "Duration",
      options: [
        ["up-to-15", "Up to 15s"],
        ["20", "20s"],
        ["30-plus", "30s+"],
      ],
    },
    {
      key: "inputType",
      label: "Inputs",
      options: [
        ["product-image", "Product image"],
        ["product-url", "Product URL"],
        ["person-image", "Person / Avatar"],
        ["existing-video", "Existing video"],
        ["images", "Images"],
        ["text-only", "Text only"],
      ],
    },
    {
      key: "useCase",
      label: "Use case",
      options: useCases.map((v) => [
        slug(v),
        {
          "organic-social": "Organic social",
          "paid-ads": "Paid ads",
          "product-showcase": "Product showcase",
          ugc: "UGC",
          branding: "Branding",
        }[v] ?? v,
      ]),
    },
  ];
  return (
    <Shell>
      <section className="utility-page catalog" id="create">
        <h1>Templates</h1>
        <p>Choose a starting point for your next video.</p>
        <label className="catalog-search">
          Search templates
          <input
            type="search"
            value={filters.search ?? ""}
            onChange={(e) => update({ search: e.target.value })}
            placeholder="Search by name, description or tag"
          />
        </label>
        <div className="category-filters" aria-label="Categories">
          <button
            aria-pressed={!filters.category}
            onClick={() => update({ category: "" })}
          >
            All
          </button>
          {categories.slice(0, 5).map((v) => (
            <button
              key={v}
              aria-pressed={slug(v) === slug(filters.category ?? "")}
              onClick={() => update({ category: slug(v) })}
            >
              {v}
            </button>
          ))}
          {categories.length > 5 && (
            <label>
              More
              <select
                aria-label="More categories"
                value={
                  categories.slice(5).some((v) => slug(v) === filters.category)
                    ? filters.category
                    : ""
                }
                onChange={(e) => update({ category: e.target.value })}
              >
                <option value="">More categories</option>
                {categories.slice(5).map((v) => (
                  <option key={v} value={slug(v)}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div className="catalog-filters">
          {controls.map((c) => (
            <label key={c.key}>
              {c.label}
              <select
                aria-label={c.label}
                value={String(filters[c.key] ?? "")}
                onChange={(e) => update({ [c.key]: e.target.value })}
              >
                <option value="">All {c.label.toLowerCase()}</option>
                {c.options.map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
        <div className="catalog-summary">
          <span role="status">
            {loading ? "Loading templates…" : `${rows.length} templates`}
          </span>
          {Object.values(filters).some(Boolean) &&
            rows.length > 0 &&
            !loading && (
              <button
                className="text-button"
                onClick={() => router.push("/templates", { scroll: false })}
              >
                Clear all
              </button>
            )}
        </div>
        <div className="filter-chips">
          {Object.entries(filters)
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <button
                key={k}
                onClick={() => update({ [k]: "" })}
                aria-label={`Remove ${k} filter`}
              >
                {controls.find((c) => c.key === k)?.label ??
                  (k === "search" ? "Search" : "Category")}
                :{" "}
                {controls
                  .find((c) => c.key === k)
                  ?.options.find(([value]) => value === v)?.[1] ?? v}{" "}
                ×
              </button>
            ))}
        </div>
        {error && !loading ? (
          <div role="alert">
            <p>{error}</p>
            <button onClick={() => setRetry((r) => r + 1)}>
              Retry loading templates
            </button>
          </div>
        ) : !loading && !rows.length ? (
          <div className="history-empty">
            <p>No templates match these filters.</p>
            <button
              onClick={() => router.push("/templates", { scroll: false })}
            >
              Clear filters
            </button>
          </div>
        ) : (
          !loading && (
            <div className="template-gallery catalog-grid">
              {rows.map((t) => {
                const artwork = templateArtwork(t);
                return <Link
                  key={t.id}
                  href={`/?template=${encodeURIComponent(t.id)}`}
                  className="catalog-card"
                  aria-disabled={!t.available}
                  onClick={(e) => {
                    if (!t.available) e.preventDefault();
                  }}
                >
                  {artwork ? (
                    <img src={artwork} alt="" />
                  ) : (
                    <span className="image-placeholder" />
                  )}
                  <strong>{t.name}</strong>
                  <span>{t.description}</span>
                  <small>
                    {t.category} ·{" "}
                    {(t.supportedDurations ?? [15, 20, 30])
                      .map((d) => `${d}s`)
                      .join(" / ")}
                  </small>
                  {!t.available && (
                    <span>{t.unavailableReason ?? "Unavailable"}</span>
                  )}
                </Link>;
              })}
            </div>
          )
        )}
      </section>
    </Shell>
  );
}
