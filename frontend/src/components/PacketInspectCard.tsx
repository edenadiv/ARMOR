/* Click-a-packet inspection card for the Packet-Tracer view. */
import type { CSSProperties } from "react";

import { hostFor, labelFor } from "../lib/inspect";
import type { HostInfo, SampledPacket } from "../lib/types";

const KIND_COLOR: Record<string, string> = {
  benign: "var(--green)",
  ddos: "var(--red)",
  zero_day: "var(--violet)",
  port_scan: "var(--amber)",
  lateral: "var(--red)",
};

export function PacketInspectCard({
  packet,
  hosts,
  onClose,
}: {
  packet: SampledPacket;
  hosts: HostInfo[];
  onClose: () => void;
}) {
  const dstHost = hostFor(packet.dst_ip, hosts);
  const service = dstHost?.services?.find((s) => s.port === packet.port);
  const color = KIND_COLOR[packet.kind] ?? "var(--cyan)";

  return (
    <div style={CARD}>
      <div style={HEAD}>
        <span style={{ color, fontWeight: 700, letterSpacing: 0.5 }}>
          {packet.kind.replace("_", " ").toUpperCase()} PACKET
        </span>
        <button onClick={onClose} style={X} aria-label="close">
          ×
        </button>
      </div>
      <Row k="flow">
        {labelFor(packet.src_ip, hosts)} → {labelFor(packet.dst_ip, hosts)}
      </Row>
      <Row k="addr">
        <span className="mono" style={{ fontSize: 10 }}>
          {packet.src_ip} → {packet.dst_ip}
        </span>
      </Row>
      <Row k="service">
        port {packet.port}
        {service ? ` · ${service.name}` : ""} / {packet.protocol}
      </Row>
      <Row k="size">
        {packet.pkt_size} B · ~{Math.round(packet.freq)} pps
      </Row>
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div style={ROW}>
      <span style={KSTY}>{k}</span>
      <span>{children}</span>
    </div>
  );
}

const CARD: CSSProperties = {
  position: "absolute",
  bottom: 16,
  left: 16,
  width: 280,
  padding: "12px 14px",
  borderRadius: 12,
  background: "rgba(10,16,26,0.94)",
  border: "1px solid var(--line)",
  boxShadow: "0 8px 30px rgba(0,0,0,0.5)",
  zIndex: 3,
};
const HEAD: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 8,
  fontSize: 12,
};
const ROW: CSSProperties = { display: "flex", gap: 10, fontSize: 12, padding: "3px 0" };
const KSTY: CSSProperties = { color: "var(--faint)", width: 56, flexShrink: 0 };
const X: CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--faint)",
  fontSize: 18,
  cursor: "pointer",
  lineHeight: 1,
};
