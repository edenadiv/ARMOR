import { Link, NavLink } from "react-router-dom";

import { shortScenarioName } from "../lib/replay";
import { useReplay } from "../lib/replayContext";

export function Header({ onStepThrough }: { onStepThrough: () => void }) {
  const { playing, scenarios, scenario, viewMode, setViewMode, live } = useReplay();
  const isLive = viewMode === "live";

  return (
    <header className="topbar">
      <div className="left-header-section">
        <div className="brand">
          <Link to="/" className="brand-home" aria-label="Go to dashboard">
            <svg width="36" height="36" viewBox="0 8 100 100" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M50 15 L80 35 L80 65 C80 85 65 95 50 100 C35 95 20 85 20 65 L20 35 Z"
                fill="none"
                stroke="#185FA5"
                strokeWidth="2.2"
                strokeLinejoin="round"
              />
              <path
                d="M50 25 L70 38 L70 65 C70 80 60 90 50 94 C40 90 30 80 30 65 L30 38 Z"
                fill="#185FA5"
                opacity="0.2"
              />
              <path
                d="M50 35 L60 43 L60 65 C60 75 55 85 50 88 C45 85 40 75 40 65 L40 43 Z"
                fill="#185FA5"
                opacity="0.5"
              />
            </svg>
            <span className="brand-label">ARMOR</span>
          </Link>
        </div>
        <nav className="nav">
          <NavLink to="/network">Network</NavLink>
          <NavLink to="/inspector">Agent Inspector</NavLink>
          <NavLink to="/validator">Validator</NavLink>
        </nav>
      </div>
      <div className="right-actions">
        <div className="mode-toggle" role="group" aria-label="View mode">
          <button className={!isLive ? "on" : ""} onClick={() => setViewMode("replay")}>
            Replay
          </button>
          <button className={isLive ? "on" : ""} onClick={() => setViewMode("live")}>
            Live
          </button>
        </div>
        {isLive ? (
          <div className="conn-badges">
            <span className={`conn-badge ${live.connected ? "ok" : "bad"}`}>
              <span className="conn-dot" /> Stream
            </span>
            <span className={`conn-badge ${live.conn.agents_connected > 0 ? "ok" : "bad"}`}>
              <span className="conn-dot" /> Agents {live.conn.agents_connected}/{live.conn.agents_total}
            </span>
            <span className={`conn-badge ${live.conn.bus_connected ? "ok" : "bad"}`}>
              <span className="conn-dot" /> Bus
            </span>
          </div>
        ) : (
          <>
            <button className="btn primary header-tour" onClick={onStepThrough}>
              ▶ Step by Step
            </button>
            <span className={`live-pill header-status ${playing ? "is-playing" : "is-paused"}`}>
              <span className="live-dot" /> {playing ? "SIMULATION ACTIVE" : "SIMULATION PAUSED"} ·{" "}
              {shortScenarioName(scenarios[scenario]).toUpperCase()}
            </span>
          </>
        )}
      </div>
    </header>
  );
}
