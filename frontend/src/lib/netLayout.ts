/* Layout for the Packet-Tracer network map: tile the canvas into one box per segment, and
   place a segment's named devices on a grid inside its box. Pure geometry — no React. */
import type { Pt, ViewBox } from "./graph";
import type { HostInfo } from "./types";

/** The full network-map SVG canvas. */
export const NETWORK_CANVAS: ViewBox = { x: 0, y: 0, w: 1000, h: 640 };

const SEG_ORDER = ["public-facing", "server", "internal", "sec-mon"];

function ordered(segments: string[]): string[] {
  const known = SEG_ORDER.filter((s) => segments.includes(s));
  const rest = segments.filter((s) => !SEG_ORDER.includes(s));
  return [...known, ...rest];
}

/** One disjoint box per segment, tiled across the canvas (2 columns). */
export function segmentBoxes(segments: string[], canvas: ViewBox = NETWORK_CANVAS): Record<string, ViewBox> {
  const segs = ordered(segments);
  const n = Math.max(1, segs.length);
  const cols = n <= 1 ? 1 : 2;
  const rows = Math.ceil(n / cols);
  const gap = 30;
  const cw = (canvas.w - gap * (cols + 1)) / cols;
  const ch = (canvas.h - gap * (rows + 1)) / rows;
  const out: Record<string, ViewBox> = {};
  segs.forEach((s, i) => {
    const c = i % cols;
    const r = Math.floor(i / cols);
    out[s] = {
      x: canvas.x + gap + c * (cw + gap),
      y: canvas.y + gap + r * (ch + gap),
      w: cw,
      h: ch,
    };
  });
  return out;
}

/** Place each host on a grid inside `box`; returns ip -> point. */
export function layoutSegment(hosts: HostInfo[], box: ViewBox): Record<string, Pt> {
  const out: Record<string, Pt> = {};
  const n = hosts.length;
  if (!n) return out;
  const cols = Math.ceil(Math.sqrt(n));
  const rows = Math.ceil(n / cols);
  const padX = box.w * 0.14;
  const padY = box.h * 0.24;
  const cellW = (box.w - 2 * padX) / cols;
  const cellH = (box.h - 2 * padY) / rows;
  hosts.forEach((h, i) => {
    const c = i % cols;
    const r = Math.floor(i / cols);
    out[h.ip] = {
      x: box.x + padX + cellW * (c + 0.5),
      y: box.y + padY + cellH * (r + 0.5),
      color: "var(--primary)",
    };
  });
  return out;
}

/** A gateway anchor for a segment box — where unknown/external (attacker) packets enter. */
export function gatewayPoint(box: ViewBox): Pt {
  return { x: box.x + box.w / 2, y: box.y + box.h * 0.06, color: "var(--red)" };
}
