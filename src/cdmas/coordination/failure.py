"""Agent failure detection and coverage reassignment (SDD §4.5, Figure 11).

A heartbeat monitor flags an agent failed after 1s of silence; coverage of its segment is
reassigned to the minimum-load healthy peer, asserted to complete within 2s.
"""

from __future__ import annotations

HEARTBEAT_TIMEOUT_MS = 1000.0
REASSIGN_DEADLINE_MS = 2000.0


class HeartbeatMonitor:
    def __init__(self, *, timeout_ms: float = HEARTBEAT_TIMEOUT_MS) -> None:
        self.timeout_ms = timeout_ms
        self._last_seen: dict[str, float] = {}

    def beat(self, agent_id: str, now_ms: float) -> None:
        self._last_seen[agent_id] = now_ms

    def failed(self, now_ms: float) -> list[str]:
        return [a for a, ts in self._last_seen.items() if now_ms - ts > self.timeout_ms]

    def forget(self, agent_id: str) -> None:
        self._last_seen.pop(agent_id, None)


def select_failover_peer(candidates: dict[str, float]) -> str | None:
    """Pick the minimum-load healthy peer to take over (candidates: agent_id -> load)."""
    if not candidates:
        return None
    return min(candidates, key=lambda a: candidates[a])
