import { describe, expect, it } from "vitest";
import { fluidLoaderOptions } from "../services/fluid-loader-options";

describe("fluidLoaderOptions", () => {
  it("keeps gentle splats running for an indefinite generation", () => {
    expect(fluidLoaderOptions(false)).toMatchObject({
      AUTO: true,
      IMMEDIATE: true,
      INTERVAL: 6500,
      DENSITY_DISSIPATION: 0.15,
      VELOCITY_DISSIPATION: 0.08,
      SPLAT_FORCE: 1100,
      SPLAT_COUNT: 2,
      COLOR_UPDATE_SPEED: 2,
    });
  });

  it("reduces GPU work on small screens", () => {
    expect(fluidLoaderOptions(true)).toMatchObject({
      SIM_RESOLUTION: 64,
      DYE_RESOLUTION: 256,
      BLOOM: false,
      SUNRAYS: false,
    });
  });
});
