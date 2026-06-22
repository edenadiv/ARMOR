/* Resolve a packet IP to its named device (for the packet-inspection card). */
import type { HostInfo } from "./types";

export function hostFor(ip: string, hosts: HostInfo[]): HostInfo | null {
  return hosts.find((h) => h.ip === ip) ?? null;
}

export function isExternal(ip: string): boolean {
  return ip.startsWith("203.0.") || ip === "198.51.100.7" || ip === "192.0.2.66";
}

/** A human label for an IP: the hostname if known, "internet / attacker" if a signature, else the IP. */
export function labelFor(ip: string, hosts: HostInfo[]): string {
  const h = hostFor(ip, hosts);
  if (h) return h.hostname;
  if (isExternal(ip)) return "internet / attacker";
  return ip;
}
