import { type CSSProperties, useState } from "react";

import { shortScenarioName } from "../lib/replay";
import { useReplay } from "../lib/replayContext";

const SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

export function ReplayControls() {
  const {
    scenarios,
    scenario,
    selectScenario,
    t,
    setT,
    duration,
    playing,
    setPlaying,
    speed,
    setSpeed,
    director,
    viewMode,
  } = useReplay();

  if (viewMode === "live") return <LiveControls />;

  const pct = Math.min(100, (t / duration) * 100);

  const onScenario = (i: number) => {
    if (director.active) {
      selectScenario(i); // (re)start step-by-step narration for the chosen scenario
      return;
    }
    if (i === scenario) {
      if (t >= duration) setT(0);
      setPlaying(!playing);
    } else {
      selectScenario(i);
    }
  };

  return (
    <div style={{ padding: "0 22px 18px" }}>
      <div className="scenario-bar">
        {scenarios.map((name, i) => (
          <button
            key={name}
            className={`btn${i === scenario ? " primary" : ""}`}
            title={name}
            aria-pressed={i === scenario}
            onClick={() => onScenario(i)}
          >
            {i === scenario && playing ? "❚❚" : "▶"} <span className="scn-num">S{i + 1}</span>
            {shortScenarioName(name)}
          </button>
        ))}
      </div>
      <div className="replay">
        <button
          className="btn"
          onClick={() => {
            setPlaying(false);
            setT(0);
          }}
        >
          ⏮ Restart
        </button>
        <span className="clock mono">
          {(t / 1000).toFixed(2)}s / {(duration / 1000).toFixed(2)}s
        </span>
        <input
          className="scrub"
          type="range"
          min={0}
          max={duration}
          value={t}
          style={{ "--pct": `${pct}%` } as CSSProperties}
          onChange={(e) => {
            setPlaying(false);
            setT(Number(e.target.value));
          }}
        />
        <div className="speeds">
          {SPEEDS.map((s) => (
            <button key={s} className={s === speed ? "active" : ""} onClick={() => setSpeed(s)}>
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function LiveControls() {
  const { live } = useReplay();
  const segments = live.segments.length ? live.segments : ["public-facing"];
  const [seg, setSeg] = useState(segments[0]);
  const target = segments.includes(seg) ? seg : segments[0];
  const stepMode = live.sim.mode === "step";

  return (
    <div style={{ padding: "0 22px 18px" }}>
      <div className="live-bar">
        <span className="live-bar-label">LIVE SIMULATION</span>
        <select
          className="seg-select"
          value={target}
          onChange={(e) => setSeg(e.target.value)}
          aria-label="Target segment"
        >
          {segments.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <button className="btn" onClick={() => live.sendLegal(target)} disabled={!live.connected}>
          ✅ Send Legal
        </button>
        <button
          className="btn danger"
          onClick={() => live.sendDos(target)}
          disabled={!live.connected}
        >
          ⚡ Send DoS
        </button>
        <span className="live-sep" />
        <button
          className={`btn${!stepMode ? " primary" : ""}`}
          onClick={() => live.setRunMode("auto")}
          disabled={!live.connected}
        >
          ▶ Auto-run
        </button>
        <button
          className={`btn${stepMode ? " primary" : ""}`}
          onClick={() => live.setRunMode("step")}
          disabled={!live.connected}
        >
          ❚❚ Step
        </button>
        <button
          className="btn"
          onClick={() => live.next()}
          disabled={!live.connected || !live.sim.awaiting_next}
        >
          Next ▶
        </button>
        <span className="live-status mono">
          {live.connected
            ? `round ${live.sim.round} · ${live.sim.mode}${live.sim.awaiting_next ? " · awaiting next" : ""}`
            : "connecting…"}
        </span>
      </div>
    </div>
  );
}
