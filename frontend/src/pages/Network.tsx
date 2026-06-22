/* Packet-Tracer network view: the 4 segments as glowing boxes; click one to animate the
   SVG viewBox into it (reusing the camera/lerp + sprite math) and watch packets travel
   device->device between named hosts. Click a packet to inspect it, a device for its detail,
   and watch the anti-poisoning baseline hold flat while traffic spikes. Live + replay. */
import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";

import { PacketInspectCard } from "../components/PacketInspectCard";
import { baselineSeriesFromEvents, baselineSparkline } from "../lib/baseline";
import { type Pt, type ViewBox, viewBoxStr } from "../lib/graph";
import { HEALTH_COLOR, deviceHealth } from "../lib/health";
import { NETWORK_CANVAS, gatewayPoint, layoutSegment, segmentBoxes } from "../lib/netLayout";
import { buildDeviceSprites } from "../lib/netPackets";
import { activeSprites } from "../lib/packets";
import { useReplay } from "../lib/replayContext";
import type { HostInfo, SampledPacket } from "../lib/types";
import { lerpViewBox } from "../lib/zoom";

const STATUS_COLOR: Record<string, string> = {
  normal: "var(--green)",
  under_attack: "var(--red)",
  mitigating: "var(--cyan)",
  quarantined: "var(--violet)",
};
const TRAIL = 14;

const easeInOut = (p: number) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2);
const isAttacker = (ip: string) =>
  ip.startsWith("203.0.") || ip === "198.51.100.7" || ip === "192.0.2.66";

function ipHash(ip: string): number {
  const last = Number(ip.split(".")[3]);
  if (!Number.isNaN(last)) return last;
  let h = 0;
  for (const c of ip) h = (h * 31 + c.charCodeAt(0)) | 0;
  return Math.abs(h);
}

/** Resolve every packet endpoint to a device point: named hosts map directly; internal
    synthetic client IPs map to a host by hash; attacker/external IPs go to the gateway. */
function resolvePosMap(
  packets: SampledPacket[],
  base: Record<string, Pt>,
  hosts: HostInfo[],
): Record<string, Pt> {
  const map: Record<string, Pt> = { ...base };
  const ips = hosts.map((h) => h.ip);
  for (const p of packets) {
    for (const ip of [p.src_ip, p.dst_ip]) {
      if (map[ip] || isAttacker(ip) || ips.length === 0) continue;
      map[ip] = base[ips[ipHash(ip) % ips.length]];
    }
  }
  return map;
}

export function Network() {
  const { data, t, derived, live } = useReplay();
  const segments = data.topology.segments ?? [];
  const hosts = data.topology.hosts ?? [];
  const adjacency = data.topology.adjacency ?? {};
  const packets = data.replay.packets ?? [];

  const boxes = useMemo(() => segmentBoxes(segments), [segments]);
  const [selected, setSelected] = useState<string | null>(null);
  const [pkt, setPkt] = useState<SampledPacket | null>(null);
  const [dev, setDev] = useState<HostInfo | null>(null);
  const active = selected && boxes[selected] ? selected : null;

  // Clear pop-overs whenever the zoom target changes.
  useEffect(() => {
    setPkt(null);
    setDev(null);
  }, [active]);

  // Animate the viewBox toward the selected segment box (or back to the full canvas).
  const [vb, setVb] = useState<ViewBox>(NETWORK_CANVAS);
  const vbRef = useRef(vb);
  vbRef.current = vb;
  useEffect(() => {
    const target = active ? boxes[active] : NETWORK_CANVAS;
    const from = vbRef.current;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / 480);
      setVb(lerpViewBox(from, target, easeInOut(p)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, boxes]);

  const zoom = useMemo(() => {
    if (!active) return null;
    const box = boxes[active];
    const segHosts = hosts.filter((h) => h.segment === active);
    const base = layoutSegment(segHosts, box);
    const segPackets = packets.filter((p) => p.segment === active);
    const posMap = resolvePosMap(segPackets, base, segHosts);
    const gateway = gatewayPoint(box);
    return {
      box,
      segHosts,
      base,
      segPackets,
      status: derived.segments[active]?.status ?? "normal",
      sprites: buildDeviceSprites(segPackets, posMap, gateway),
    };
  }, [active, boxes, hosts, packets, derived]);

  const centers = useMemo(() => {
    const c: Record<string, Pt> = {};
    for (const [seg, b] of Object.entries(boxes)) {
      c[seg] = { x: b.x + b.w / 2, y: b.y + b.h / 2, color: "var(--primary)" };
    }
    return c;
  }, [boxes]);

  const sprites = zoom ? activeSprites(zoom.sprites, t) : [];

  // Anti-poisoning baseline series for the readout: continuous live frames if present, else
  // derived from the recorded baseline_update events (replay).
  const series = useMemo(() => {
    if (!active) return [];
    const liveSeries = live.baselines[active];
    if (liveSeries && liveSeries.length > 1) return liveSeries.slice(-90);
    return baselineSeriesFromEvents(data.replay.events, active).slice(-90);
  }, [active, live.baselines, data.replay.events]);
  const spark = baselineSparkline(series, 180, 46);
  const latest = series[series.length - 1];

  return (
    <div className="network-view" style={WRAP}>
      {active && (
        <button className="btn net-back" style={BACK} onClick={() => setSelected(null)}>
          ◀ All segments
        </button>
      )}
      <svg
        viewBox={viewBoxStr(vb)}
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        style={{ display: "block" }}
      >
        {Object.entries(adjacency).flatMap(([a, ns]) =>
          (ns as string[]).map((b) =>
            a < b && centers[a] && centers[b] ? (
              <line
                key={`${a}-${b}`}
                x1={centers[a].x}
                y1={centers[a].y}
                x2={centers[b].x}
                y2={centers[b].y}
                stroke="var(--line)"
                strokeWidth={1.5}
                strokeDasharray="5 6"
                opacity={active ? 0.1 : 0.4}
              />
            ) : null,
          ),
        )}

        {segments.map((seg) => {
          const b = boxes[seg];
          if (!b) return null;
          const status = derived.segments[seg]?.status ?? "normal";
          const color = STATUS_COLOR[status] ?? "var(--green)";
          const count = hosts.filter((h) => h.segment === seg).length;
          const dim = active && active !== seg;
          return (
            <g
              key={seg}
              opacity={dim ? 0.25 : 1}
              onClick={() => setSelected(seg)}
              style={{ cursor: "pointer" }}
            >
              <rect
                x={b.x}
                y={b.y}
                width={b.w}
                height={b.h}
                rx={16}
                fill="rgba(12,18,28,0.72)"
                stroke={color}
                strokeWidth={status === "normal" ? 1.5 : 2.5}
                style={{ filter: `drop-shadow(0 0 ${status === "normal" ? 4 : 12}px ${color})` }}
              />
              <text x={b.x + 18} y={b.y + 30} fill={color} fontSize={18} fontWeight={700}>
                {seg.toUpperCase()}
              </text>
              <text x={b.x + 18} y={b.y + 50} fill="var(--dim)" fontSize={12}>
                {count} devices · {status.replace("_", " ")}
              </text>
            </g>
          );
        })}

        {zoom &&
          zoom.segHosts.map((h) => {
            const p = zoom.base[h.ip];
            if (!p) return null;
            const ring = HEALTH_COLOR[deviceHealth(h, zoom.status, zoom.segPackets).level];
            return (
              <g key={h.ip} style={{ cursor: "pointer" }} onClick={() => setDev(h)}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={10}
                  fill="rgba(10,16,26,0.95)"
                  stroke={ring}
                  strokeWidth={2.5}
                  style={{ filter: `drop-shadow(0 0 8px ${ring})` }}
                />
                <text x={p.x} y={p.y + 26} fill="var(--text)" fontSize={11} textAnchor="middle">
                  {h.hostname}
                </text>
                <text x={p.x} y={p.y - 16} fill="var(--faint)" fontSize={9} textAnchor="middle">
                  {h.role}
                </text>
              </g>
            );
          })}

        {zoom &&
          sprites.map(({ s, pos }) => {
            const dx = s.x2 - s.x1;
            const dy = s.y2 - s.y1;
            const len = Math.hypot(dx, dy) || 1;
            return (
              <g
                key={s.id}
                opacity={pos.opacity}
                style={{ cursor: "pointer" }}
                onClick={() => zoom.segPackets[s.id] && setPkt(zoom.segPackets[s.id])}
              >
                <line
                  x1={pos.x - (dx / len) * TRAIL}
                  y1={pos.y - (dy / len) * TRAIL}
                  x2={pos.x}
                  y2={pos.y}
                  stroke={s.color}
                  strokeWidth={2}
                  strokeLinecap="round"
                  opacity={0.5}
                />
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={4}
                  fill={s.color}
                  style={{ filter: `drop-shadow(0 0 5px ${s.color})` }}
                />
              </g>
            );
          })}
      </svg>

      {!active && <div style={HINT}>▶ click a segment to zoom into its devices</div>}

      {/* anti-poisoning baseline readout */}
      {active && spark.hasData && latest && (
        <div style={READOUT}>
          <div style={{ fontSize: 11, color: "var(--faint)", marginBottom: 4 }}>
            anti-poisoning baseline · {active}
          </div>
          <svg width={180} height={46} style={{ display: "block" }}>
            <path d={spark.band} fill="var(--primary)" opacity={0.16} />
            <polyline points={spark.mean} fill="none" stroke="var(--primary)" strokeWidth={1.2} opacity={0.7} />
            <polyline points={spark.current} fill="none" stroke="var(--amber)" strokeWidth={1.8} />
          </svg>
          <div style={{ fontSize: 11, marginTop: 4 }}>
            <span style={{ color: "var(--amber)" }}>current {Math.round(latest.current)}</span>
            {"  "}
            <span style={{ color: "var(--faint)" }}>
              baseline {Math.round(latest.mean)}±{Math.round(latest.std)}
            </span>
            {"  "}
            <span style={{ color: latest.deviation > 2 ? "var(--red)" : "var(--dim)" }}>
              {latest.deviation.toFixed(1)}σ
            </span>
          </div>
        </div>
      )}

      {pkt && <PacketInspectCard packet={pkt} hosts={hosts} onClose={() => setPkt(null)} />}

      {dev && (
        <div style={DEVCARD}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <strong>{dev.hostname}</strong>
            <button onClick={() => setDev(null)} style={X} aria-label="close">
              ×
            </button>
          </div>
          <div className="mono" style={{ fontSize: 11, color: "var(--cyan)" }}>{dev.ip}</div>
          <div style={{ fontSize: 12, color: "var(--dim)", marginTop: 4 }}>
            {dev.role} · {dev.os}
          </div>
          <div style={{ fontSize: 11, color: "var(--faint)", marginTop: 6 }}>
            {(dev.services ?? []).map((s) => `${s.name}:${s.port}`).join(" · ") || "no exposed services"}
          </div>
        </div>
      )}
    </div>
  );
}

const WRAP: CSSProperties = {
  position: "relative",
  height: "calc(100vh - 150px)",
  margin: "0 22px",
  borderRadius: 14,
  overflow: "hidden",
  background: "radial-gradient(120% 120% at 50% 0%, rgba(24,95,165,0.10), transparent 60%)",
};
const BACK: CSSProperties = { position: "absolute", top: 14, left: 14, zIndex: 2 };
const HINT: CSSProperties = {
  position: "absolute",
  bottom: 16,
  left: 0,
  right: 0,
  textAlign: "center",
  color: "var(--faint)",
  fontSize: 12,
  pointerEvents: "none",
};
const READOUT: CSSProperties = {
  position: "absolute",
  bottom: 16,
  right: 16,
  padding: "10px 12px",
  borderRadius: 12,
  background: "rgba(10,16,26,0.92)",
  border: "1px solid var(--line)",
  zIndex: 3,
};
const DEVCARD: CSSProperties = {
  position: "absolute",
  top: 14,
  right: 16,
  width: 230,
  padding: "12px 14px",
  borderRadius: 12,
  background: "rgba(10,16,26,0.94)",
  border: "1px solid var(--line)",
  zIndex: 3,
};
const X: CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--faint)",
  fontSize: 18,
  cursor: "pointer",
  lineHeight: 1,
};
