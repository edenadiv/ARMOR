"""A sink that forwards agent events into the live EventHub (and an optional inner sink).

Drop-in for any ``EventSink`` the agents already use, so wiring it in adds the live stream
without changing agent code or losing existing sink behaviour (e.g. structured logging).
"""

from __future__ import annotations

from cdmas.common.logging.event_log import EventLog, EventSink
from cdmas.live.hub import KIND_AGENT_EVENT, EventHub


class HubSink(EventSink):
    def __init__(self, hub: EventHub, inner: EventSink | None = None) -> None:
        self.hub = hub
        self.inner = inner

    async def write(self, event: EventLog) -> None:
        if self.inner is not None:
            await self.inner.write(event)
        self.hub.publish(KIND_AGENT_EVENT, event.model_dump(mode="json"), ts_ms=event.wall_ms)
