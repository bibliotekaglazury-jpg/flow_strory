import { afterEach, expect, it, vi } from "vitest";
import type { Generation, Services } from "@ugc/contracts";
import { pollGeneration } from "../services/poll-generation";
afterEach(() => vi.useRealTimers());
it("honors backoff and stops after a terminal response", async () => {
  vi.useFakeTimers();
  const get = vi
    .fn()
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({
      generation: { id: "g", status: "generating" },
      pollAfterMs: 900,
    })
    .mockResolvedValueOnce({
      generation: { id: "g", status: "completed" },
      pollAfterMs: null,
    });
  const updates: Generation[] = [];
  const stop = pollGeneration(
    { get } as unknown as Services["generations"],
    "g",
    async (job) => {
      updates.push(job);
    },
    vi.fn(),
  );
  await vi.advanceTimersByTimeAsync(700);
  expect(get).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(1000);
  expect(get).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(900);
  expect(updates.map((x) => x.status)).toEqual(["generating", "completed"]);
  await vi.advanceTimersByTimeAsync(10000);
  expect(get).toHaveBeenCalledTimes(3);
  stop();
});
it("does not reschedule when selection changes during refresh", async () => {
  vi.useFakeTimers();
  const get = vi
    .fn()
    .mockResolvedValue({
      generation: { id: "g", status: "generating" },
      pollAfterMs: 800,
    });
  let finish!: () => void;
  const refresh = new Promise<void>((resolve) => {
    finish = resolve;
  });
  const stop = pollGeneration(
    { get } as unknown as Services["generations"],
    "g",
    () => refresh,
    vi.fn(),
  );
  await vi.advanceTimersByTimeAsync(700);
  stop();
  finish();
  await vi.advanceTimersByTimeAsync(10000);
  expect(get).toHaveBeenCalledTimes(1);
});
