import { describe, expect, it } from "vitest";

import { deviceSpriteFor } from "./netPackets";
import type { SampledPacket } from "./types";

const pkt = (src: string, dst: string, kind: SampledPacket["kind"] = "benign"): SampledPacket => ({
  src_ip: src,
  dst_ip: dst,
  port: 443,
  protocol: "TCP",
  pkt_size: 512,
  freq: 100,
  ts_ms: 1000,
  kind,
  segment: "server",
  alert_ms: null,
});

const gateway = { x: 5, y: 5, color: "x" };
const posMap = {
  "10.0.2.10": { x: 100, y: 100, color: "x" },
  "10.0.2.20": { x: 200, y: 200, color: "x" },
};

describe("deviceSpriteFor", () => {
  it("routes a sprite from the src device to the dst device", () => {
    const s = deviceSpriteFor(pkt("10.0.2.10", "10.0.2.20"), posMap, gateway, 0);
    expect([s.x1, s.y1]).toEqual([100, 100]);
    expect([s.x2, s.y2]).toEqual([200, 200]);
  });

  it("falls back to the gateway for an unknown/attacker source", () => {
    const s = deviceSpriteFor(pkt("203.0.1.2", "10.0.2.20", "ddos"), posMap, gateway, 0);
    expect([s.x1, s.y1]).toEqual([5, 5]); // attacker src enters from the gateway
    expect([s.x2, s.y2]).toEqual([200, 200]);
    expect(s.color).toBe("var(--red)");
  });
});
