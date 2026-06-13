/* React lifecycle around the live WebSocket: connects when enabled, folds frames into a
   LiveState via the pure reducer, and exposes the manual/control actions as REST posts. */
import { useEffect, useState } from "react";

import { type LiveState, initialLiveState, liveReduce } from "./liveStore";

const meta = import.meta as unknown as { env?: Record<string, string | undefined> };
const env = meta.env ?? {};
const HTTP = env.VITE_LIVE_HTTP ?? "http://localhost:8000";
const TOKEN = env.VITE_LIVE_TOKEN ?? "changeme";
const WS = HTTP.replace(/^http/, "ws") + "/ws/events";

export interface LiveConnection {
  state: LiveState;
  connected: boolean;
  sendDos: (segment: string) => void;
  sendLegal: (segment: string) => void;
  setRunMode: (m: "auto" | "step") => void;
  next: () => void;
}

export function useLiveConnection(enabled: boolean): LiveConnection {
  const [state, setState] = useState<LiveState>(initialLiveState);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setState(initialLiveState);
      setConnected(false);
      return;
    }
    let closed = false;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS}?token=${encodeURIComponent(TOKEN)}`);
    } catch {
      return;
    }
    ws.onopen = () => !closed && setConnected(true);
    ws.onclose = () => !closed && setConnected(false);
    ws.onerror = () => !closed && setConnected(false);
    ws.onmessage = (e) => {
      try {
        const frame = JSON.parse(e.data);
        setState((s) => liveReduce(s, frame));
      } catch {
        /* ignore malformed frame */
      }
    };
    return () => {
      closed = true;
      ws?.close();
      setConnected(false);
    };
  }, [enabled]);

  const post = (path: string, body: Record<string, unknown>): void => {
    void fetch(`${HTTP}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` },
      body: JSON.stringify(body),
    }).catch(() => {});
  };

  return {
    state,
    connected,
    sendDos: (segment) => post("/manual/send-dos", { segment }),
    sendLegal: (segment) => post("/manual/send-legal", { segment }),
    setRunMode: (mode) => post("/control/mode", { mode }),
    next: () => post("/control/next", {}),
  };
}
