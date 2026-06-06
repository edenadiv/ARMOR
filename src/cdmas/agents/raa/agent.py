"""Resource Allocator Agent — overhead monitoring + resource reclamation.

Phase 3 implements overhead monitoring (warn 35% / critical 40%) and reclamation on
resolution. The sealed-bid auction is wired in Phase 4.
"""

from __future__ import annotations

from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.belief_base import Belief
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import EventSink, EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.timing.clock import Clock
from cdmas.simulator.client import SimClientProtocol

_MONITOR_INTERVAL_MS = 1000.0
_WARN = 0.35
_CAP = 0.40


class ResourceAllocatorAgent(BaseAgent):
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
        self._last_monitor_ms = -1e9

    def setup(self) -> None:
        self.subscribe(Topic.RESOURCE_BIDS)
        self.subscribe(Topic.RESOLUTION)
        self.goals.add(Goal(description="manage resources", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="monitor",
                trigger=lambda b: True,
                precondition=lambda b: True,
                body=self._monitor,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        if message.topic is Topic.RESOLUTION:
            self.beliefs.revise(
                Belief(predicate="reclaim_pending", value=True, source=message.sender)
            )
            self.beliefs.revise(
                Belief(
                    predicate="reclaim_ts",
                    value=message.content.get("ts_ms", self.now_ms()),
                    source=message.sender,
                )
            )

    async def _monitor(self, _agent: BaseAgent) -> None:
        now = self.now_ms()
        if self.beliefs.value("reclaim_pending"):
            self.beliefs.revise(
                Belief(predicate="reclaim_pending", value=False, source=self.agent_id)
            )
            ts = self.beliefs.value("reclaim_ts", now)
            await self.log_event(
                EventType.RESOURCE_ALLOCATED,
                payload={"signal": "reclaim"},
                latency_ms=int(now - ts),
            )
        if now - self._last_monitor_ms >= _MONITOR_INTERVAL_MS:
            self._last_monitor_ms = now
            state = await self.sim.get_state()
            overhead = state.resource_overhead
            status = "CRITICAL" if overhead > _CAP else "WARNING" if overhead > _WARN else "OK"
            await self.log_event(
                EventType.RESOURCE_ALLOCATED,
                payload={"signal": "overhead", "overhead": overhead, "status": status},
            )
