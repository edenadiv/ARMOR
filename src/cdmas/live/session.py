"""LiveSession — the whole MAS in one process, streamed to the dashboard.

Wires the in-process simulator, an in-memory bus, the real agent fleet (events routed
through a HubSink), and a heartbeat monitor. Drives them in a continuous async loop with
two modes (auto-run / step), and exposes manual actions (send legal / DoS traffic) that the
real agents then detect and respond to. This is the "global vars" live source — no Kafka,
no prebaked replay.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from cdmas.agents.factory import build_all
from cdmas.agents.tma.agent import TrafficMonitorAgent
from cdmas.analytics.metrics import compute_metrics
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.logging.event_log import EventLog, EventSink
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.models.enums import AttackType, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.coordination.failure import HeartbeatMonitor
from cdmas.live.hub import (
    KIND_BASELINE,
    KIND_CONNECTION_STATUS,
    KIND_METRICS,
    KIND_PACKETS,
    KIND_SIM_EVENT,
    KIND_SIMULATION_STATE,
    EventHub,
)
from cdmas.live.sink import HubSink
from cdmas.simulator.attacks import AttackSpec
from cdmas.simulator.engine import InProcessSimulator
from cdmas.simulator.sampling import PacketSampler

_STEP_MS = 50  # sim time advanced per round
_INTERVAL_S = 0.12  # real time between rounds (playback pace)
_METRICS_WINDOW_MS = 12_000  # trailing window (sim ms) that live DR/FPR are scored over


class _EventCollector(EventSink):
    """Bounded rolling buffer of recent agent events, for live metric computation.

    Capped so a long-running live server stays memory-bounded. Wired as the HubSink's inner
    sink, so every event is both streamed to the dashboard and retained for ``compute_metrics``.
    """

    def __init__(self, maxlen: int = 4000) -> None:
        self._events: deque[EventLog] = deque(maxlen=maxlen)

    async def write(self, event: EventLog) -> None:
        self._events.append(event)

    @property
    def events(self) -> list[EventLog]:
        return list(self._events)


class LiveSession:
    def __init__(
        self,
        *,
        segments: list[Segment],
        hub: EventHub | None = None,
        clock: ManualClock | None = None,
        step_ms: int = _STEP_MS,
        seed: int = 0,
    ) -> None:
        self.hub = hub or EventHub()
        self.clock: ManualClock = clock or ManualClock()
        self.step_ms = step_ms
        self.segments = segments
        self.sampler = PacketSampler()
        self.sim = InProcessSimulator(
            clock=self.clock, segments=segments, seed=seed, sampler=self.sampler
        )
        self.bus = InMemoryBus()
        self.collector = _EventCollector()
        self.sink = HubSink(self.hub, inner=self.collector)
        self.agents: list[BaseAgent] = build_all(
            segments, self.bus, self.sim, self.sink, self.clock
        )
        for agent in self.agents:
            agent.setup()
        self.monitor = HeartbeatMonitor()
        self.mode = "auto"
        self.awaiting_next = False
        self._next = asyncio.Event()
        self._running = False
        self._round = 0
        self._active_attacks: set[Segment] = set()  # segments with a live attack (for release)

    # --- control -----------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        self.mode = "step" if mode == "step" else "auto"
        if self.mode == "auto":
            self._next.set()  # release any pending step gate

    def request_next(self) -> None:
        self._next.set()

    def stop(self) -> None:
        self._running = False
        self._next.set()

    # --- manual actions ----------------------------------------------------
    def send_dos(self, segment: str, intensity: float = 3.0, duration_ms: int = 3000) -> None:
        # Bounded burst: the attack subsides after duration_ms so the segment recovers
        # (an unbounded attack would flood the segment forever).
        now = self.clock.now_ms()
        self.sim.inject(
            AttackSpec(
                type=AttackType.DDOS,
                segment=Segment(segment),
                intensity=intensity,
                start_ms=now,
                duration_ms=duration_ms,
            )
        )
        self.hub.publish(
            KIND_SIM_EVENT,
            {
                "signal": "manual_dos",
                "segment": segment,
                "attack_type": "DDOS",
                "intensity": intensity,
                "duration_ms": duration_ms,
            },
            ts_ms=now,
        )

    def send_attack(
        self, attack_type: str, segment: str, intensity: float = 3.0, duration_ms: int = 3000
    ) -> None:
        # Inject any typed bounded attack and announce it so the UI shows the matching flow.
        # Lets the live demo drive lateral/zero-day (which escalate to quarantine votes and
        # TIA coalitions), not just DoS. Unknown type/segment strings raise ValueError.
        now = self.clock.now_ms()
        self.sim.inject(
            AttackSpec(
                type=AttackType(attack_type),
                segment=Segment(segment),
                intensity=intensity,
                start_ms=now,
                duration_ms=duration_ms,
            )
        )
        self.hub.publish(
            KIND_SIM_EVENT,
            {
                "signal": f"manual_{attack_type.lower()}",
                "segment": segment,
                "attack_type": attack_type,
                "intensity": intensity,
                "duration_ms": duration_ms,
            },
            ts_ms=now,
        )

    def send_legal(self, segment: str, volume: float = 1.0) -> None:
        # Legal traffic is the always-on baseline; announce a pulse so the UI can show
        # green flow without tripping any alert (no attack is injected).
        now = self.clock.now_ms()
        self.hub.publish(
            KIND_SIM_EVENT,
            {"signal": "manual_legal", "segment": segment, "volume": volume},
            ts_ms=now,
        )

    # --- run loop ----------------------------------------------------------
    def topology(self) -> dict[str, Any]:
        return {
            "segments": [s.value for s in self.segments],
            "adjacency": self.sim.topology.adjacency_view(),
            "hosts": self.sim.hosts.to_view(self.segments),
        }

    def emit_status(self) -> None:
        self._emit_status(self.clock.now_ms())

    def _release_expired_segments(self) -> None:
        # When a manual attack ends, release its segment's reserved resources and lift its
        # defenses so overhead falls and the segment recovers. Live-only: the validator runs
        # fixed-length scenarios and never calls this, so its overhead holds a bounded steady
        # state. `active(now)` is time-based, so a just-expired spec is no longer "active".
        active = {spec.segment for spec in self.sim.injector.active(self.clock.now_ms())}
        for seg in self._active_attacks - active:
            self.sim.release_segment(seg)
        self._active_attacks = active

    async def tick_round(self) -> None:
        self.sim.tick()
        # Spread the agents across the round (sub-step the clock between them) so the
        # detect -> classify -> respond chain gets realistic, non-zero latencies. The
        # round's total advance is unchanged, so deadlines/cooldowns behave as before.
        sub = self.step_ms / max(1, len(self.agents))
        for agent in self.agents:
            await agent.step()
            self.monitor.beat(agent.agent_id, self.clock.now_ms())
            self.clock.advance(sub)
        self._release_expired_segments()  # free resources/defenses for attacks that just ended
        self._round += 1
        self._emit_status(self.clock.now_ms())
        self._emit_metrics_and_packets(self.clock.now_ms())

    def _emit_status(self, now: float) -> None:
        failed = set(self.monitor.failed(now))
        connected = sum(1 for a in self.agents if a.agent_id not in failed)
        self.hub.publish(
            KIND_CONNECTION_STATUS,
            {
                "agents_connected": connected,
                "agents_total": len(self.agents),
                "bus_connected": self.bus.running,
                "stream_connected": self.hub.subscribers > 0,
            },
            ts_ms=now,
        )
        self.hub.publish(
            KIND_SIMULATION_STATE,
            {
                "mode": self.mode,
                "paused": not self._running,
                "awaiting_next": self.awaiting_next,
                "round": self._round,
            },
            ts_ms=now,
        )

    def _windowed_events(self, now: float) -> list[EventLog]:
        """Events within the trailing scoring window — keeps DR/FPR a coherent 'recent' figure."""
        floor = now - _METRICS_WINDOW_MS
        return [e for e in self.collector.events if e.wall_ms >= floor]

    def _emit_metrics_and_packets(self, now: float) -> None:
        # Real metrics from the analytics module (SW, DR, FPR, attacker utility) — the dashboard
        # no longer has to fake these. We have the in-process ground truth right here.
        # Score events and ground truth over the SAME trailing window: prune attacks at the
        # window floor (not at expiry) so a just-expired attack is still scored against its own
        # detections — otherwise DR resets to a vacuous 100% while those detections look like
        # false positives. `active(now)` still yields no packets for an expired spec (so the
        # overlay/recovery is unchanged), and pruning past the window bounds memory.
        self.sim.injector.prune_expired(now - _METRICS_WINDOW_MS)
        events = self._windowed_events(now)
        if events:
            metrics = compute_metrics(
                events,
                self.sim.ground_truth(),
                segment_count=len(self.segments),
                total_time_ms=max(now, 1.0),
            )
            self.hub.publish(KIND_METRICS, metrics.model_dump(mode="json"), ts_ms=now)
        # This round's representative packet sample feeds the war-room sprites; reset so the
        # next round captures fresh traffic (and the sampler stays bounded on long runs).
        packets = self.sampler.export()
        if packets:
            self.hub.publish(KIND_PACKETS, {"packets": packets}, ts_ms=now)
        self.sampler.reset()
        # Per-segment anti-poisoning baseline (current vs mean +/- std), emitted every round —
        # even during an attack — so the readout shows current spiking while the band holds.
        for agent in self.agents:
            if isinstance(agent, TrafficMonitorAgent):
                self.hub.publish(KIND_BASELINE, agent.baseline_snapshot(), ts_ms=now)

    async def run(self, *, interval_s: float = _INTERVAL_S) -> None:
        self._running = True
        await self.bus.start()  # bus_connected now reflects this real state
        try:
            self._emit_status(self.clock.now_ms())
            while self._running:
                if self.mode == "step":
                    self.awaiting_next = True
                    self._emit_status(self.clock.now_ms())
                    await self._next.wait()
                    self._next.clear()
                    self.awaiting_next = False
                    if not self._running:
                        break
                await self.tick_round()  # tick_round advances the clock by one full round
                await asyncio.sleep(interval_s)
        finally:
            await self.bus.stop()
