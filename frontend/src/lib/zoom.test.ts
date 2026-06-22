import { describe, expect, it } from "vitest";

import { lerpViewBox } from "./zoom";

const A = { x: 0, y: 0, w: 100, h: 100 };
const B = { x: 100, y: 50, w: 200, h: 80 };

describe("lerpViewBox", () => {
  it("returns the start box at p=0 and the end box at p=1", () => {
    expect(lerpViewBox(A, B, 0)).toEqual(A);
    expect(lerpViewBox(A, B, 1)).toEqual(B);
  });

  it("interpolates strictly between at p=0.5", () => {
    const m = lerpViewBox(A, B, 0.5);
    expect(m.x).toBe(50);
    expect(m.w).toBe(150);
  });

  it("clamps p outside [0,1]", () => {
    expect(lerpViewBox(A, B, -1)).toEqual(A);
    expect(lerpViewBox(A, B, 2)).toEqual(B);
  });
});
