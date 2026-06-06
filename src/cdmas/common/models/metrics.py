"""Canonical metrics snapshot (SRS §7.3).

Shared by the simulator ``/metrics`` endpoint (live, partial) and the Phase 6 analytics
layer (computed from the event log). Structurally satisfies the validator's ``Metrics``
protocol.
"""

from pydantic import BaseModel


class MetricsSnapshot(BaseModel):
    dr: float = 0.0
    fpr: float = 0.0
    mttr_alert_ms: float = 0.0
    mttr_response_ms: float = 0.0
    availability: float = 1.0
    resource_overhead: float = 0.0
    social_welfare: float = 0.0
    attacker_utility: float = 0.0
    coalition_ms: float | None = None
    evasion_rate: float | None = None
    concurrent_incidents: int = 0
