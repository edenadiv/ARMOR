"""Inter-agent communication: FIPA-ACL over a publish-subscribe bus.

Planned modules (built test-first, see the Foundations plan):
    acl      — ACLMessage envelope (performative, sender, receiver, topic, content),
               schema validation, FAILURE / NOT-UNDERSTOOD error replies.
    topics   — the topic registry (alerts, threat-reports, threat-intel, resource-bids,
               resource-grants, coalition, votes, resolution) and publisher/subscriber map.
    lamport  — Lamport logical clock for total message ordering with deterministic ties.
    bus      — async pub/sub client (Kafka-backed in prod, in-memory for tests) with
               per-topic FIFO delivery, idempotent dedup, and deadline-bounded waits.
"""
