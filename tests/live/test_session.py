"""LiveSession — runs the real fleet in-process and streams it to the EventHub."""

import asyncio

from cdmas.common.logging.event_log import EventLog, EventType
from cdmas.common.models.enums import Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.live.hub import StreamFrame
from cdmas.live.session import LiveSession


def _drain(q) -> list[StreamFrame]:
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def _session() -> LiveSession:
    return LiveSession(segments=[Segment.PUBLIC_FACING], clock=ManualClock())


async def _wait_until(predicate, timeout: float = 3.0) -> bool:
    """Poll a condition rather than sleeping a fixed time — robust under CI load."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.005)
    return False


async def test_send_dos_injects_attack_and_emits_sim_event():
    s = _session()
    q = s.hub.subscribe()
    s.send_dos("public-facing", intensity=3.0)
    assert s.sim.ground_truth().is_attack(Segment.PUBLIC_FACING, s.clock.now_ms()) is True
    sim_events = [f for f in _drain(q) if f.kind == "sim_event"]
    assert any(f.payload.get("signal") == "manual_dos" for f in sim_events)


async def test_manual_dos_expires_so_the_system_can_recover():
    s = _session()
    s.send_dos("public-facing", duration_ms=200)
    gt = s.sim.ground_truth()
    now = s.clock.now_ms()
    assert gt.is_attack(Segment.PUBLIC_FACING, now) is True  # active now
    assert gt.is_attack(Segment.PUBLIC_FACING, now + 500) is False  # subsided later


async def test_send_legal_does_not_inject_an_attack():
    s = _session()
    q = s.hub.subscribe()
    s.send_legal("public-facing")
    assert s.sim.ground_truth().is_attack(Segment.PUBLIC_FACING, s.clock.now_ms()) is False
    sim_events = [f for f in _drain(q) if f.kind == "sim_event"]
    assert any(f.payload.get("signal") == "manual_legal" for f in sim_events)


async def test_live_fleet_detects_injected_dos():
    s = _session()
    q = s.hub.subscribe()
    for _ in range(30):  # warm up the traffic baseline
        await s.tick_round()
    s.send_dos("public-facing", intensity=4.0)
    for _ in range(15):
        await s.tick_round()
    agent_events = [f for f in _drain(q) if f.kind == "agent_event"]
    types = {f.payload["event_type"] for f in agent_events}
    assert "ALERT_PUBLISHED" in types  # the real TMA detected the live attack


async def test_finer_clock_yields_nonzero_latencies():
    s = _session()
    q = s.hub.subscribe()
    for _ in range(30):
        await s.tick_round()
    s.send_dos("public-facing", intensity=4.0)
    for _ in range(15):
        await s.tick_round()
    agent_events = [f for f in _drain(q) if f.kind == "agent_event"]
    lats = [
        f.payload.get("latency_ms") for f in agent_events if f.payload.get("latency_ms") is not None
    ]
    # sub-stepping spreads the pipeline in time, so decisions take a real (>0) latency
    assert any((latency or 0) > 0 for latency in lats)


async def test_status_frames_report_topology_and_stream():
    s = _session()
    q = s.hub.subscribe()
    await s.tick_round()
    frames = _drain(q)
    status = [f for f in frames if f.kind == "connection_status"]
    state = [f for f in frames if f.kind == "simulation_state"]
    assert status and state
    assert status[-1].payload["stream_connected"] is True
    assert status[-1].payload["agents_total"] >= 1
    assert state[-1].payload["mode"] == "auto"


async def test_step_mode_gate_can_be_released():
    s = _session()
    s.set_mode("step")
    assert s.mode == "step"
    s.request_next()  # arms the gate
    assert s._next.is_set()


async def test_run_loop_auto_advances_then_stops():
    s = _session()
    task = asyncio.create_task(s.run(interval_s=0.001))
    assert await _wait_until(lambda: s._round > 0)  # auto mode advances on its own
    s.stop()
    await asyncio.wait_for(task, timeout=2.0)


async def test_run_loop_step_gate_holds_until_next():
    s = _session()
    s.set_mode("step")
    task = asyncio.create_task(s.run(interval_s=0.001))
    # In step mode the loop gates before the first tick, so it never advances on its own.
    await asyncio.sleep(0.05)
    assert s._round == 0
    s.request_next()
    assert await _wait_until(lambda: s._round >= 1)  # advances once Next is requested
    s.stop()
    await asyncio.wait_for(task, timeout=2.0)


async def test_metrics_frame_carries_real_social_welfare():
    s = _session()
    q = s.hub.subscribe()
    for _ in range(30):  # warm up the baseline
        await s.tick_round()
    s.send_dos("public-facing", intensity=4.0)
    for _ in range(20):  # detect -> classify -> respond
        await s.tick_round()
    metrics = [f for f in _drain(q) if f.kind == "metrics"]
    assert metrics, "expected the session to stream backend-computed metrics"
    latest = metrics[-1].payload
    # Real values from the analytics module, not the frontend's hardcoded 0 placeholders.
    assert latest["social_welfare"] > 0
    assert 0.0 <= latest["dr"] <= 1.0


async def test_packets_frame_streams_sampled_traffic():
    s = _session()
    q = s.hub.subscribe()
    s.send_dos("public-facing", intensity=4.0)
    for _ in range(5):
        await s.tick_round()
    packet_frames = [f for f in _drain(q) if f.kind == "packets"]
    assert packet_frames, "expected the session to stream sampled packets for the war-room sprites"
    sample = packet_frames[-1].payload["packets"]
    assert isinstance(sample, list) and sample
    assert {"src_ip", "kind", "segment", "ts_ms"} <= set(sample[0].keys())


async def test_bus_connected_reflects_real_bus_state():
    s = _session()
    q = s.hub.subscribe()
    await s.bus.start()
    await s.tick_round()
    status = [f for f in _drain(q) if f.kind == "connection_status"]
    assert status and status[-1].payload["bus_connected"] is True
    await s.bus.stop()
    s.emit_status()
    status = [f for f in _drain(q) if f.kind == "connection_status"]
    assert status and status[-1].payload["bus_connected"] is False  # honest, not hardcoded


async def test_metrics_window_keeps_dr_fpr_coherent():
    s = _session()
    q = s.hub.subscribe()
    for _ in range(30):  # warm up the baseline
        await s.tick_round()
    s.send_dos("public-facing", intensity=4.0, duration_ms=300)
    for _ in range(30):  # attack runs ~6 rounds, then expires — all within the metrics window
        await s.tick_round()
    reported = [
        e
        for e in s.collector.events
        if e.event_type is EventType.THREAT_CLASSIFIED and e.payload.get("reported")
    ]
    assert reported, "expected the live fleet to classify the injected DoS"
    metrics = [f for f in _drain(q) if f.kind == "metrics"]
    assert metrics
    m = metrics[-1].payload
    # The attack expired (pruned from the overlay) but is still inside the scoring window,
    # so its detections must NOT flip to false positives: no vacuous DR=100% with FPR>0.
    assert not (m["dr"] == 1.0 and m["fpr"] > 0.0)
    assert m["fpr"] == 0.0


async def test_metrics_window_drops_events_older_than_window():
    s = _session()
    now = 50_000.0
    old = EventLog(
        lamport_ts=1,
        wall_ms=now - 20_000.0,
        event_type=EventType.ALERT_PUBLISHED,
        agent_id="TMA:public-facing",
        agent_type="TMA",
    )
    recent = EventLog(
        lamport_ts=2,
        wall_ms=now - 1_000.0,
        event_type=EventType.ALERT_PUBLISHED,
        agent_id="TMA:public-facing",
        agent_type="TMA",
    )
    await s.collector.write(old)
    await s.collector.write(recent)
    windowed = s._windowed_events(now)
    assert recent in windowed
    assert old not in windowed


async def test_send_attack_injects_typed_attack_and_emits_sim_event():
    s = _session()
    q = s.hub.subscribe()
    s.send_attack("LATERAL", "public-facing", intensity=4.0)
    assert s.sim.ground_truth().is_attack(Segment.PUBLIC_FACING, s.clock.now_ms()) is True
    sim_events = [f for f in _drain(q) if f.kind == "sim_event"]
    assert any(f.payload.get("signal") == "manual_lateral" for f in sim_events)
    assert any(f.payload.get("attack_type") == "LATERAL" for f in sim_events)
    # send_dos still emits its own manual_dos signal (thin wrapper, no regression)
    s.send_dos("public-facing")
    assert any(f.payload.get("signal") == "manual_dos" for f in _drain(q) if f.kind == "sim_event")


async def test_send_attack_multi_segment_forms_coalition():
    s = LiveSession(segments=list(Segment), clock=ManualClock())
    for _ in range(30):  # warm up
        await s.tick_round()
    # Two concurrent containment attacks → TIA correlates ≥2 active segments → coalition,
    # and the high-severity lateral escalates to quarantine votes.
    s.send_attack("LATERAL", "internal", intensity=5.0, duration_ms=6000)
    s.send_attack("LATERAL", "server", intensity=5.0, duration_ms=6000)
    for _ in range(60):
        await s.tick_round()
    # Read the retained event buffer (the hub queue is small and drops the early frames).
    types = {e.event_type for e in s.collector.events}
    assert EventType.COALITION_FORMED in types  # the coordination layer now runs in live mode
    assert EventType.VOTE_CAST in types  # quarantine escalates through a coalition vote


async def test_overhead_rises_during_incident_then_recovers():
    s = _session()
    for _ in range(30):  # warm up
        await s.tick_round()
    s.send_dos("public-facing", intensity=4.0, duration_ms=600)
    peak = 0.0
    for _ in range(40):
        await s.tick_round()
        peak = max(peak, s.sim.resources.utilization())
    assert peak > 0.0  # a response allocated a real resource slot during the incident
    assert s.sim.resources.utilization() == 0.0  # released once the attack expired
    state = await s.sim.get_state()
    pf = next(x for x in state.segments if x.segment is Segment.PUBLIC_FACING)
    assert pf.active_defenses == []


async def test_topology_includes_named_hosts():
    s = _session()
    topo = s.topology()
    assert topo["hosts"]
    assert all({"hostname", "ip", "segment", "role"} <= set(h.keys()) for h in topo["hosts"])


async def test_baseline_frame_streams_per_segment():
    s = _session()
    q = s.hub.subscribe()
    for _ in range(10):
        await s.tick_round()
    baseline = [f for f in _drain(q) if f.kind == "baseline"]
    assert baseline, "expected per-segment anti-poisoning baseline frames"
    payload = baseline[-1].payload
    assert {"segment", "current", "mean", "std", "deviation"} <= set(payload.keys())
