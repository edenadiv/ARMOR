"""Network simulation engine (SDD section 6.1).

A standalone FastAPI service that models the four-segment network, generates synthetic
traffic, injects attack scenarios, and exposes a REST API consumed by agents and the
dashboard.

Planned modules (built test-first):
    topology        — NetworkTopology: 4-segment graph + lateral-movement adjacency.
    traffic         — TrafficGenerator: Gaussian-noise packet streams at configurable PPS.
    attack_injector — AttackInjector: DDoS / port-scan / lateral / zero-day patterns.
    clock           — SimClock: real-time .. 10x accelerated, normalized timestamps.
    state           — StateManager: segment health, active defenses, resource utilization.
    api             — FastAPI app: /packets, /action, /topology, /state, /metrics,
                      /inject-attack + WebSocket state feed.
"""
