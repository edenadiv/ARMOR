"""Synthetic traffic generator: seeded Gaussian baseline per segment (SDD §6.1.1)."""

from __future__ import annotations

import numpy as np

from cdmas.common.models.enums import Segment
from cdmas.simulator.hosts import HostRegistry
from cdmas.simulator.packet import Packet

# Default per-segment baseline (mean, std) in packets/sec.
_DEFAULT_BASELINES: dict[Segment, tuple[float, float]] = {
    Segment.INTERNAL: (300.0, 40.0),
    Segment.SERVER: (500.0, 60.0),
    Segment.PUBLIC_FACING: (800.0, 80.0),
    Segment.SEC_MON: (150.0, 20.0),
}


class TrafficGenerator:
    """Produces realistic packet-level data per segment. Seeded for determinism."""

    def __init__(
        self,
        *,
        seed: int = 0,
        baselines: dict[Segment, tuple[float, float]] | None = None,
        registry: HostRegistry | None = None,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self.baselines = baselines if baselines is not None else dict(_DEFAULT_BASELINES)
        self.registry = registry or HostRegistry()

    def baseline(self, segment: Segment) -> tuple[float, float]:
        return self.baselines.get(segment, (400.0, 50.0))

    def sample(self, segment: Segment, n: int, ts_ms: float = 0.0) -> list[Packet]:
        mean, std = self.baseline(segment)
        freqs = self._rng.normal(mean, std, n)
        octets = self._rng.integers(2, 254, n)
        idx = list(Segment).index(segment)
        seg = segment.value
        # src stays the diverse synthetic client IP (unique-src COUNT is an ACA feature, so it
        # must not change); only dst becomes a named server. The frontend resolves both ends to
        # devices for the Packet-Tracer view. Feature-neutral -> detection/scoring unchanged.
        return [
            Packet(
                src_ip=f"10.{idx}.0.{int(o)}",
                dst_ip=self.registry.target_for(seg, int(o)),
                port=443,
                protocol="TCP",
                pkt_size=512,
                freq=float(max(0.0, f)),
                ts_ms=ts_ms,
            )
            for f, o in zip(freqs, octets, strict=True)
        ]
