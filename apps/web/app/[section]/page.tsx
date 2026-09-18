import { notFound } from "next/navigation";
import Link from "next/link";
import { Shell } from "@/components/shell";
const sections: Record<string, string> = {
  "brand-kit": "Brand Kit",
  analytics: "Analytics",
  settings: "Settings",
};
export default async function Section({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  const title = sections[section];
  if (!title) notFound();
  return (
    <Shell>
      <section className="utility-page" id="create">
        <p className="eyebrow">YOUR WORKSPACE</p>
        <h1>{title}</h1>
        <p>This section is outside the current creation MVP.</p>
        <Link className="button button-primary" href="/">
          Back to Create
        </Link>
      </section>
    </Shell>
  );
}
