import { Coins } from "lucide-react";
import { HeroVideoGallery } from "./hero-video-gallery";

export function Hero({
  balance,
}: {
  balance: number | null;
}) {
  return (
    <header className="hero">
      <div className="hero-utilities">
        <span className="credit-pill">
          <Coins size={16} />
          {balance === null
            ? "Loading credits…"
            : `${balance.toLocaleString("en-US")} credits`}
        </span>
        <span className="utility-avatar" aria-label="Workspace account">
          F
        </span>
      </div>
      <div className="hero-copy">
        <p className="eyebrow">VIDEO FOR YOUR NEXT BIG IDEA</p>
        <h1>
          Your product.
          <br />A <em>real</em> story.
        </h1>
        <p className="hero-subtitle">
          Create scroll-stopping UGC videos in minutes.
          <br />
          Your product. Your voice. Your story.
        </p>
      </div>
      <HeroVideoGallery />
      <div className="hero-lettering" aria-label="Make it real!" role="img" />
    </header>
  );
}
