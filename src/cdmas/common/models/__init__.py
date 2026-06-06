"""Typed message payloads exchanged between agents (SDD section 3.2).

Planned modules (built test-first):
    enums         — Segment, AttackType, Classification, ResponseType, ResourceType.
    alert         — Alert (TMA -> ACA).
    threat_report — ThreatReport (ACA -> RCA, TIA).
    bid           — ResourceBid (Agent -> RAA), AuctionResult.
    vote          — VoteRequest, VoteResponse (RCA <-> coalition).
    coalition     — CoalitionInvite, CoalitionRecord.
    resolution    — ResolutionNotice.
    errors        — Failure, NotUnderstood.
"""
