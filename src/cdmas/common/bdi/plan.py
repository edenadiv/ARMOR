"""Plans and intentions (SDD §2.1, §5.2.1).

A Plan is a conditional recipe: (trigger, precondition, body). An Intention is a
committed (goal, plan) pair the agent is currently executing.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cdmas.common.bdi.belief_base import BeliefBase
from cdmas.common.bdi.goals import Goal

if TYPE_CHECKING:
    from cdmas.common.bdi.base_agent import BaseAgent

Predicate = Callable[[BeliefBase], bool]
PlanBody = Callable[["BaseAgent"], Awaitable[Any]]


@dataclass
class Plan:
    plan_id: str
    trigger: Predicate
    precondition: Predicate
    body: PlanBody
    deadline_ms: int | None = None

    def applicable(self, beliefs: BeliefBase) -> bool:
        return self.trigger(beliefs) and self.precondition(beliefs)


@dataclass
class Intention:
    goal: Goal
    plan: Plan
    started_at: int  # Lamport timestamp at commitment
