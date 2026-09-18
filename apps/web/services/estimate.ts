import type { CreativeInput, EstimateInput } from "@ugc/contracts";
export function estimateInput(
  draft: CreativeInput,
  promptId: string | undefined,
  model: string,
): EstimateInput {
  return {
    templateId: draft.templateId,
    duration: draft.duration,
    aspectRatio: draft.aspectRatio,
    inputAssets: draft.inputAssets,
    productUrl: draft.productUrl,
    promptId,
    ...(draft.normalizedInputs
      ? { normalizedInputs: draft.normalizedInputs }
      : {}),
    model,
    voice: "auto",
    quality: "auto",
  };
}
