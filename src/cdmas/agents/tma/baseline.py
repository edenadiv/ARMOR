"""Rolling traffic baseline: mean + std over a recent window (FR-02)."""

from __future__ import annotations

from collections import deque

import numpy as np


class RollingBaseline:
    def __init__(self, window: int = 60, warmup: int = 5) -> None:
        self._w: deque[float] = deque(maxlen=window)
        self.warmup = warmup

    def _clean(self) -> list[float]:
        """The oldest 50% of history, excluding the most-recent sample (anti-poisoning).

        An ongoing attack floods the *recent* end of the window, so reading the baseline
        from the oldest half keeps mean/std anchored to pre-attack traffic — an attack must
        run for more than half the window before it can shift its own detection threshold.
        """
        w = list(self._w)
        hist = w[:-1] if len(w) > 1 else w
        cutoff = max(self.warmup, len(hist) // 2)
        return hist[:cutoff]

    @property
    def mean(self) -> float:
        clean = self._clean()
        return float(np.mean(clean)) if clean else 0.0

    @property
    def std(self) -> float:
        clean = self._clean()
        return float(np.std(clean)) if len(clean) > 1 else 0.0

    def update(self, x: float) -> None:
        self._w.append(x)

    def deviation(self, x: float) -> float:
        """Deviation of ``x`` from the baseline in standard deviations."""
        if len(self._w) < self.warmup or self.std == 0.0:
            return 0.0
        return (x - self.mean) / self.std
