from cdmas.common.bdi.belief_base import Belief, BeliefBase
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Intention, Plan


def test_applicable_requires_trigger_and_precondition():
    bb = BeliefBase()
    bb.revise(Belief(predicate="anomaly", value=True, source="self", lamport_ts=1))

    async def body(agent):
        return "done"

    plan = Plan(
        plan_id="detect_anomaly",
        trigger=lambda b: b.value("anomaly") is True,
        precondition=lambda b: True,
        body=body,
        deadline_ms=100,
    )
    assert plan.applicable(bb) is True

    bb.revise(Belief(predicate="anomaly", value=False, source="self", lamport_ts=2))
    assert plan.applicable(bb) is False


def test_intention_binds_goal_and_plan():
    async def body(agent):
        return None

    plan = Plan(plan_id="p", trigger=lambda b: True, precondition=lambda b: True, body=body)
    goal = Goal(description="g", priority=1.0)
    intent = Intention(goal=goal, plan=plan, started_at=5)
    assert intent.plan.plan_id == "p"
    assert intent.started_at == 5
