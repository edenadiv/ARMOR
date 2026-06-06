"""Metric collection and scenario reporting (SDD sections 7.2-7.4).

Computes the SRS metrics from the event log and produces per-scenario reports.

Planned modules (built test-first):
    metrics  — DR, FPR, MTTR(alert/response), availability, resource overhead,
               per-agent utilities, and the weighted Social Welfare score.
    reports  — ScenarioReport assembling metadata, agent utilities, system metrics,
               Social Welfare PASS/FAIL, attacker utility, and constraint violations.
"""
