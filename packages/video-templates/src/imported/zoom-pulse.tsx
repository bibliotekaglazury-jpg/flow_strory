import type { NormalizedTemplateInput } from "../types";
"use client";
import React from "react";
import { Img, useCurrentFrame, useVideoConfig, staticFile } from "remotion";

interface ZoomPulseProps {
  imageUrl?: string;
  duration?: number;
  minScale?: number;
  maxScale?: number;
}

export const ZoomPulse: React.FC<ZoomPulseProps> = ({
  imageUrl = staticFile("neutral-product.svg"),
  duration = 4,
  minScale = 1,
  maxScale = 1.1,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = Math.min(1, frame / (fps * duration));
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "black",
        overflow: "hidden",
      }}
    >
      <Img
        src={imageUrl}
        width={800}
        height={450}
        alt="Zoom Pulse"
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${minScale + (maxScale-minScale) * (1-Math.cos(frame / fps / duration * Math.PI * 2))/2})`,
        }}
      />
      
    </div>
  );
};

export default ZoomPulse;
