"""Shared building blocks reused by every service.

Submodules:
    bdi       — BaseAgent and the Belief/Desire/Intention cognitive core.
    messaging — FIPA-ACL message schema, the pub/sub bus client, Lamport clocks, topics.
    models    — typed message payloads (Alert, ThreatReport, Bid, Vote, ...).
    logging   — structured JSON event log used for visualization and the validator.
"""
