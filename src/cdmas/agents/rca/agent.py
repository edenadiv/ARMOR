"""Response Coordinator Agent — proportional response <500ms, resolution notices.

Phase 3 executes non-quarantine actions directly. QUARANTINE requires a coalition vote
(Phase 4); until then it falls back to BLOCK as a safe default.
"""

from __future__ import annotations

from typing import Any

from cdmas.agents.rca.policy import (
    ResponseAction,
    proportionality_score,
    select_proportional_action,
)
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import DecisionTrace, EventSink, EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Classification, Performative, ResponseType, Segment
from cdmas.common.models.resolution import ResolutionNotice
from cdmas.common.timing.clock import Clock
from cdmas.simulator.client import SimClientProtocol
from cdmas.simulator.models import ActionRequest

_SEVERITY_THRESHOLD = 0.7


class ResponseCoordinatorAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        sim: SimClientProtocol,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        super().__init__(agent_id, segment, bus, event_sink, clock=clock)
        self.sim = sim
        self._pending: list[dict[str, Any]] = []

    def setup(self) -> None:
        self.subscribe(Topic.THREAT_REPORTS)
        self.goals.add(Goal(description="coordinate response", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="respond",
                trigger=lambda b: len(self._pending) > 0,
                precondition=lambda b: True,
                body=self._respond,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        if message.topic is not Topic.THREAT_REPORTS:
            return
        threat = message.content["threat"]
        if (
            threat["classification"] == Classification.CONFIRMED_THREAT.value
            and threat["severity"] >= _SEVERITY_THRESHOLD
        ):
            self._pending.append(
                {"threat": threat, "ts_ms": message.content.get("ts_ms", self.now_ms())}
            )

    async def _respond(self, _agent: BaseAgent) -> None:
        while self._pending:
            item = self._pending.pop(0)
            threat = item["threat"]
            ts_ms: float = item["ts_ms"]
            severity: float = threat["severity"]
            seg = Segment(threat["segment"])
            action = select_proportional_action(severity)
            exec_type = await self._resolve_action(action, threat)
            result = await self.sim.apply_action(ActionRequest(type=exec_type, segment=seg))
            now = self.now_ms()
            await self.log_event(
                EventType.ACTION_EXECUTED,
                payload={
                    "signal": "response",
                    "action": exec_type.value,
                    "severity": severity,
                    "segment": seg.value,
                    "threat_id": threat["threat_id"],
                    "proportionality_score": proportionality_score(action),
                    "effectiveness": result.effectiveness,
                },
                latency_ms=int(now - ts_ms),
                decision_trace=DecisionTrace(
                    inputs={"threat_id": threat["threat_id"], "severity": severity},
                    plan_selected="respond",
                    reasoning=f"least-disruptive effective action for sev={severity:.2f}",
                    action=exec_type.value,
                ),
            )
            await self._resolve_incident(threat, seg, now)

    async def _resolve_action(self, action: ResponseAction, threat: dict[str, Any]) -> ResponseType:
        if action.type is ResponseType.QUARANTINE:
            # Phase 4 replaces this with a coalition vote.
            await self.log_event(
                EventType.ACTION_EXECUTED,
                payload={
                    "signal": "vote_required",
                    "action": "QUARANTINE",
                    "threat_id": threat["threat_id"],
                },
            )
            return ResponseType.BLOCK
        return action.type

    async def _resolve_incident(self, threat: dict[str, Any], seg: Segment, now: float) -> None:
        notice = ResolutionNotice(threat_id=threat["threat_id"], segment=seg, outcome="neutralized")
        await self.publish(
            ACLMessage(
                performative=Performative.INFORM,
                sender=self.agent_id,
                receiver="BROADCAST",
                topic=Topic.RESOLUTION,
                content={"resolution": notice.model_dump(mode="json"), "ts_ms": now},
            )
        )
        await self.log_event(
            EventType.INCIDENT_RESOLVED,
            payload={
                "threat_id": threat["threat_id"],
                "resolution_id": notice.resolution_id,
                "segment": seg.value,
            },
        )
