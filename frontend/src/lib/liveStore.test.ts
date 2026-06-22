import { describe, expect, it } from "vitest";

import {
  type StreamFrame,
  initialLiveState,
  liveDerived,
  liveMetrics,
  liveReduce,
} from "./liveStore";

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

  it("synthesizes a verified-legitimate flow from a manual legal sim_event", () => {
    const s = liveReduce(
      initialLiveState,
      frame("sim_event", { signal: "manual_legal", segment: "public-facing" }, 60),
    );
    const legal = s.events.find(
      (e) => e.event_type === "THREAT_CLASSIFIED" && e.payload?.classification === "NORMAL",
    );
    expect(legal).toBeTruthy();
    expect(legal!.payload.reported).toBe(false);
  });

  it("synthesizes a typed attacker flow from any manual_<type> sim_event", () => {
    const s = liveReduce(
      initialLiveState,
      frame("sim_event", { signal: "manual_lateral", segment: "internal", attack_type: "LATERAL" }, 70),
    );
    const atk = s.events.find((e) => e.payload?.signal === "attack_action");
    expect(atk).toBeTruthy();
    expect(atk!.agent_type).toBe("ATK");
    expect(atk!.agent_id).toBe("ATK:lateral");
    expect(atk!.payload.attack_type).toBe("LATERAL");
    expect(atk!.segment).toBe("internal");
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

const responseEvent = (wall_ms: number, latency_ms: number) => ({
  event_id: `r${wall_ms}`,
  lamport_ts: 1,
  wall_ms,
  event_type: "ACTION_EXECUTED",
  timestamp: "",
  agent_id: "RCA:public-facing",
  agent_type: "RCA",
  segment: "public-facing",
  payload: { signal: "response", action: "BLOCK" },
  latency_ms,
  decision_trace: null,
});

describe("liveMetrics", () => {
  it("availability drops and incidents rise while a segment is under attack", () => {
    let s = liveReduce(
      initialLiveState,
      frame("topology", { segments: ["public-facing", "internal"], adjacency: {} }),
    );
    s = liveReduce(s, frame("agent_event", alertEvent(100), 100));
    const m = liveMetrics(s);
    expect(m.availability).toBeCloseTo(0.5); // 1 of 2 segments compromised
    expect(m.concurrent_incidents).toBe(1);
  });

  it("computes mean response latency from real events", () => {
    let s = liveReduce(
      initialLiveState,
      frame("topology", { segments: ["public-facing"], adjacency: {} }),
    );
    s = liveReduce(s, frame("agent_event", responseEvent(200, 120), 200));
    s = liveReduce(s, frame("agent_event", responseEvent(260, 80), 260));
    expect(liveMetrics(s).mttr_response_ms).toBeCloseTo(100); // (120 + 80) / 2
  });

  it("returns safe zeros (no NaN) for an empty stream", () => {
    const m = liveMetrics(initialLiveState);
    expect(m.mttr_response_ms).toBe(0);
    expect(m.availability).toBe(1);
    expect(Number.isNaN(m.availability)).toBe(false);
  });
});

describe("metrics & packets frames", () => {
  it("stores backend-computed metrics from a metrics frame", () => {
    const s = liveReduce(
      initialLiveState,
      frame("metrics", { dr: 1, fpr: 0, social_welfare: 0.93, attacker_utility: 0.1 }),
    );
    // Real SW/attacker_utility from the backend analytics, not the live heuristic's neutral 0.
    expect(s.metrics?.social_welfare).toBe(0.93);
    expect(s.metrics?.attacker_utility).toBe(0.1);
  });

  it("stores sampled packets from a packets frame", () => {
    const s = liveReduce(
      initialLiveState,
      frame("packets", {
        packets: [
          {
            src_ip: "203.0.1.2",
            dst_ip: "10.0.0.1",
            port: 443,
            protocol: "TCP",
            pkt_size: 512,
            freq: 5000,
            ts_ms: 50,
            kind: "ddos",
            segment: "public-facing",
            alert_ms: null,
          },
        ],
      }),
    );
    expect(s.packets).toHaveLength(1);
    expect(s.packets[0].kind).toBe("ddos");
  });
});

describe("baseline frames", () => {
  it("accumulates a per-segment anti-poisoning baseline series", () => {
    let s = liveReduce(
      initialLiveState,
      frame("baseline", { segment: "public-facing", current: 1000, mean: 800, std: 50, deviation: 4 }, 100),
    );
    s = liveReduce(
      s,
      frame("baseline", { segment: "public-facing", current: 900, mean: 800, std: 50, deviation: 2 }, 200),
    );
    expect(s.baselines["public-facing"]).toHaveLength(2);
    expect(s.baselines["public-facing"][1].current).toBe(900);
    expect(s.baselines["public-facing"][1].ts_ms).toBe(200);
  });
});
