"use client";
import { useCallback, useEffect, useState } from "react";
import type { Generation, VideoTemplate } from "@ugc/contracts";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/shell";
import { Collections } from "@/features/create/collections";
import { Preview } from "@/features/create/preview";
import { getServices } from "@/services";
import { pollGeneration } from "@/services/poll-generation";
export default function Library() {
  const router = useRouter();
  const [history, setHistory] = useState<Generation[]>([]),
    [templates, setTemplates] = useState<VideoTemplate[]>([]),
    [job, setJob] = useState<Generation | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setHistory((await getServices().generations.list()).generations);
  }, []);
  useEffect(() => {
    let stopped = false;
    const s = getServices();
    void Promise.all([s.generations.list(), s.templates.list()])
      .then(([h, t]) => {
        if (!stopped) {
          setHistory(h.generations);
          setTemplates(t.templates);
        }
      })
      .catch((e) => {
        if (!stopped) setError(e.message);
      })
      .finally(() => {
        if (!stopped) setLoading(false);
      });
    return () => {
      stopped = true;
    };
  }, []);
  const jobId = job?.id,
    jobStatus = job?.status;
  useEffect(() => {
    if (!jobId || !jobStatus || !["queued", "generating"].includes(jobStatus))
      return;
    return pollGeneration(
      getServices().generations,
      jobId,
      async (generation) => {
        setJob(generation);
        setError("");
        await refresh();
      },
      () =>
        setError(
          "Connection interrupted. Reconnecting to your saved generation…",
        ),
    );
  }, [jobId, jobStatus, refresh]);
  async function open(id: string) {
    setError("");
    try {
      setJob((await getServices().generations.get(id)).generation);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function remove(ids: string[]) {
    const results = await Promise.allSettled(
      ids.map((id) => getServices().generations.remove(id)),
    );
    await refresh();
    if (job && ids.includes(job.id)) setJob(null);
    if (results.some((r) => r.status === "rejected")) throw new Error("Some deletes failed");
  }
  return (
    <Shell>
      <section className="utility-page" id="create">
        <h1>Library</h1>
        {error && <p role="alert">{error}</p>}
        {loading ? (
          <p role="status">Loading your creations…</p>
        ) : (
          <Collections
            templates={[]}
            history={history}
            onTemplate={() => {}}
            onOpen={(id) => {
              void open(id);
            }}
            onRecreate={(generation) =>
              router.push(`/?recreate=${generation.id}#create`)
            }
            onDelete={remove}
          />
        )}
        {job && (
          <Preview job={job} templates={templates} />
        )}
      </section>
    </Shell>
  );
}
