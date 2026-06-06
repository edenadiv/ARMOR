# CDMAS Master Implementation Roadmap

**Goal:** Build the full Collaborative Cyber-Defense Multi-Agent System — all five
defense agents, four attacker agents, four coordination protocols, the network
simulator, the visualization dashboard, and the validation harness — to production
quality, passing all six SRS validation scenarios.

**Source specs:** `docs/srs_cyber_defence_multi_agent_systems_2026.pdf` (SRS, the *what*)
and `docs/SDD_Cyber_Defense_MAS-6 2.pdf` (SDD, the *how*).

**Tech stack (exactly as the SDD prescribes):** Python 3.11 + asyncio, Apache Kafka
(`aiokafka`), scikit-learn + numpy, FastAPI + Uvicorn + WebSocket, React + D3.js +
Recharts (Vite), structlog → PostgreSQL, Docker Compose.

---

## Why this is split into 8 plans

The system spans eight subsystems with clear boundaries. Each gets its own detailed,
test-first plan that produces **working, independently testable software**. They are
built in dependency order. A detailed plan for each phase is written *when that phase
starts* — later phases depend on interfaces and decisions finalized while building
earlier ones, so writing all eight in full up front would bake in guesses.

This roadmap is the index and the contract between phases: it fixes the build order, the
dependency edges, and the "definition of done" for each subsystem.

---

## Build order & dependency graph

```
Phase 1: Foundations ─────────────┐
  (BDI core, FIPA-ACL, bus,        │ everything depends on this
   models, event log, config)      │
                                    ▼
Phase 2: Simulator ────────► Phase 3: Defense Agents ────► Phase 4: Coordination
  (topology, traffic,          (TMA, ACA, RCA, TIA, RAA      (pub/sub wiring, auction,
   attack injector, clock,      as BDI agents against         coalition, voting,
   state, REST + WS API)        the sim API)                  failure/resilience)
                                    │                              │
                                    ▼                              ▼
                              Phase 5: Attackers ──────────► Phase 6: Observability
                                (DDoS, scan, lateral,          (metric collection,
                                 zero-day adversaries)          scenario reports)
                                    │                              │
                                    └──────────────┬───────────────┘
                                                   ▼
                          Phase 7: Dashboard          Phase 8: Validation
                            (React: Dashboard,          (constraint checker for
                             Inspector, Validator        FR-01..FR-34, scenario
                             pages over WS/REST)         runner, 6 scenarios green)
```

Phases 5–6 can proceed in parallel once Phase 4 lands. Phase 7 (dashboard) only needs
Phases 1–2 and the event-log shape from Phase 6; Phase 8 (validation) needs all backend
phases and is the final acceptance gate.

---

## Phase 1 — Foundations  ⟶ `2026-06-06-phase-1-foundations.md` (written, ready to execute)

The shared substrate every other phase imports. No agent logic yet — just the BDI
machinery, the message layer, typed payloads, the event log, and config.

**Delivers:**
- `common/bdi`: `BeliefBase` + `Belief` + belief-revision function; `GoalSet` + `Goal`;
  `Plan` + `Intention`; `BaseAgent` abstract perceive→reason→act loop with heartbeat.
- `common/messaging`: `ACLMessage` envelope + schema validation; topic registry;
  `LamportClock`; async `MessageBus` (in-memory impl + Kafka impl behind one interface)
  with per-topic FIFO, idempotent dedup, deadline-bounded waits, FAILURE/NOT-UNDERSTOOD.
- `common/models`: all enums + payloads (Alert, ThreatReport, ResourceBid, AuctionResult,
  VoteRequest/Response, Coalition*, ResolutionNotice, Failure, NotUnderstood).
- `common/logging`: `EventLog` record + in-memory and structlog sinks.
- `common/config`: pydantic-settings reading `CDMAS_*`.

**Definition of done:** `pytest` green; a demo test wires two `BaseAgent` subclasses
through the in-memory bus and shows ordered, deduplicated, deadline-bounded delivery.
**Covers SRS:** FR-32 (schema + reject malformed); SDD §2, §3.1, §3.2, §5.2, §7.1.

---

## Phase 2 — Simulator  ⟶ `phase-2-simulator.md` (write at phase start)

Standalone FastAPI service modeling the 4-segment network so agents have an environment.

**Delivers:** `NetworkTopology` (4 segments + lateral adjacency), `TrafficGenerator`
(Gaussian baseline, configurable PPS), `AttackInjector` (DDoS/scan/lateral/zero-day),
`SimClock` (real-time…10×), `StateManager`, and the REST API (`/packets/{segment}`,
`/action`, `/topology`, `/state`, `/metrics`, `/inject-attack`) + WebSocket state feed,
token-authed and per-agent rate-limited.
**Definition of done:** API integration tests; `docker compose up simulator` serves
live synthetic traffic and accepts injected attacks. **Covers SRS:** §5.1, FR-23 cap
enforcement hook. **Depends on:** Phase 1 (models, config, event log).

---

## Phase 3 — Defense Agents  ⟶ `phase-3-defense-agents.md` (write at phase start)

The five BDI agents, each as its own package + container entrypoint, running against the
simulator but not yet coordinating beyond raw pub/sub.

**Delivers (one sub-plan section per agent, TDD):**
- **TMA** — sample ≥10×/s, rolling baseline, >2σ detect, alert <100 ms (FR-01..04).
- **ACA** — scikit-learn classifier, severity 0–1, threat report <200 ms, FPR<10%,
  online learning, DBSCAN novelty (FR-05..09).
- **RCA** — proportional `select_proportional_action`, response <500 ms (FR-10,12,13,14).
- **TIA** — global threat map ≤500 ms, multi-segment correlation <1 s, priority list
  (FR-15..18).
- **RAA** — sealed-bid auction <300 ms, notify <100 ms, reclaim <500 ms, <40% overhead
  (FR-19..23).

**Definition of done:** each agent's unit tests green against its FRs; single-agent
end-to-end (TMA→ACA→RCA) detect-classify-respond works on the in-memory bus.
**Depends on:** Phases 1–2.

---

## Phase 4 — Coordination  ⟶ `phase-4-coordination.md` (write at phase start)

The four MAS mechanisms that turn five agents into a coordinated system.

**Delivers:** pub/sub topic wiring end-to-end; **Auction** (FR-19..22, SDD §4.2);
**Coalition formation** (FR-16,17, SDD §4.3); **Voting-based quarantine escalation**
(FR-11, SDD §4.4, 300 ms deadline, majority rule, BLOCK fallback); **Agent
failure & resilience** (FR-34, SDD §4.5, heartbeat loss → reassign <2 s).
**Definition of done:** integration tests for each protocol incl. timeout/edge cases;
multi-agent scenario forms a coalition and resolves a multi-segment incident.
**Depends on:** Phases 1–3.

---

## Phase 5 — Attackers  ⟶ `phase-5-attackers.md` (write at phase start)

The four adversary agents driving realistic attack patterns through the injector.

**Delivers:** `DDoSAttacker` (randomized source IPs, FR-24), `PortScanner` (pseudo-random
order, FR-25), `LateralMovementAgent`, `ZeroDayEmulator` (no-signature traffic, FR-26);
attacker utility `U_ATK`; coordinated multi-attacker scheduling (FR-27,28).
**Definition of done:** each attacker's behavior verified; a defense run measurably
detects/mitigates each. **Depends on:** Phases 1–2 (3–4 to measure defense response).

---

## Phase 6 — Observability  ⟶ `phase-6-observability.md` (write at phase start)

Turn the event log into the metrics the SRS grades on.

**Delivers:** PostgreSQL event-log sink; `analytics/metrics` (DR, FPR, MTTR_alert,
MTTR_response, availability, resource overhead, per-agent utilities U_TMA..U_TIA, and the
weighted Social Welfare SW); `analytics/reports` (ScenarioReport).
**Definition of done:** metrics computed from a recorded log match hand-computed
fixtures; SW weights match SRS §7.2. **Covers SRS:** §7. **Depends on:** Phases 1, 3–5.

---

## Phase 7 — Dashboard  ⟶ `phase-7-dashboard.md` (write at phase start)

The React visualization (SDD §6.2) over the simulator's WebSocket + REST.

**Delivers:** **Dashboard page** (topology, message-flow & coalition overlay, alert feed,
live metrics vs targets, resource panel); **Agent Inspector** (live BDI: intention,
beliefs+confidence, ranked desires, strategy trace); **Validator page** (replay +
per-FR pass/fail + incident chain).
**Definition of done:** component tests pass; pages render live data from a running
backend. **Depends on:** Phases 1–2, 6 (event/metric shapes).

---

## Phase 8 — Validation  ⟶ `phase-8-validation.md` (write at phase start)

The acceptance gate: prove the system meets the spec.

**Delivers:** `validator/constraints` (one assertion per FR-01..34), `validator/scenarios`
(the six SRS scenarios + success criteria), `validator/runner` (inject → run → collect →
assert). CI target running all six scenarios.
**Definition of done:** all six scenarios PASS with SW ≥ 0.80 and the documented
per-scenario defense/attacker criteria met; constraint checker reports FR coverage.
**Covers SRS:** §8 entirely. **Depends on:** all prior phases.

---

## Cross-cutting conventions (apply to every phase)

- **TDD always** — failing test → minimal code → green → commit. Bite-sized steps.
- **One responsibility per file**; files that change together live together.
- **Frequent commits** with conventional-commit messages.
- **Every timing requirement is a test** — deadlines (100/200/300/500/1000 ms) are
  asserted, not assumed. Use a controllable clock so timing tests are deterministic.
- **Traceability** — every task notes the FR(s) and SDD section it implements.
- **No agent-to-agent direct calls** — all communication goes through the bus (SDD §5.3).
