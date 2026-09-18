import { test, expect } from "@playwright/test";
import { filterTemplates, readFilters } from "../services/template-filters";
import type { VideoTemplate } from "@ugc/contracts";
const templates: VideoTemplate[] = Array.from({ length: 8 }, (_, i) => ({
  id: `fixture_${i}`,
  name: `Story ${i}`,
  description: "Catalog test fixture",
  thumbnailUrl: null,
  available: true,
  unavailableReason: null,
  templateType: "remotion",
  category: [
    "UGC",
    "Product",
    "E-commerce",
    "Social Ads",
    "Testimonials",
    "Hooks",
    "Promos",
    "Other",
  ][i],
  featured: true,
  supportedAspectRatios: ["9:16"],
  supportedDurations: [15],
  tags: ["motion"],
  useCases: ["social-ad"],
  inputSchema: {
    type: "object",
    properties: {
      headline: { type: "string", title: "Headline", default: "Hello" },
    },
  },
}));
test.beforeEach(async ({ page }) => {
  await page.route("**/api/templates**", (route) =>
    route.fulfill({
      json: {
        templates: filterTemplates(
          templates,
          readFilters(new URL(route.request().url()).searchParams),
        ),
      },
    }),
  );
});
test("catalog URL filters, count, chips, back/forward and zero clear", async ({
  page,
}) => {
  await page.goto("/templates");
  await expect(page.getByRole("status")).toHaveText("8 templates");
  await page.getByRole("button", { name: "UGC", exact: true }).click();
  await expect(page).toHaveURL(/category=ugc/);
  await expect(page.getByRole("status")).toHaveText("1 templates");
  await page.getByLabel("Search templates").fill("Missing");
  await expect(
    page.getByText("No templates match these filters."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Remove search filter" }).click();
  await expect(page.getByRole("status")).toHaveText("1 templates");
  await page.goBack();
  await expect(page.getByLabel("Search templates")).toHaveValue("Missing");
  await page.goForward();
  await expect(page.getByLabel("Search templates")).toHaveValue("");
  await page.getByRole("button", { name: "Clear all", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("8 templates");
  await page.getByLabel("More categories").selectOption("other");
  await expect(page.getByRole("status")).toHaveText("1 templates");
  await page.getByLabel("Type", { exact: true }).selectOption("generative");
  await expect(
    page.getByText("No templates match these filters."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("8 templates");
});
test("render template schema goes from estimate to submission without a prompt request", async ({
  page,
}) => {
  let estimate: Record<string, unknown> | undefined,
    submitted: Record<string, unknown> | undefined,
    promptCalls = 0;
  await page.route("**/api/templates**", (r) =>
    r.fulfill({
      json: {
        templates: [
          ...templates,
          {
            ...templates[0],
            id: "ugc_review",
            name: "UGC Review",
            templateType: "generative",
            inputSchema: undefined,
          },
        ],
      },
    }),
  );
  await page.route("**/api/models", (r) =>
    r.fulfill({
      json: {
        models: [
          { id: "auto", label: "Auto", available: true },
          { id: "manual-ai", label: "Manual AI", available: true },
        ],
      },
    }),
  );
  await page.route("**/api/credits**", (r) => {
    const raw = new URL(r.request().url()).searchParams.get("estimate");
    if (raw) estimate = JSON.parse(raw);
    return r.fulfill({
      json: {
        balance: 100,
        quote: raw
          ? {
              id: "quote",
              creditsEstimated: 3,
              expiresAt: new Date(Date.now() + 300000).toISOString(),
            }
          : null,
        updatedAt: new Date().toISOString(),
      },
    });
  });
  await page.route("**/api/prompts/**", (r) => {
    promptCalls++;
    return r.abort();
  });
  await page.route("**/api/generations", (r) => {
    if (r.request().method() === "POST") {
      submitted = r.request().postDataJSON();
      return r.fulfill({
        json: {
          generation: {
            id: "test",
            status: "failed",
            outputAssets: [],
            inputAssets: [],
            error: { message: "Test fixture" },
            createdAt: new Date().toISOString(),
          },
        },
      });
    }
    return r.fulfill({ json: { generations: [], nextCursor: null } });
  });
  // The strip shows the generative formats, so a render template is reached by link,
  // the same way the bounded-strip test below does it.
  await page.goto("/?template=fixture_0");
  await expect(
    page.locator(".style-option[aria-pressed=true]"),
  ).toContainText("Story 0");
  // A render template has no model choice to make: it is forced to auto by design,
  // which the model assertions at the end of this test still check.
  await expect(page.getByRole("button", { name: "Advanced options" })).toHaveCount(0);
  await expect(page.getByLabel("Headline", { exact: true })).toHaveValue(
    "Hello",
  );
  await page.getByLabel("Headline", { exact: true }).fill("Custom title");
  await expect(
    page.getByRole("button", { name: "Generate Prompt", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Get estimate", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /Generate Video/ }),
  ).toBeEnabled();
  await page.getByRole("button", { name: /Generate Video/ }).click();
  await expect.poll(() => submitted).toBeTruthy();
  expect(estimate?.normalizedInputs).toEqual({ headline: "Custom title" });
  expect(submitted?.normalizedInputs).toEqual({ headline: "Custom title" });
  expect(estimate?.model).toBe("auto");
  expect(submitted?.model).toBe("auto");
  expect(submitted?.promptId).toBeUndefined();
  expect(submitted?.prompt).toBeUndefined();
  expect(promptCalls).toBe(0);
});

test("nonfeatured deep-link selection stays visible in the bounded style strip", async ({
  page,
}) => {
  await page.route("**/api/templates**", (r) =>
    r.fulfill({
      json: {
        templates: [
          ...templates,
          {
            ...templates[0],
            id: "catalog-only",
            name: "Catalog only",
            featured: false,
          },
        ],
      },
    }),
  );
  await page.route("**/api/models", (r) => r.fulfill({ json: { models: [] } }));
  await page.route("**/api/credits**", (r) =>
    r.fulfill({ json: { balance: 100, quote: null } }),
  );
  await page.route("**/api/generations", (r) =>
    r.fulfill({ json: { generations: [], nextCursor: null } }),
  );
  await page.goto("/?template=catalog-only");
  await expect(page.locator(".style-option[aria-pressed=true]")).toContainText(
    "Catalog only",
  );
  await expect(page.locator(".style-option")).toHaveCount(7);
});
