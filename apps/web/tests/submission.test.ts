import { describe, expect, it } from "vitest";
import { prepareSubmission, submissionFailed } from "../services/submission";
import { ServiceError } from "../services/http";
import type { GenerationInput } from "@ugc/contracts";
const input: GenerationInput = {
  inputAssets: {},
  productUrl: "https://example.com/product",
  templateId: "ugc_review",
  brief: "A shoe",
  duration: 15,
  aspectRatio: "9:16",
  model: "auto",
  voice: "auto",
  quality: "auto",
  promptId: "p",
  prompt: "Show the shoe",
  quoteId: "q",
};
describe("submission recovery", () => {
  it("replays the original key and body after a timeout, even with a replaced quote", () => {
    const first = prepareSubmission(null, input, () => "original");
    const pending = submissionFailed(
      first,
      new ServiceError("NETWORK_ERROR", "Lost response", true),
    );
    const retry = prepareSubmission(
      pending,
      { ...input, quoteId: "replacement" },
      () => "duplicate",
    );
    expect(retry).toEqual(first);
  });
  it("retains uncertain server failures but clears an explicit admission rejection", () => {
    const first = prepareSubmission(null, input, () => "original");
    expect(submissionFailed(first, new Error("Invalid response"))).toEqual(
      first,
    );
    expect(
      submissionFailed(first, new ServiceError("STALE_QUOTE", "Expired")),
    ).toBeNull();
  });
  it("creates a fresh key after a confirmed request, allowing a terminal job retry", () => {
    const first = prepareSubmission(null, input, () => "original");
    const retry = prepareSubmission(null, input, () => "new");
    expect(retry.key).not.toBe(first.key);
    expect(retry.input).toEqual(first.input);
  });
});
