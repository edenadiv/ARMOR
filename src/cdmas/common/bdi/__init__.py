"""BDI (Belief-Desire-Intention) cognitive core.

Every agent inherits from ``BaseAgent``, which runs the continuous
``perceive -> reason -> act`` loop, emits heartbeats, integrates with the message bus,
and logs a strategy trace for every decision.

Planned modules (built test-first, see the Foundations plan):
    belief_base — BeliefBase, Belief, belief revision function (BRF).
    goals       — GoalSet, Goal (utility-ranked desires).
    plan        — Plan (trigger, precondition, body), Intention.
    base_agent  — BaseAgent abstract class wiring it all together.
"""
