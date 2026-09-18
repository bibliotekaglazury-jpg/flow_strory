"use client";
import { useCreation } from "@/hooks/use-creation";
import { Shell } from "@/components/shell";
import { Hero } from "@/components/hero";
import { Workspace } from "./workspace";
import { Collections } from "./collections";
import { TryOnPanel } from "./try-on-panel";
export function CreateScreen() {
  const c = useCreation();
  return (
    <Shell>
      <Hero balance={c.credits?.balance ?? null} />
      <div className={`creation-band${c.tryOn.open ? "" : " creation-band-wide"}`}>
        <Workspace c={c} />
        {c.tryOn.open && <div className="creation-aside">
          <TryOnPanel
            c={c}
            onVideo={() => {
              void c.autoPlan();
              document
                .getElementById("create")
                ?.scrollIntoView({ behavior: "smooth" });
            }}
          />
        </div>}
      </div>
      <Collections
        templates={c.templates}
        history={c.history}
        onTemplate={c.selectTemplate}
        onOpen={(id) => {
          void c.open(id);
          document
            .getElementById("create")
            ?.scrollIntoView({ behavior: "smooth" });
        }}
        onRecreate={(generation) => {
          c.startRecreate(generation);
          document
            .getElementById("create")
            ?.scrollIntoView({ behavior: "smooth" });
        }}
      />
    </Shell>
  );
}
