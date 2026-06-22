import { describe, expect, it } from "vitest";

import { baselineSeriesFromEvents, baselineSparkline } from "./baseline";
import { deviceHealth } from "./health";
import { hostFor, labelFor } from "./inspect";
import type { CdmasEvent, HostInfo, SampledPacket } from "./types";

const host = (ip: string, segment = "server"): HostInfo => ({
  hostname: `host-${ip}`,
  ip,
  segment,
  role: "database",
});

const pkt = (dst: string, kind: SampledPacket["kind"]): SampledPacket => ({
  src_ip: "x",
  dst_ip: dst,
  port: 1,
  protocol: "TCP",
  pkt_size: 1,
  freq: 1,
  ts_ms: 0,
  kind,
  segment: "server",
  alert_ms: null,
});

describe("inspect", () => {
  it("resolves a named host and labels unknown/attacker IPs", () => {
    const hosts = [host("10.0.2.20")];
    expect(hostFor("10.0.2.20", hosts)?.hostname).toBe("host-10.0.2.20");
    expect(hostFor("9.9.9.9", hosts)).toBeNull();
    expect(labelFor("203.0.1.2", hosts)).toBe("internet / attacker");
  });
});

describe("deviceHealth", () => {
  it("is crit when the device is an attack target", () => {
    expect(deviceHealth(host("10.0.2.20"), "under_attack", [pkt("10.0.2.20", "ddos")]).level).toBe("crit");
  });
  it("is warn in an under-attack segment but not targeted", () => {
    expect(deviceHealth(host("10.0.2.20"), "under_attack", [pkt("10.0.2.20", "benign")]).level).toBe("warn");
  });
  it("is ok otherwise", () => {
    expect(deviceHealth(host("10.0.2.20"), "normal", []).level).toBe("ok");
  });
});

describe("baseline readout", () => {
  const ev = (seg: string, current: number, mean: number, std: number): CdmasEvent => ({
    event_id: `${seg}-${current}`,
    lamport_ts: 1,
    wall_ms: current,
    event_type: "ACTION_EXECUTED",
    timestamp: "",
    agent_id: "TMA:server",
    agent_type: "TMA",
    segment: seg,
    payload: { signal: "baseline_update", current, mean, std },
    latency_ms: null,
    decision_trace: null,
  });

  it("extracts a per-segment series from baseline_update events", () => {
    const series = baselineSeriesFromEvents([ev("server", 100, 90, 5), ev("internal", 9, 9, 1)], "server");
    expect(series).toHaveLength(1);
    expect(series[0].current).toBe(100);
  });

  it("builds sparkline geometry from a series", () => {
    const series = baselineSeriesFromEvents([ev("server", 100, 90, 5), ev("server", 5000, 92, 6)], "server");
    const spark = baselineSparkline(series, 100, 40);
    expect(spark.hasData).toBe(true);
    expect(spark.current.length).toBeGreaterThan(0);
    expect(spark.band.startsWith("M")).toBe(true);
  });

  it("has no data for a short series", () => {
    expect(baselineSparkline([], 100, 40).hasData).toBe(false);
  });
});
