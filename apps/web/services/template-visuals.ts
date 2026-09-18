import type { VideoTemplate } from "@ugc/contracts";

/** Product-facing artwork is deliberately independent from a template engine. */
const coreTemplateArtwork: Record<string, string> = {
  ugc_review: "/template-styles/ugc-review.webp",
  product_unboxing: "/template-styles/product-unboxing.webp",
  problem_solution: "/template-styles/problem-solution.webp",
  product_demo: "/template-styles/product-demo.webp",
  testimonial: "/template-styles/testimonial.webp",
  trending_style: "/template-styles/trending-style.webp",
  hook_cta: "/template-styles/hook-cta.webp",
  before_after: "/template-styles/before-after.webp",
  // Placeholder until dedicated self-presentation artwork exists.
  self_presentation: "/template-styles/testimonial.webp",
};

export function templateArtwork(
  template: Pick<VideoTemplate, "id" | "thumbnailUrl">,
) {
  return coreTemplateArtwork[template.id] ?? template.thumbnailUrl;
}
