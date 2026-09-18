import { SharedSubtitleVideo } from "@/features/subtitles/shared-video";

export default async function SharePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <SharedSubtitleVideo token={token} />;
}
