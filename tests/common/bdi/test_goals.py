from cdmas.common.bdi.goals import Goal, GoalSet


def test_top_returns_highest_priority_active_goal():
    gs = GoalSet()
    gs.add(Goal(description="minimize FPR", priority=0.3))
    gs.add(Goal(description="maximize U_ACA", priority=0.9))
    held = Goal(description="refresh model", priority=1.0, status="held")
    gs.add(held)
    assert gs.top().description == "maximize U_ACA"  # held goal excluded despite priority


def test_drop_and_ranked():
    gs = GoalSet()
    g1 = Goal(description="a", priority=0.1)
    g2 = Goal(description="b", priority=0.5)
    gs.add(g1)
    gs.add(g2)
    assert [g.description for g in gs.ranked()] == ["b", "a"]
    gs.drop(g2)
    assert gs.top().description == "a"
