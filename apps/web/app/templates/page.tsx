import { Suspense } from "react";
import { TemplateCatalog } from "@/features/templates/catalog";
export default function TemplatesPage() {
  return (
    <Suspense fallback={<p>Loading templates…</p>}>
      <TemplateCatalog />
    </Suspense>
  );
}
