import { Suspense } from "react";
import { Shell } from "@/components/shell";
import { SubtitleStudio } from "@/features/subtitles/subtitle-studio";

export default function SubtitlesPage() {
  return (
    <Shell>
      {/* The studio reads ?project= to reopen a saved project after a reload. */}
      <Suspense fallback={null}>
        <SubtitleStudio />
      </Suspense>
    </Shell>
  );
}
