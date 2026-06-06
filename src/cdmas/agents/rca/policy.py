"""Proportional response selection (SDD §4.1, Figure 6).

Pick the least-disruptive action that is still effective against a threat of severity S.
"""

from __future__ import annotations

from dataclasses import dataclass

from cdmas.common.models.enums import ResponseType


@dataclass(frozen=True)
class ResponseAction:
    type: ResponseType
    effectiveness_threshold: float  # effective for threats with severity >= this
    disruption_score: float  # 0 = harmless, 1 = maximally disruptive


# Candidate actions (MONITOR is the fallback, not a candidate).
DEFAULT_ACTIONS: tuple[ResponseAction, ...] = (
    ResponseAction(ResponseType.THROTTLE, 0.3, 0.2),
    ResponseAction(ResponseType.BLOCK, 0.5, 0.5),
    ResponseAction(ResponseType.REDEPLOY, 0.6, 0.6),
    ResponseAction(ResponseType.QUARANTINE, 0.7, 0.9),
)

_MONITOR = ResponseAction(ResponseType.MONITOR, 0.0, 0.0)


def select_proportional_action(
    severity: float, actions: tuple[ResponseAction, ...] = DEFAULT_ACTIONS
) -> ResponseAction:
    candidates = [a for a in actions if a.effectiveness_threshold <= severity]
    if not candidates:
        return _MONITOR
    return min(candidates, key=lambda a: a.disruption_score)


def proportionality_score(action: ResponseAction) -> float:
    """Higher = more proportional (less disruptive). Always >= 0.7 for the catalog."""
    return round(1.0 - 0.3 * action.disruption_score, 3)
