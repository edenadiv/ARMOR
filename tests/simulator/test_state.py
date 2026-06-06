from cdmas.common.models.enums import ResponseType, Segment
from cdmas.simulator.models import ActionRequest
from cdmas.simulator.state import NORMAL, UNDER_ATTACK, StateManager
from cdmas.simulator.topology import NetworkTopology


def _sm() -> StateManager:
    return StateManager(NetworkTopology())


def test_health_transitions():
    sm = _sm()
    assert sm.health(Segment.SERVER) == NORMAL
    sm.mark_under_attack(Segment.SERVER)
    assert sm.health(Segment.SERVER) == UNDER_ATTACK


def test_throttle_records_defense():
    sm = _sm()
    r = sm.apply_action(ActionRequest(type=ResponseType.THROTTLE, segment=Segment.PUBLIC_FACING))
    assert r.accepted and r.effectiveness > 0
    assert "THROTTLE" in sm.active_defenses(Segment.PUBLIC_FACING)


def test_quarantine_isolates_segment():
    sm = _sm()
    sm.mark_under_attack(Segment.SERVER)
    sm.apply_action(ActionRequest(type=ResponseType.QUARANTINE, segment=Segment.SERVER))
    assert sm.is_quarantined(Segment.SERVER)
    # A quarantined segment cannot be re-marked under attack.
    sm.mark_under_attack(Segment.SERVER)
    assert sm.health(Segment.SERVER) == NORMAL
