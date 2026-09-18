"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

type HeroVideo = {
  src: string;
  poster: string;
  label: string;
};

const videos: HeroVideo[] = [
  {
    src: "/media/create-preview.mp4",
    poster: "/media/create-preview.webp",
    label: "Product story",
  },
  {
    src: "/media/showcase/product-demo.mp4",
    poster: "/media/showcase/product-demo.jpg",
    label: "Product demo",
  },
  {
    src: "/media/showcase/product-unboxing.mp4",
    poster: "/media/showcase/product-unboxing.jpg",
    label: "Unboxing",
  },
  {
    src: "/media/showcase/premium-ugc.mp4",
    poster: "/media/showcase/premium-ugc.jpg",
    label: "Premium UGC",
  },
  ...Array.from({ length: 12 }, (_, index) => {
    const number = String(index + 1).padStart(2, "0");
    return {
      src: `/media/showcase/pika/pika-${number}.mp4`,
      poster: `/media/showcase/pika/pika-${number}.jpg`,
      label: `Creative story ${index + 1}`,
    };
  }),
];

const visibleCount = 4;

export function HeroVideoGallery() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const [sliding, setSliding] = useState(false);

  const moveBack = () =>
    setActive((current) => (current - 1 + videos.length) % videos.length);

  const startNextSlide = () => {
    if (!sliding) setSliding(true);
  };

  const finishNextSlide = () => {
    setActive((current) => (current + 1) % videos.length);
    setSliding(false);
  };

  useEffect(() => {
    if (paused || sliding) return;
    const timer = window.setTimeout(() => setSliding(true), 5200);
    return () => window.clearTimeout(timer);
  }, [active, paused, sliding]);

  const visible = Array.from(
    { length: visibleCount + 1 },
    (_, offset) => videos[(active + offset) % videos.length],
  );

  return (
    <section
      className="hero-video-gallery"
      aria-label="Video inspiration"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget))
          setPaused(false);
      }}
    >
      <div className="hero-video-stack">
        <div
          className="hero-video-track"
          data-sliding={sliding}
          onTransitionEnd={(event) => {
            if (
              event.target === event.currentTarget &&
              event.propertyName === "transform" &&
              sliding
            ) {
              finishNextSlide();
            }
          }}
        >
          {visible.map((video, slot) => (
            <article
              className="hero-video-card"
              data-slot={slot}
              key={`${active}-${video.src}`}
            >
              <span>{video.label}</span>
              <video
                src={video.src}
                poster={video.poster}
                aria-label={video.label}
                autoPlay
                muted
                loop
                playsInline
                preload="metadata"
              />
            </article>
          ))}
        </div>
      </div>
      <div className="hero-gallery-controls">
        <span>
          {String(active + 1).padStart(2, "0")}–
          {String(((active + visibleCount - 1) % videos.length) + 1).padStart(
            2,
            "0",
          )}{" "}
          of {videos.length}
        </span>
        <button
          type="button"
          aria-label="Previous videos"
          onClick={moveBack}
          disabled={sliding}
        >
          <ChevronLeft size={18} />
        </button>
        <button
          type="button"
          aria-label="Next videos"
          onClick={startNextSlide}
          disabled={sliding}
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </section>
  );
}
