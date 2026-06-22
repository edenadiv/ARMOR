/* Device->device packet sprites for the Packet-Tracer view: route each sampled packet from
   its src device point to its dst device point. Reuses the sprite math (spriteAt/activeSprites)
   so positions stay a pure function of the playback clock. Unknown/external IPs fall back to a
   gateway anchor so an attack sprite always has somewhere to enter from. */
import type { Pt } from "./graph";
import { type Sprite, TRAVEL_MS } from "./packets";
import type { SampledPacket } from "./types";

const KIND_FILL: Record<string, string> = {
  benign: "var(--green)",
  ddos: "var(--red)",
  zero_day: "var(--violet)",
  port_scan: "var(--amber)",
  lateral: "var(--red)",
};

export function deviceSpriteFor(
  p: SampledPacket,
  posMap: Record<string, Pt>,
  gateway: Pt,
  id: number,
): Sprite {
  const src = posMap[p.src_ip] ?? gateway;
  const dst = posMap[p.dst_ip] ?? gateway;
  const arrive = p.alert_ms ?? p.ts_ms;
  const stagger = (id % 6) * 60;
  return {
    id,
    x1: src.x,
    y1: src.y,
    x2: dst.x,
    y2: dst.y,
    startMs: arrive - TRAVEL_MS - stagger,
    endMs: arrive - stagger,
    kind: p.kind,
    color: KIND_FILL[p.kind] ?? "var(--cyan)",
  };
}

export function buildDeviceSprites(
  packets: SampledPacket[],
  posMap: Record<string, Pt>,
  gateway: Pt,
): Sprite[] {
  return packets.map((p, i) => deviceSpriteFor(p, posMap, gateway, i));
}
