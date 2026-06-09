import { useMemo } from "react";

import { useReplay } from "../lib/replayContext";

const NODES: Record<string, { x: number; y: number; color: string }> = {
  "ATK-DDOS": { x: 90, y: 90, color: "var(--red)" },
  "ATK-LAT": { x: 90, y: 250, color: "var(--red)" },
  CLIENTS: { x: 90, y: 170, color: "var(--green)" },
  NETWORK: { x: 280, y: 170, color: "var(--amber)" },
  TMA: { x: 450, y: 60, color: "var(--cyan)" },
  ACA: { x: 520, y: 130, color: "var(--green)" },
  RCA: { x: 520, y: 210, color: "var(--amber)" },
  TIA: { x: 450, y: 280, color: "var(--violet)" },
  RAA: { x: 390, y: 340, color: "var(--cyan)" },
};

const NODE_LABELS: Record<string, string> = {
  "ATK-DDOS": "ATK-DDOS",
  "ATK-LAT": "ATK-LAT",
  CLIENTS: "LEGIT-CLIENTS",
  NETWORK: "NETWORK",
};

const KIND_COLOR: Record<string, string> = {
  attack: "var(--red)",
  normal: "var(--green)",
  allow: "var(--green)",
  alert: "var(--cyan)",
  report: "var(--green)",
  coalition: "var(--violet)",
  correlate: "var(--violet)",
  vote: "var(--amber)",
  grant: "var(--cyan)",
  mitigate: "var(--green)",
};

export function MessageFlow() {
  const { data, derived, t } = useReplay();
  const coalition = derived.coalitions[0];
  const timeline = useMemo(() => {
    return data.replay.events
      .filter((e) => e.wall_ms <= t)
      .filter((e) => {
        const sig = e.payload?.signal;
        if (sig === "attack_action") return true;
        if (e.event_type === "ALERT_PUBLISHED") return true;
        if (e.event_type === "THREAT_CLASSIFIED") return true;
        if (e.event_type === "ACTION_EXECUTED" && sig === "response") return true;
        return false;
      })
      .slice(-8)
      .map((e) => {
        const ts = `${(e.wall_ms / 1000).toFixed(2)}s`;
        const seg = e.segment ? ` (${e.segment})` : "";
        const sig = e.payload?.signal;
        if (sig === "attack_action") {
          return {
            ts,
            level: "attack",
            text: `${String(e.payload?.attack_type ?? "ATTACK")} sent to network${seg}`,
          };
        }
        if (e.event_type === "ALERT_PUBLISHED") {
          return { ts, level: "alert", text: `TMA detected anomaly and published alert${seg}` };
        }
        if (e.event_type === "THREAT_CLASSIFIED") {
          if (!e.payload?.reported || e.payload?.classification === "NORMAL") {
            return {
              ts,
              level: "normal",
              text: `Normal traffic verified and allowed${seg}`,
            };
          }
          return {
            ts,
            level: "report",
            text: `ACA classified ${String(e.payload?.attack_type ?? "threat")}${seg}`,
          };
        }
        return {
          ts,
          level: "mitigate",
          text: `RCA executed ${String(e.payload?.action ?? "response")}${seg}`,
        };
      })
      .reverse();
  }, [data.replay.events, t]);

  return (
    <div className="panel" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
      <div className="panel-title">
        <span className="tick" />
        <h3>Agent Message Flow &amp; Coalition Overlay</h3>
      </div>
      <svg viewBox="0 0 620 380" style={{ width: "100%", flex: 1, minHeight: 0 }}>
        <style>{`
          .edge { stroke-dasharray: 6 8; animation: dash 0.7s linear infinite; }
          .edge-attack { stroke-dasharray: 7 7; animation-duration: 0.55s; }
          .edge-normal { stroke-dasharray: 2 10; animation-duration: 1.2s; }
          .edge-alert { stroke-dasharray: 5 8; animation-duration: 0.8s; }
          .edge-control { stroke-dasharray: 6 8; animation-duration: 0.7s; }
          @keyframes dash { to { stroke-dashoffset: -28; } }
          .node-c { transition: all .3s ease; }
        `}</style>

        {coalition && (
          <g>
            <ellipse
              cx={490}
              cy={180}
              rx={128}
              ry={158}
              fill="rgba(176,139,255,0.05)"
              stroke="var(--violet)"
              strokeDasharray="4 6"
              strokeWidth={1.2}
            />
            <text x={360} y={24} className="flow-label" fill="var(--violet)">
              COALITION · {coalition.members.length} members
            </text>
          </g>
        )}

        <text x={54} y={26} className="flow-label" fill="var(--red)">
          ATTACKERS
        </text>
        <text x={44} y={188} className="flow-label" fill="var(--green)">
          NORMAL TRAFFIC
        </text>
        <text x={246} y={26} className="flow-label" fill="var(--amber)">
          NETWORK
        </text>
        <text x={430} y={26} className="flow-label" fill="var(--green)">
          DEFENSE AGENTS
        </text>

        {derived.flows.map((f, i) => {
          const a = NODES[f.from];
          const b = NODES[f.to];
          if (!a || !b) return null;
          const edgeClass =
            f.kind === "attack"
              ? "edge edge-attack"
              : f.kind === "normal" || f.kind === "allow"
                ? "edge edge-normal"
                : f.kind === "alert"
                  ? "edge edge-alert"
                  : "edge edge-control";
          return (
            <line
              key={`${f.from}-${f.to}-${i}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={KIND_COLOR[f.kind] ?? "var(--cyan)"}
              strokeWidth={1.6}
              className={edgeClass}
              opacity={f.kind === "normal" || f.kind === "allow" ? 0.78 : 0.9}
            />
          );
        })}

        {Object.entries(NODES).map(([name, n]) => {
          const active = derived.flows.some((f) => f.from === name || f.to === name);
          return (
            <g key={name}>
              <circle
                className="node-c"
                cx={n.x}
                cy={n.y}
                r={active ? 30 : 26}
                fill="rgba(7,12,20,0.9)"
                stroke={n.color}
                strokeWidth={active ? 2.4 : 1.4}
                style={{ filter: active ? `drop-shadow(0 0 10px ${n.color})` : "none" }}
              />
              <text
                x={n.x}
                y={n.y + 5}
                textAnchor="middle"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: name.length > 5 ? 11 : 14,
                  fontWeight: 700,
                  fill: n.color,
                }}
              >
                {NODE_LABELS[name] ?? name}
              </text>
            </g>
          );
        })}
      </svg>
      <div
        style={{
          borderTop: "1px solid var(--line)",
          marginTop: 10,
          paddingTop: 10,
          maxHeight: 125,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        {timeline.length === 0 && <div className="empty">waiting for attack/defense actions...</div>}
        {timeline.map((item, i) => (
          <div
            key={`${item.ts}-${item.text}-${i}`}
            style={{
              display: "flex",
              gap: 10,
              fontFamily: "var(--font-body)",
              fontSize: 11,
              borderLeft: `2px solid ${KIND_COLOR[item.level] ?? "var(--cyan)"}`,
              padding: "3px 8px",
              background: "rgba(7, 12, 20, 0.4)",
            }}
          >
            <span style={{ color: "var(--faint)", minWidth: 46, fontFamily: "var(--font-mono)" }}>
              {item.ts}
            </span>
            <span style={{ color: "var(--text)" }}>{item.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
