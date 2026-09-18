import { expect, it } from "vitest";
import { estimateInput } from "../services/estimate";
it("projects only public estimate fields so strict FastAPI validation accepts it", () => {
  const estimate = estimateInput(
    {
      templateId: "ugc_review",
      duration: 15,
      aspectRatio: "9:16",
      inputAssets: { productImageId: "asset" },
      brief: "Secret campaign brief",
    },
    "prompt",
    "auto",
  );
  expect(estimate).not.toHaveProperty("brief");
  expect(estimate).toEqual({
    templateId: "ugc_review",
    duration: 15,
    aspectRatio: "9:16",
    inputAssets: { productImageId: "asset" },
    productUrl: undefined,
    promptId: "prompt",
    model: "auto",
    voice: "auto",
    quality: "auto",
  });
});
