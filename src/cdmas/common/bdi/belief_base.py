"""Belief base and belief revision function (SDD §2.1, §5.2.1)."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Belief:
    predicate: str
    value: Any
    source: str
    lamport_ts: int = 0
    confidence: float = 1.0


class BeliefBase:
    """The agent's current knowledge, keyed by predicate."""

    def __init__(self) -> None:
        self._beliefs: dict[str, Belief] = {}

    def revise(self, belief: Belief) -> None:
        """BRF: accept a belief if it is at least as recent (Lamport) as the held one."""
        existing = self._beliefs.get(belief.predicate)
        if existing is None or belief.lamport_ts >= existing.lamport_ts:
            self._beliefs[belief.predicate] = belief

    def query(self, predicate: str) -> Belief | None:
        return self._beliefs.get(predicate)

    def value(self, predicate: str, default: Any = None) -> Any:
        belief = self._beliefs.get(predicate)
        return belief.value if belief is not None else default

    def __contains__(self, predicate: str) -> bool:
        return predicate in self._beliefs

    def __len__(self) -> int:
        return len(self._beliefs)
