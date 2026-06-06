"""Token authentication and per-agent token-bucket rate limiting (FR-23 edge)."""

from __future__ import annotations

from dataclasses import dataclass

from cdmas.common.timing.clock import Clock, WallClock


@dataclass
class _Bucket:
    tokens: float
    last_ms: float


class RateLimiter:
    """Per-key token bucket. Enforces the per-agent request cap at the API edge."""

    def __init__(
        self, *, rate_per_s: float = 50.0, burst: float = 50.0, clock: Clock | None = None
    ) -> None:
        self.rate = rate_per_s
        self.burst = burst
        self.clock = clock or WallClock()
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, key: str) -> bool:
        now = self.clock.now_ms()
        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = _Bucket(tokens=self.burst - 1, last_ms=now)
            return True
        elapsed_s = (now - bucket.last_ms) / 1000.0
        bucket.tokens = min(self.burst, bucket.tokens + elapsed_s * self.rate)
        bucket.last_ms = now
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True
        return False


def token_ok(authorization: str | None, expected: str) -> bool:
    return authorization == f"Bearer {expected}"
