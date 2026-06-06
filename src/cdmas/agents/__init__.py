"""The defense and attacker agents.

Each agent subclasses ``cdmas.common.bdi.BaseAgent`` and supplies its own beliefs,
desires, and plan library.

Planned packages (one per agent type, built test-first):
    tma        — Traffic Monitor Agent.
    aca        — Anomaly Classifier Agent (scikit-learn online learner).
    rca        — Response Coordinator Agent (proportional response, voting).
    tia        — Threat Intelligence Agent (correlation, coalition triggering).
    raa        — Resource Allocator Agent (sealed-bid auction).
    attackers  — DDoS, PortScanner, LateralMovement, ZeroDay adversaries.
"""
