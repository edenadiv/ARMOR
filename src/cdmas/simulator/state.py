"""Segment state, defenses, and action application (SDD §6.1.1, Table 5)."""

from __future__ import annotations

from cdmas.common.models.enums import ResponseType, Segment
from cdmas.simulator.models import ActionRequest, ActionResult
from cdmas.simulator.topology import NetworkTopology

NORMAL = "NORMAL"
SUSPICIOUS = "SUSPICIOUS"
UNDER_ATTACK = "UNDER_ATTACK"

_EFFECTIVENESS: dict[ResponseType, float] = {
    ResponseType.THROTTLE: 0.8,
    ResponseType.BLOCK: 0.7,
    ResponseType.QUARANTINE: 0.95,
    ResponseType.REDEPLOY: 0.5,
    ResponseType.MONITOR: 0.1,
}


class StateManager:
    def __init__(self, topology: NetworkTopology) -> None:
        self.topology = topology
        self._health: dict[Segment, str] = {s: NORMAL for s in topology.segments}
        self._defenses: dict[Segment, list[str]] = {s: [] for s in topology.segments}
        self._quarantined: set[Segment] = set()

    def health(self, segment: Segment) -> str:
        return self._health.get(segment, NORMAL)

    def set_health(self, segment: Segment, health: str) -> None:
        self._health[segment] = health

    def mark_under_attack(self, segment: Segment) -> None:
        if segment not in self._quarantined:
            self._health[segment] = UNDER_ATTACK

    def active_defenses(self, segment: Segment) -> list[str]:
        return list(self._defenses.get(segment, []))

    def is_quarantined(self, segment: Segment) -> bool:
        return segment in self._quarantined

    def apply_action(self, req: ActionRequest) -> ActionResult:
        eff = _EFFECTIVENESS.get(req.type, 0.1)
        if req.type == ResponseType.QUARANTINE:
            self._quarantined.add(req.segment)
            self._health[req.segment] = NORMAL  # isolated from the rest of the network
            self._defenses.setdefault(req.segment, []).append("QUARANTINE")
            return ActionResult(accepted=True, effectiveness=eff, detail="segment quarantined")
        if req.type in (ResponseType.THROTTLE, ResponseType.BLOCK, ResponseType.REDEPLOY):
            self._defenses.setdefault(req.segment, []).append(req.type.value)
            return ActionResult(
                accepted=True, effectiveness=eff, detail=f"{req.type.value} applied"
            )
        return ActionResult(accepted=True, effectiveness=eff, detail="monitoring")

    def clear_defenses(self, segment: Segment) -> None:
        # Lift every defense on a segment and return it to NORMAL — used when its threat has
        # cleared so the simulator can free the resources those defenses reserved.
        self._defenses[segment] = []
        self._quarantined.discard(segment)
        self._health[segment] = NORMAL
