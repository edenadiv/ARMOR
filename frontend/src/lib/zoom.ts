/* Camera tween for the Packet-Tracer view: interpolate one SVG viewBox toward another so
   "zoom into a node" is a smooth animated crop (paired with viewBoxStr from graph.ts). */
import type { ViewBox } from "./graph";

export function lerpViewBox(from: ViewBox, to: ViewBox, p: number): ViewBox {
  const c = Math.min(1, Math.max(0, p));
  return {
    x: from.x + (to.x - from.x) * c,
    y: from.y + (to.y - from.y) * c,
    w: from.w + (to.w - from.w) * c,
    h: from.h + (to.h - from.h) * c,
  };
}
