"use client";

import { useEffect, useMemo, useState } from "react";
import { fluidLoaderOptions } from "@/services/fluid-loader-options";

function fluidDocument(compact: boolean) {
  const options = JSON.stringify(fluidLoaderOptions(compact)).replaceAll(
    "<",
    "\\u003c",
  );
  return `<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body,canvas{width:100%;height:100%;margin:0;overflow:hidden;background:#081218}
canvas{display:block}
</style></head><body><canvas></canvas><script type="module">
import WebGLFluid from '/vendor/webgl-fluid-0.4.0.mjs';
WebGLFluid(document.querySelector('canvas'), ${options});
</script></body></html>`;
}

export function FluidLoader() {
  const [motionAllowed, setMotionAllowed] = useState(false);
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const narrow = window.matchMedia("(max-width: 767px)");
    const update = () => {
      setMotionAllowed(!reduced.matches);
      setCompact(narrow.matches);
    };
    update();
    reduced.addEventListener("change", update);
    narrow.addEventListener("change", update);
    return () => {
      reduced.removeEventListener("change", update);
      narrow.removeEventListener("change", update);
    };
  }, []);

  const srcDoc = useMemo(() => fluidDocument(compact), [compact]);
  if (!motionAllowed)
    return <span className="fluid-loader-static" aria-hidden="true" />;
  return (
    <iframe
      className="fluid-loader-frame"
      srcDoc={srcDoc}
      sandbox="allow-scripts allow-same-origin"
      tabIndex={-1}
      aria-hidden="true"
      title=""
    />
  );
}
