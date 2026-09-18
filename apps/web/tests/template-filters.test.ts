import { describe, expect, it } from "vitest";
import fixtures from "../../../packages/contracts/template-filter-cases.json";
import type { VideoTemplate } from "@ugc/contracts";
import {
  filterTemplates,
  filterQuery,
  readFilters,
  featuredTemplates,
  creationTemplates,
} from "../services/template-filters";
import { mockTemplates } from "../services/mock";

const currentTemplateIds = [
  "ugc_review",
  "product_unboxing",
  "problem_solution",
  "product_demo",
  "testimonial",
  "trending_style",
  "hook_cta",
  "before_after",
  "self_presentation",
];

it("exposes only the nine current templates in mock mode", () => {
  expect(mockTemplates.map((template) => template.id)).toEqual(currentTemplateIds);
});
describe("catalog filters share server AND semantics", () => {
  for (const [i, c] of fixtures.cases.entries())
    it(`shared filter vector ${i}`, () => {
      expect(
        filterTemplates(
          fixtures.templates as unknown as VideoTemplate[],
          c.filters,
        ).map((t) => t.id),
      ).toEqual(c.expected);
    });
  it("round trips all filters in URLs and clears empty values", () => {
    const f = {
      search: "Bold & clear",
      category: "text-animations",
      templateType: "remotion",
      aspectRatio: "9:16",
      duration: "up-to-15",
      inputType: "text-only",
      useCase: "social-ad",
    };
    expect(readFilters(new URLSearchParams(filterQuery(f)))).toEqual(f);
    expect(filterQuery({ search: "", category: "" })).toBe("");
    expect(readFilters(new URLSearchParams("unknown=thing"))).toEqual({});
  });
  it("keeps Create a featured collection of at most eight", () => {
    const list = Array.from(
      { length: 81 },
      (_, i) =>
        ({ id: String(i), available: true, featured: i < 9 }) as VideoTemplate,
    );
    expect(featuredTemplates(list)).toHaveLength(8);
    expect(featuredTemplates(list).every((t) => t.featured)).toBe(true);
  });
});

it.each(["ugc_review", "catalog-only"])(
  "keeps selected %s visible within seven style cards",
  (selectedId) => {
    const featured = Array.from(
      { length: 8 },
      (_, i) =>
        ({
          id: `render_${i}`,
          templateType: "remotion",
          available: true,
          featured: true,
        }) as VideoTemplate,
    );
    const selected = {
      id: selectedId,
      available: true,
      featured: false,
    } as VideoTemplate;
    const visible = creationTemplates([...featured, selected], selectedId);
    expect(visible).toHaveLength(7);
    expect(visible.some((t) => t.id === selectedId)).toBe(true);
    expect(new Set(visible.map((t) => t.id)).size).toBe(7);
  },
);

it("hides disabled records by default and exposes them only with explicit false", () => {
  const records = [
    { id: "enabled", enabled: true, available: true },
    { id: "disabled", enabled: false, available: false },
  ] as VideoTemplate[];
  for (const filters of [{}, { enabled: undefined }, { enabled: null }]) {
    expect(filterTemplates(records, filters).map((t) => t.id)).toEqual([
      "enabled",
    ]);
  }
  expect(filterTemplates(records, { enabled: false }).map((t) => t.id)).toEqual(
    ["disabled"],
  );
  expect(
    filterTemplates(records, { enabled: "false" }).map((t) => t.id),
  ).toEqual(["disabled"]);
});
