import type { Generation, Services } from "@ugc/contracts";
export function pollGeneration(
  service: Services["generations"],
  id: string,
  onGeneration: (job: Generation) => Promise<void>,
  onError: () => void,
) {
  let stopped = false,
    failures = 0;
  let timer: ReturnType<typeof setTimeout>;
  const poll = async () => {
    try {
      const result = await service.get(id);
      if (stopped) return;
      await onGeneration(result.generation);
      failures = 0;
      if (!stopped && result.pollAfterMs !== null)
        timer = setTimeout(poll, Math.max(500, result.pollAfterMs));
    } catch {
      if (!stopped) {
        onError();
        timer = setTimeout(poll, Math.min(1000 * 2 ** failures++, 15000));
      }
    }
  };
  timer = setTimeout(poll, 700);
  return () => {
    stopped = true;
    clearTimeout(timer);
  };
}
