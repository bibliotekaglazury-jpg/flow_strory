import type { NormalizedTemplateInput } from "../types";
"use client";
import React from "react";
import { Img, useCurrentFrame, useVideoConfig, staticFile } from "remotion";

interface KenBurnsProps {
  imageUrl?: string;
  duration?: number;
  scale?: number;
  translateX?: number;
  translateY?: number;
}

export const KenBurns: React.FC<KenBurnsProps> = ({
  imageUrl = staticFile("neutral-product.svg"),
  duration = 20,
  scale = 1.5,
  translateX = -50,
  translateY = -30,
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
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${1 + (scale - 1) * progress}) translate(${translateX * progress}px, ${translateY * progress}px)`,
        }}
      />
      
    </div>
  );
};

export default KenBurns;
