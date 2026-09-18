"use client";
import { useEffect, useState } from "react";
import type { BillingSummary } from "@ugc/contracts";
import { Shell } from "@/components/shell";
import { Button } from "@ugc/ui";
import { getServices } from "@/services";
export default function Billing() {
  const [summary, setSummary] = useState<BillingSummary | null>(null),
    [balance, setBalance] = useState<number | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    const s = getServices();
    void Promise.all([s.billing.summary(), s.credits.get()])
      .then(([b, c]) => {
        setSummary(b);
        setBalance(c.balance);
      })
      .catch((e) => setError(e.message));
  }, []);
  async function manage(price?: string) {
    setBusy(true);
    try {
      const s = getServices();
      const url = price
        ? (await s.billing.checkout(price)).checkoutUrl
        : (await s.billing.portal()).portalUrl;
      if (new URL(url).protocol !== "https:")
        throw new Error("Invalid billing redirect.");
      window.location.assign(url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell>
      <section className="utility-page" id="create">
        <h1>Billing</h1>
        {summary ? (
          <>
            <dl className="billing-details">
              <div>
                <dt>Current plan</dt>
                <dd>{summary.plan}</dd>
              </div>
              <div>
                <dt>Credits remaining</dt>
                <dd>{balance}</dd>
              </div>
              <div>
                <dt>Renewal date</dt>
                <dd>
                  {summary.renewalDate
                    ? new Date(summary.renewalDate).toLocaleDateString()
                    : "—"}
                </dd>
              </div>
            </dl>
            <Button
              disabled={busy || summary.status === "simulation"}
              onClick={() => manage()}
            >
              Manage subscription
            </Button>
            {summary.prices.map((p) => (
              <Button key={p.id} disabled={busy} onClick={() => manage(p.id)}>
                {p.label}
              </Button>
            ))}
            {summary.status === "simulation" && (
              <p>Demo credits have no monetary value. Payments are disabled.</p>
            )}
          </>
        ) : (
          <p>Loading billing details…</p>
        )}
        {error && <p role="alert">{error}</p>}
      </section>
    </Shell>
  );
}
