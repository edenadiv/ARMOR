import { describe, expect, it } from "vitest";

import { layoutSegment, segmentBoxes } from "./netLayout";
import type { HostInfo } from "./types";

const hosts = (n: number): HostInfo[] =>
  Array.from({ length: n }, (_, i) => ({
    hostname: `h${i}`,
    ip: `10.0.0.${i}`,
    segment: "server",
    role: "x",
  }));

describe("segmentBoxes", () => {
  it("gives a disjoint box per segment", () => {
    const boxes = segmentBoxes(["public-facing", "server", "internal", "sec-mon"]);
    expect(Object.keys(boxes)).toHaveLength(4);
    const origins = new Set(Object.values(boxes).map((b) => `${b.x},${b.y}`));
    expect(origins.size).toBe(4);
  });
});

describe("layoutSegment", () => {
  it("gives a unique point per host inside the box", () => {
    const box = { x: 0, y: 0, w: 400, h: 300 };
    const pos = layoutSegment(hosts(5), box);
    expect(Object.keys(pos)).toHaveLength(5);
    for (const p of Object.values(pos)) {
      expect(p.x).toBeGreaterThanOrEqual(box.x);
      expect(p.x).toBeLessThanOrEqual(box.x + box.w);
      expect(p.y).toBeGreaterThanOrEqual(box.y);
      expect(p.y).toBeLessThanOrEqual(box.y + box.h);
    }
    const pts = new Set(Object.values(pos).map((p) => `${p.x},${p.y}`));
    expect(pts.size).toBe(5);
  });

  it("returns nothing for an empty host list", () => {
    expect(layoutSegment([], { x: 0, y: 0, w: 100, h: 100 })).toEqual({});
  });
});
