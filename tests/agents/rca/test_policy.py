from cdmas.agents.rca.policy import (
    proportionality_score,
    select_proportional_action,
)
from cdmas.common.models.enums import ResponseType


def test_low_severity_returns_monitor():
    assert select_proportional_action(0.1).type is ResponseType.MONITOR


def test_picks_least_disruptive_effective_action():
    # severity 0.9: all actions effective -> least disruptive (THROTTLE) chosen.
    assert select_proportional_action(0.9).type is ResponseType.THROTTLE
    # severity 0.55: THROTTLE + BLOCK effective -> THROTTLE.
    assert select_proportional_action(0.55).type is ResponseType.THROTTLE


def test_proportionality_always_above_threshold():
    for sev in (0.0, 0.3, 0.5, 0.7, 0.9, 1.0):
        action = select_proportional_action(sev)
        assert proportionality_score(action) >= 0.7
