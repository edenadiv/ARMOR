"""Desires: utility-ranked goals (SDD §2.1, §5.2.1)."""

from collections.abc import Callable
from dataclasses import dataclass, field

from cdmas.common.bdi.belief_base import BeliefBase


@dataclass
class Goal:
    description: str
    priority: float
    utility_fn: Callable[[BeliefBase], float] | None = None
    status: str = "active"  # active | held | queued | satisfied | dropped


@dataclass
class GoalSet:
    _goals: list[Goal] = field(default_factory=list)

    def add(self, goal: Goal) -> None:
        self._goals.append(goal)

    def drop(self, goal: Goal) -> None:
        if goal in self._goals:
            self._goals.remove(goal)

    def ranked(self) -> list[Goal]:
        """Active goals, highest priority first."""
        active = [g for g in self._goals if g.status == "active"]
        return sorted(active, key=lambda g: g.priority, reverse=True)

    def top(self) -> Goal | None:
        ranked = self.ranked()
        return ranked[0] if ranked else None
