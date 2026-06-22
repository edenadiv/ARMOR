/* Per-device health for the Packet-Tracer view: a device is crit if its segment is
   quarantined or it's the dst of a non-benign packet, warn if its segment is under attack. */
import type { HostInfo, SampledPacket } from "./types";

export type HealthLevel = "ok" | "warn" | "crit";

export interface Health {
  level: HealthLevel;
  reason: string;
}

export function deviceHealth(
  host: HostInfo,
  segStatus: string,
  packets: SampledPacket[],
): Health {
  if (segStatus === "quarantined") return { level: "crit", reason: "segment quarantined" };
  if (packets.some((p) => p.dst_ip === host.ip && p.kind !== "benign")) {
    return { level: "crit", reason: "targeted by an attack" };
  }
  if (segStatus === "under_attack") return { level: "warn", reason: "segment under attack" };
  return { level: "ok", reason: "nominal" };
}

export const HEALTH_COLOR: Record<HealthLevel, string> = {
  ok: "var(--green)",
  warn: "var(--amber)",
  crit: "var(--red)",
};
