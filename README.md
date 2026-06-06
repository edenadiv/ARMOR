# Collaborative Cyber-Defense Multi-Agent System (CDMAS)

A decentralized **Multi-Agent System (MAS)** for automated cyber-defense and incident
response, validated inside a simulated four-segment corporate network. Autonomous
**BDI (Belief–Desire–Intention)** agents collaboratively monitor, detect, classify, and
respond to attacks with a target **Mean Time to Respond (MTTR) < 1 second**.

> ⚠️ **This is a simulation and validation platform, not a live network appliance.**
> Every "attacker" is a simulated agent. The system models a cyber-defense layer and
> proves, via an automated constraint checker, that it meets a set of quantitative
> performance targets defined in the SRS.

See the source specifications in [`docs/`](docs/):
- `srs_cyber_defence_multi_agent_systems_2026.pdf` — Software Requirements Specification
- `SDD_Cyber_Defense_MAS-6 2.pdf` — Software Design Document

---

## The agents

**5 defense agent types**, each a BDI agent running a `perceive → reason → act` loop:

| Agent | Role | Headline responsibility |
|-------|------|-------------------------|
| **TMA** – Traffic Monitor      | The eyes          | Sample traffic ≥10×/s, flag >2σ anomalies, alert < 100 ms |
| **ACA** – Anomaly Classifier   | The analyst       | ML-classify alerts < 200 ms, severity 0–1, online learning, FPR < 10% |
| **RCA** – Response Coordinator | Incident commander| Proportional response < 500 ms, vote before quarantine |
| **TIA** – Threat Intelligence  | Memory / broker   | Cross-segment correlation, coalition triggering |
| **RAA** – Resource Allocator   | Logistics         | Sealed-bid auction, host overhead < 40% |

**4 attacker agent types** for stress-testing: DDoS, Port Scanner, Lateral Movement,
Zero-Day Emulator (modeled as a two-player zero-sum game vs. the defense coalition).

## Coordination mechanisms

1. **Publish-Subscribe bus** (FIPA-ACL messages, Lamport clocks, idempotent dedup)
2. **Coalition formation** (multi-segment threats)
3. **Auction-based resource allocation** (sealed-bid, first-price)
4. **Voting-based escalation** (>50% majority for quarantine)

## Mandatory targets (asserted by the validator)

| Metric | Target |
|--------|--------|
| Detection Rate | > 90% |
| False Positive Rate | < 8–10% |
| MTTR (alert) | < 100 ms |
| MTTR (response) | < 1000 ms |
| System Availability | > 99% |
| Resource Overhead | < 40% of host |
| Social Welfare | ≥ 0.80 |

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Agent runtime | Python 3.11 + `asyncio` |
| Message bus | Apache Kafka (`aiokafka`) |
| ML / classification | scikit-learn, numpy |
| Simulation API | FastAPI + Uvicorn |
| Visualization backend | FastAPI + WebSocket |
| Visualization frontend | React + D3.js + Recharts (Vite) |
| Logging / analytics | structlog → PostgreSQL |
| Orchestration | Docker Compose |

## Repository layout

```
.
├── docs/                      # Specs (SRS, SDD) + implementation plans
│   └── superpowers/plans/     # Phase-by-phase implementation plans
├── src/cdmas/                 # Python monorepo package
│   ├── common/                # Shared: BDI core, messaging, models, logging
│   │   ├── bdi/               # BaseAgent, BeliefBase, GoalSet, Plan, Intention
│   │   ├── messaging/         # FIPA-ACL schema, bus client, Lamport clock, topics
│   │   ├── models/            # Message payloads (Alert, ThreatReport, Bid, Vote, ...)
│   │   └── logging/           # Structured event log
│   ├── agents/                # The five defense agents + attackers
│   ├── simulator/             # FastAPI network simulation engine
│   ├── validator/             # Constraint checker + scenario runner
│   └── analytics/             # Metric collection + scenario reports
├── frontend/                  # React dashboard (3 pages: Dashboard, Inspector, Validator)
├── deploy/dockerfiles/        # Per-service Dockerfiles
├── tests/                     # Pytest suite (mirrors src/cdmas)
├── docker-compose.yml         # Full system orchestration
├── pyproject.toml             # Python package + dependencies
└── Makefile                   # Common dev commands
```

---

## Quick start

> Implementation is in progress — see the plans in `docs/superpowers/plans/`.

```bash
# Local dev (Python)
make install          # create venv + install package with dev extras
make test             # run the pytest suite
make lint             # ruff + mypy

# Full system
docker compose up --build
```

## Development

This project is built **test-first (TDD)** following the plans in
`docs/superpowers/plans/`. Each subsystem plan produces working, tested software on its
own. Build order: Foundations → Simulator → Defense Agents → Coordination → Attackers →
Observability → Dashboard → Validation.
