import type { NormalizedTemplateInput } from "../types";
"use client";
import React from "react";
import { Img, useCurrentFrame, useVideoConfig, staticFile } from "remotion";

interface ParallaxPanProps {
  imageUrl?: string;
  duration?: number;
  direction?: "left-right" | "right-left" | "top-bottom" | "bottom-top";
  scale?: number;
}

export const ParallaxPan: React.FC<ParallaxPanProps> = ({
  imageUrl = staticFile("neutral-product.svg"),
  duration = 15,
  direction = "left-right",
  scale = 1.2,
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
        alt="Parallax Pan"
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate${direction.startsWith("top") || direction.startsWith("bottom") ? "Y" : "X"}(${(direction.startsWith("right") || direction.startsWith("bottom") ? 1-progress : progress) * -12}%)`,
        }}
      />
      
    </div>
  );
};

export default ParallaxPan;
