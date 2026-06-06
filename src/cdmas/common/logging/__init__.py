"""Structured JSON event logging (SDD section 7.1).

Every agent decision, inter-agent message, and environment state change is recorded to a
persistent event store, enabling real-time visualization and post-run validation.

Planned modules (built test-first):
    event_log — EventLog model (event_id, lamport_ts, event_type, agent, payload,
                latency_ms, decision_trace) + sinks (in-memory, structlog, PostgreSQL).
"""
