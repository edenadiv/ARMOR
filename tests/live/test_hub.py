"""EventHub — the process-global fan-out for live dashboard frames."""

import asyncio

from cdmas.live.hub import EventHub


async def test_publish_fans_out_to_all_subscribers():
    hub = EventHub()
    a = hub.subscribe()
    b = hub.subscribe()
    frame = hub.publish("sim_event", {"x": 1}, ts_ms=10.0)
    fa = await asyncio.wait_for(a.get(), 0.1)
    fb = await asyncio.wait_for(b.get(), 0.1)
    assert fa.kind == "sim_event" and fa.payload == {"x": 1} and fa.ts_ms == 10.0
    assert fa.server_seq == frame.server_seq == 1
    assert fb.server_seq == 1


async def test_server_seq_is_monotonic():
    hub = EventHub()
    q = hub.subscribe()
    hub.publish("a", {})
    hub.publish("b", {})
    assert (await q.get()).server_seq == 1
    assert (await q.get()).server_seq == 2


async def test_unsubscribe_stops_delivery():
    hub = EventHub()
    q = hub.subscribe()
    hub.unsubscribe(q)
    hub.publish("a", {})
    assert q.empty()
    assert hub.subscribers == 0


async def test_overflow_drops_oldest_and_counts():
    hub = EventHub(max_queue=2)
    q = hub.subscribe()
    hub.publish("a", {"n": 1})
    hub.publish("b", {"n": 2})
    hub.publish("c", {"n": 3})  # overflow -> drop oldest (n=1), keep newest
    assert hub.dropped >= 1
    delivered = [(await q.get()).payload["n"] for _ in range(q.qsize())]
    assert 3 in delivered  # newest survives
    assert 1 not in delivered  # oldest dropped
