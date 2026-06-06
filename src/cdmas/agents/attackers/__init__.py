"""Simulated adversary agents that stress-test the defense coalition.

Modeled as the attacker side of a two-player zero-sum game (SDD 2.7, SRS 6.5):
    DDoSAttacker          — floods a segment, randomized source IPs (botnet emulation).
    PortScanner           — pseudo-random scan order to avoid fixed signatures.
    LateralMovementAgent  — quiet host-to-host movement after a breach.
    ZeroDayEmulator       — traffic matching no known signature (tests novelty detection).
"""
