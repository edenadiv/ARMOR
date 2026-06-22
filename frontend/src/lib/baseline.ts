/* The anti-poisoning baseline readout: derive a per-segment current-vs-baseline series from
   the TMA's baseline_update events (works in live and replay), and turn it into sparkline
   geometry — a current line over a flat mean +/- std band. The whole point of the chart is
   that the band stays flat while `current` spikes during an attack. */
import type { BaselinePoint, CdmasEvent } from "./types";

export function baselineSeriesFromEvents(events: CdmasEvent[], segment: string): BaselinePoint[] {
  const out: BaselinePoint[] = [];
  for (const e of events) {
    if (e.payload?.signal === "baseline_update" && e.segment === segment) {
      out.push({
        ts_ms: e.wall_ms,
        current: e.payload.current ?? e.payload.mean ?? 0,
        mean: e.payload.mean ?? 0,
        std: e.payload.std ?? 0,
        deviation: e.payload.deviation ?? 0,
      });
    }
  }
  return out;
}

export interface Sparkline {
  hasData: boolean;
  current: string; // polyline points "x,y x,y ..."
  mean: string;
  band: string; // filled polygon path for mean +/- std
}

export function baselineSparkline(series: BaselinePoint[], w: number, h: number): Sparkline {
  if (series.length < 2) return { hasData: false, current: "", mean: "", band: "" };
  const n = series.length;
  const maxV = Math.max(1, ...series.map((p) => Math.max(p.current, p.mean + p.std)));
  const xs = (i: number) => (i / (n - 1)) * w;
  const ys = (v: number) => h - (Math.max(0, v) / maxV) * h;
  const current = series.map((p, i) => `${xs(i).toFixed(1)},${ys(p.current).toFixed(1)}`).join(" ");
  const mean = series.map((p, i) => `${xs(i).toFixed(1)},${ys(p.mean).toFixed(1)}`).join(" ");
  const top = series.map((p, i) => `${xs(i).toFixed(1)},${ys(p.mean + p.std).toFixed(1)}`);
  const bot = series.map((p, i) => `${xs(i).toFixed(1)},${ys(p.mean - p.std).toFixed(1)}`).reverse();
  return { hasData: true, current, mean, band: `M ${[...top, ...bot].join(" L ")} Z` };
}
