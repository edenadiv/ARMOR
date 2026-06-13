import { describe, expect, it } from "vitest";

import { type StreamFrame, initialLiveState, liveDerived, liveReduce } from "./liveStore";

const frame = (
  kind: string,
  payload: Record<string, unknown>,
  ts_ms = 0,
  seq = 1,
): StreamFrame => ({ kind, server_seq: seq, ts_ms, payload });

const alertEvent = (wall_ms: number) => ({
  event_id: `a${wall_ms}`,
  lamport_ts: 1,
  wall_ms,
  event_type: "ALERT_PUBLISHED",
  timestamp: "",
  agent_id: "TMA:public-facing",
  agent_type: "TMA",
  segment: "public-facing",
  payload: { deviation_score: 3 },
  latency_ms: 0,
  decision_trace: null,
});

describe("liveReduce", () => {
  it("sets topology from a topology frame", () => {
    const s = liveReduce(
      initialLiveState,
      frame("topology", {
        segments: ["public-facing", "internal"],
        adjacency: { "public-facing": ["internal"], internal: ["public-facing"] },
      }),
    );
    expect(s.topology.segments).toEqual(["public-facing", "internal"]);
  });

  it("accumulates agent events and tracks the latest timestamp", () => {
    const s = liveReduce(initialLiveState, frame("agent_event", alertEvent(120), 120));
    expect(s.events).toHaveLength(1);
    expect(s.lastTs).toBe(120);
  });

  it("synthesizes an attacker flow from a manual DoS sim_event", () => {
    const s = liveReduce(
      initialLiveState,
      frame("sim_event", { signal: "manual_dos", segment: "public-facing", attack_type: "DDOS" }, 50),
    );
    const atk = s.events.find((e) => e.payload?.signal === "attack_action");
    expect(atk).toBeTruthy();
    expect(atk!.agent_type).toBe("ATK");
    expect(atk!.segment).toBe("public-facing");
  });

  it("updates connection and simulation state", () => {
    let s = liveReduce(
      initialLiveState,
      frame("connection_status", {
        agents_connected: 5,
        agents_total: 5,
        bus_connected: true,
        stream_connected: true,
      }),
    );
    s = liveReduce(
      s,
      frame("simulation_state", { mode: "step", paused: false, awaiting_next: true, round: 3 }),
    );
    expect(s.conn.agents_connected).toBe(5);
    expect(s.conn.stream_connected).toBe(true);
    expect(s.sim.mode).toBe("step");
    expect(s.sim.awaiting_next).toBe(true);
  });
});

describe("liveDerived", () => {
  it("derives the same DerivedState shape from accumulated live events", () => {
    let s = liveReduce(
      initialLiveState,
      frame("topology", { segments: ["public-facing"], adjacency: { "public-facing": [] } }),
    );
    s = liveReduce(s, frame("agent_event", alertEvent(120), 120));
    const d = liveDerived(s);
    expect(d.segments["public-facing"].status).toBe("under_attack");
    expect(d.counts.alerts).toBe(1);
  });
});
