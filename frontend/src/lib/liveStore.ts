/* Live store: fold the backend WebSocket frames into the SAME DerivedState the replay
   engine produces, so every panel works in live mode unchanged. Pure reducer — unit-tested. */
import { type DerivedState, deriveState } from "./replay";
import type { CdmasEvent, TopologyInfo } from "./types";

export interface StreamFrame {
  kind: string;
  server_seq: number;
  ts_ms: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: Record<string, any>;
}

export interface ConnStatus {
  agents_connected: number;
  agents_total: number;
  bus_connected: boolean;
  stream_connected: boolean;
}

export interface SimMode {
  mode: string; // "auto" | "step"
  paused: boolean;
  awaiting_next: boolean;
  round: number;
}

export interface LiveState {
  events: CdmasEvent[];
  topology: TopologyInfo;
  conn: ConnStatus;
  sim: SimMode;
  lastTs: number;
}

const MAX_EVENTS = 3000;

export const initialLiveState: LiveState = {
  events: [],
  topology: { segments: [], adjacency: {} },
  conn: { agents_connected: 0, agents_total: 0, bus_connected: false, stream_connected: false },
  sim: { mode: "auto", paused: true, awaiting_next: false, round: 0 },
  lastTs: 0,
};

function append(state: LiveState, ev: CdmasEvent): LiveState {
  const events = [...state.events, ev].slice(-MAX_EVENTS);
  return { ...state, events, lastTs: Math.max(state.lastTs, ev.wall_ms ?? 0) };
}

export function liveReduce(state: LiveState, frame: StreamFrame): LiveState {
  switch (frame.kind) {
    case "topology":
      return {
        ...state,
        topology: {
          segments: frame.payload.segments ?? [],
          adjacency: frame.payload.adjacency ?? {},
        },
      };
    case "agent_event":
      return append(state, frame.payload as CdmasEvent);
    case "sim_event":
      // A manual DoS becomes a visible attacker->network flow until the TMA reacts.
      if (frame.payload.signal === "manual_dos") {
        return append(state, {
          event_id: `sim-${frame.server_seq}`,
          lamport_ts: 0,
          wall_ms: frame.ts_ms,
          event_type: "ACTION_EXECUTED",
          timestamp: "",
          agent_id: "ATK:ddos",
          agent_type: "ATK",
          segment: frame.payload.segment ?? null,
          payload: { signal: "attack_action", attack_type: frame.payload.attack_type ?? "DDOS" },
          latency_ms: null,
          decision_trace: null,
        });
      }
      return state;
    case "connection_status":
      return { ...state, conn: { ...state.conn, ...frame.payload } };
    case "simulation_state":
      return { ...state, sim: { ...state.sim, ...frame.payload } };
    default:
      return state;
  }
}

export function liveDerived(state: LiveState): DerivedState {
  return deriveState(state.events, state.lastTs, state.topology.segments);
}
