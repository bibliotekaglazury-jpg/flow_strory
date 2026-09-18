import { describe, it, expect } from "vitest";
import { createMockServices } from "../services/mock";
const creative = {
  inputAssets: {},
  productUrl: "https://example.com/product",
  templateId: "ugc_review",
  brief: "A practical everyday product",
  duration: 15 as const,
  aspectRatio: "9:16" as const,
};
describe("mock contract and credit lifecycle", () => {
  it("deduplicates a submission and releases the reservation on cancellation", async () => {
    const s = createMockServices();
    const prompt = await s.prompts.generate(creative);
    const quote = await s.credits.get({
      ...creative,
      promptId: prompt.promptId,
      model: "auto",
      voice: "auto",
    });
    const input = {
      ...creative,
      model: "auto",
      voice: "auto",
      promptId: prompt.promptId,
      prompt: prompt.prompt,
      quoteId: quote.quote!.id,
    };
    const a = await s.generations.create(input, "one");
    const b = await s.generations.create(input, "one");
    expect(a.generation.id).toBe(b.generation.id);
    expect((await s.credits.get()).balance).toBe(
      quote.balance - quote.quote!.creditsEstimated,
    );
    await s.generations.cancel(a.generation.id);
    await s.generations.cancel(a.generation.id);
    expect((await s.credits.get()).balance).toBe(quote.balance);
  });
  it("rejects a quote reused for different settings", async () => {
    const s = createMockServices();
    const p = await s.prompts.generate(creative);
    const q = await s.credits.get({
      ...creative,
      promptId: p.promptId,
      model: "auto",
      voice: "auto",
    });
    await expect(
      s.generations.create(
        {
          ...creative,
          duration: 30,
          model: "auto",
          voice: "auto",
          promptId: p.promptId,
          prompt: p.prompt,
          quoteId: q.quote!.id,
        },
        "bad",
      ),
    ).rejects.toThrow();
  });
  it("accepts text-only offers and never overwrites manual prompt text", async () => {
    const s = createMockServices();
    await expect(
      s.prompts.generate({ ...creative, productUrl: undefined }),
    ).resolves.toHaveProperty("promptId");
    const p = await s.prompts.generate(creative);
    const q = await s.credits.get({
      ...creative,
      promptId: p.promptId,
      model: "auto",
      voice: "auto",
    });
    const job = await s.generations.create(
      {
        ...creative,
        model: "auto",
        voice: "auto",
        promptId: p.promptId,
        prompt: "My reviewed production direction",
        quoteId: q.quote!.id,
      },
      "edited",
    );
    expect(job.generation.prompt).toBe("My reviewed production direction");
  });
});
