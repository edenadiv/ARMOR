"""HubSink — forwards every agent EventLog into the live EventHub."""

from cdmas.common.logging.event_log import EventLog, EventType, InMemorySink
from cdmas.live.hub import EventHub
from cdmas.live.sink import HubSink


def _event() -> EventLog:
    return EventLog(
        lamport_ts=1,
        wall_ms=12.0,
        event_type=EventType.ALERT_PUBLISHED,
        agent_id="TMA:server",
        agent_type="TMA",
        segment="server",
        payload={"deviation_score": 3.0},
    )


async def test_hubsink_forwards_to_hub_as_agent_event():
    hub = EventHub()
    q = hub.subscribe()
    sink = HubSink(hub)
    await sink.write(_event())
    frame = await q.get()
    assert frame.kind == "agent_event"
    assert frame.payload["event_type"] == "ALERT_PUBLISHED"
    assert frame.payload["agent_id"] == "TMA:server"
    assert frame.ts_ms == 12.0


async def test_hubsink_preserves_inner_sink():
    hub = EventHub()
    inner = InMemorySink()
    sink = HubSink(hub, inner=inner)
    await sink.write(_event())
    assert len(inner.events) == 1
    assert inner.events[0].event_type is EventType.ALERT_PUBLISHED
