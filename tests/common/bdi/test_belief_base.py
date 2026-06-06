from cdmas.common.bdi.belief_base import Belief, BeliefBase


def test_add_and_query():
    bb = BeliefBase()
    bb.revise(Belief(predicate="traffic_rate", value=3902, source="sim", lamport_ts=1))
    assert bb.query("traffic_rate").value == 3902
    assert bb.value("missing", default=0) == 0
    assert "traffic_rate" in bb


def test_brf_keeps_newer_lamport():
    bb = BeliefBase()
    bb.revise(Belief(predicate="rate", value=10, source="a", lamport_ts=5))
    bb.revise(Belief(predicate="rate", value=99, source="b", lamport_ts=3))  # stale -> ignored
    assert bb.query("rate").value == 10
    bb.revise(Belief(predicate="rate", value=42, source="c", lamport_ts=9))  # newer -> wins
    assert bb.query("rate").value == 42
