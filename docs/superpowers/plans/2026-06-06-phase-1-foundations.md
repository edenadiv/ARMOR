# Phase 1: Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared substrate every CDMAS service imports — the BDI cognitive core, the FIPA-ACL message layer with a pub/sub bus, typed message payloads, the structured event log, and runtime config — all test-first.

**Architecture:** A single installable package `cdmas` (src layout). `common/` holds reusable parts: `models` (Pydantic payloads + enums), `messaging` (ACL envelope, Lamport clock, topic registry, async bus with an in-memory implementation behind an abstract interface), `bdi` (BeliefBase, GoalSet, Plan/Intention, the `BaseAgent` perceive→reason→act loop), `logging` (event log + sinks), and `config`. No agent business logic yet — that's Phase 3.

**Tech Stack:** Python 3.11, asyncio, pydantic v2, pydantic-settings, structlog, pytest + pytest-asyncio.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/cdmas/common/config.py` | `Settings` (pydantic-settings, `CDMAS_*` env) + `get_settings()` |
| `src/cdmas/common/models/enums.py` | `Segment`, `Performative`, `AttackType`, `Classification`, `ResponseType`, `ResourceType`, `VoteDecision` |
| `src/cdmas/common/models/alert.py` | `Alert` payload (TMA→ACA) |
| `src/cdmas/common/models/threat_report.py` | `ThreatReport` payload (ACA→RCA,TIA) |
| `src/cdmas/common/models/bid.py` | `ResourceBid`, `AuctionResult` |
| `src/cdmas/common/models/vote.py` | `VoteRequest`, `VoteResponse` |
| `src/cdmas/common/models/coalition.py` | `CoalitionInvite`, `CoalitionRecord` |
| `src/cdmas/common/models/resolution.py` | `ResolutionNotice` |
| `src/cdmas/common/models/errors.py` | `Failure`, `NotUnderstood` |
| `src/cdmas/common/messaging/topics.py` | `Topic` enum + `TOPIC_REGISTRY` (SDD Table 2) |
| `src/cdmas/common/messaging/lamport.py` | `LamportClock` |
| `src/cdmas/common/messaging/acl.py` | `ACLMessage` envelope + `SchemaViolation` + validation |
| `src/cdmas/common/messaging/bus.py` | `MessageBus` ABC, `Subscription`, `InMemoryBus` |
| `src/cdmas/common/logging/event_log.py` | `EventType`, `DecisionTrace`, `EventLog`, `EventSink`, `InMemorySink` |
| `src/cdmas/common/bdi/belief_base.py` | `Belief`, `BeliefBase` (belief-revision function) |
| `src/cdmas/common/bdi/goals.py` | `Goal`, `GoalSet` |
| `src/cdmas/common/bdi/plan.py` | `Plan`, `Intention` |
| `src/cdmas/common/bdi/base_agent.py` | `BaseAgent` abstract perceive→reason→act loop |

Tests mirror the source tree under `tests/common/...`.

---

## Task 0: Verify the toolchain installs

**Files:**
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Create the venv and install the package**

Run:
```bash
cd "/Users/edenadiv/Eden's Files/Eden's Coding Projects/CyberDefenceMultiAgentSystems"
make install
```
Expected: venv created at `.venv`, `pip install -e ".[dev]"` completes without error.

- [ ] **Step 2: Write a smoke test**

```python
# tests/test_smoke.py
import cdmas


def test_package_imports():
    assert cdmas.__version__ == "0.1.0"
```

- [ ] **Step 3: Run it**

Run: `.venv/bin/pytest tests/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: project scaffold + toolchain smoke test"
```

---

## Task 1: Runtime configuration

**Files:**
- Modify: `src/cdmas/common/config.py`
- Test: `tests/common/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/test_config.py
from cdmas.common.config import Settings


def test_defaults():
    s = Settings()
    assert s.kafka_bootstrap == "localhost:9092"
    assert s.sim_speed == 1.0
    assert s.log_json is True


def test_env_override(monkeypatch):
    monkeypatch.setenv("CDMAS_KAFKA_BOOTSTRAP", "kafka:9092")
    monkeypatch.setenv("CDMAS_SIM_SPEED", "5.0")
    s = Settings()
    assert s.kafka_bootstrap == "kafka:9092"
    assert s.sim_speed == 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/test_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'Settings'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/config.py
"""Centralized runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All CDMAS_* environment variables (see .env.example)."""

    model_config = SettingsConfigDict(
        env_prefix="CDMAS_", env_file=".env", extra="ignore"
    )

    # Message bus
    kafka_bootstrap: str = "localhost:9092"
    kafka_client_id: str = "cdmas"
    # Simulator
    sim_base_url: str = "http://localhost:8000"
    sim_api_token: str = "changeme"
    sim_speed: float = 1.0
    sim_tick_ms: int = 10
    # Persistence
    db_url: str = "postgresql+asyncpg://cdmas:cdmas@localhost:5432/cdmas"
    # Logging
    log_level: str = "INFO"
    log_json: bool = True
    # Agent identity (set per container)
    agent_id: str | None = None
    agent_segment: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/config.py tests/common/test_config.py
git commit -m "feat(common): runtime Settings from CDMAS_* env vars"
```

---

## Task 2: Domain enums

**Files:**
- Create: `src/cdmas/common/models/enums.py`
- Test: `tests/common/models/test_enums.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/models/test_enums.py
from cdmas.common.models.enums import (
    AttackType,
    Classification,
    ResourceType,
    ResponseType,
    Segment,
    VoteDecision,
)


def test_segment_values():
    assert Segment.PUBLIC_FACING == "public-facing"
    assert {s.value for s in Segment} == {"internal", "server", "public-facing", "sec-mon"}


def test_classification_and_response():
    assert Classification.CONFIRMED_THREAT == "CONFIRMED_THREAT"
    assert ResponseType.QUARANTINE == "QUARANTINE"
    assert ResourceType.QUARANTINE_SLOT == "QUARANTINE_SLOT"
    assert VoteDecision.ACCEPT == "ACCEPT"
    assert AttackType.ZERO_DAY == "ZERO_DAY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/models/test_enums.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/models/enums.py
"""Domain enumerations shared across message payloads (SRS §2, §3; SDD §3.2)."""

from enum import StrEnum


class Segment(StrEnum):
    INTERNAL = "internal"
    SERVER = "server"
    PUBLIC_FACING = "public-facing"
    SEC_MON = "sec-mon"


class Performative(StrEnum):
    INFORM = "INFORM"
    REQUEST = "REQUEST"
    PROPOSE = "PROPOSE"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CALL_FOR_PROPOSAL = "CALL-FOR-PROPOSAL"
    BID = "BID"
    FAILURE = "FAILURE"
    NOT_UNDERSTOOD = "NOT-UNDERSTOOD"


class AttackType(StrEnum):
    VOLUME_SPIKE = "VOLUME_SPIKE"
    PORT_SCAN = "PORT_SCAN"
    LATERAL = "LATERAL"
    NOVEL = "NOVEL"
    DDOS = "DDOS"
    RANSOMWARE = "RANSOMWARE"
    ZERO_DAY = "ZERO_DAY"


class Classification(StrEnum):
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    CONFIRMED_THREAT = "CONFIRMED_THREAT"


class ResponseType(StrEnum):
    THROTTLE = "THROTTLE"
    BLOCK = "BLOCK"
    REDEPLOY = "REDEPLOY"
    QUARANTINE = "QUARANTINE"
    MONITOR = "MONITOR"


class ResourceType(StrEnum):
    DPI_SLOT = "DPI_SLOT"
    QUARANTINE_SLOT = "QUARANTINE_SLOT"
    CPU_BUDGET = "CPU_BUDGET"


class VoteDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/models/test_enums.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/models/enums.py tests/common/models/test_enums.py
git commit -m "feat(models): domain enums (segments, performatives, attack/response types)"
```

---

## Task 3: Incident payloads — Alert & ThreatReport

**Files:**
- Create: `src/cdmas/common/models/alert.py`
- Create: `src/cdmas/common/models/threat_report.py`
- Test: `tests/common/models/test_incident_payloads.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/models/test_incident_payloads.py
import pytest
from pydantic import ValidationError

from cdmas.common.models.alert import Alert
from cdmas.common.models.enums import AttackType, Classification, Segment
from cdmas.common.models.threat_report import ThreatReport


def test_alert_roundtrip():
    a = Alert(
        segment=Segment.PUBLIC_FACING,
        anomaly_type=AttackType.VOLUME_SPIKE,
        deviation_score=4.2,
        src_ips=["10.0.1.5"],
        dst_port=443,
        traffic_volume=9800,
        baseline_mean=400,
        baseline_std=50,
    )
    assert a.alert_id  # auto uuid
    again = Alert.model_validate_json(a.model_dump_json())
    assert again.deviation_score == 4.2
    assert again.segment is Segment.PUBLIC_FACING


def test_threat_report_severity_bounds():
    with pytest.raises(ValidationError):
        ThreatReport(
            alert_id="x",
            classification=Classification.CONFIRMED_THREAT,
            attack_type=AttackType.DDOS,
            severity=1.5,  # out of [0,1]
            segment=Segment.PUBLIC_FACING,
            confidence=0.9,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/models/test_incident_payloads.py -v`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/models/alert.py
"""Alert payload published by a Traffic Monitor Agent (SDD §3.2.1)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import AttackType, Segment


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Alert(BaseModel):
    alert_id: str = Field(default_factory=_uuid)
    segment: Segment
    anomaly_type: AttackType
    deviation_score: float
    src_ips: list[str] = Field(default_factory=list)
    dst_port: int
    traffic_volume: float
    baseline_mean: float
    baseline_std: float
    detected_at: datetime = Field(default_factory=_now)
```

```python
# src/cdmas/common/models/threat_report.py
"""Threat report published by an Anomaly Classifier Agent (SDD §3.2.2)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import AttackType, Classification, Segment


class ThreatReport(BaseModel):
    threat_id: str = Field(default_factory=lambda: str(uuid4()))
    alert_id: str
    classification: Classification
    attack_type: AttackType
    severity: float = Field(ge=0.0, le=1.0)
    segment: Segment
    confidence: float = Field(ge=0.0, le=1.0)
    classified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/models/test_incident_payloads.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/models/alert.py src/cdmas/common/models/threat_report.py tests/common/models/test_incident_payloads.py
git commit -m "feat(models): Alert and ThreatReport payloads with severity bounds"
```

---

## Task 4: Coordination & error payloads

**Files:**
- Create: `src/cdmas/common/models/bid.py`
- Create: `src/cdmas/common/models/vote.py`
- Create: `src/cdmas/common/models/coalition.py`
- Create: `src/cdmas/common/models/resolution.py`
- Create: `src/cdmas/common/models/errors.py`
- Test: `tests/common/models/test_coordination_payloads.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/models/test_coordination_payloads.py
from datetime import datetime, timezone

from cdmas.common.models.bid import AuctionResult, ResourceBid
from cdmas.common.models.coalition import CoalitionInvite, CoalitionRecord
from cdmas.common.models.enums import ResourceType, ResponseType, Segment, VoteDecision
from cdmas.common.models.errors import Failure, NotUnderstood
from cdmas.common.models.resolution import ResolutionNotice
from cdmas.common.models.vote import VoteRequest, VoteResponse


def test_bid_and_result():
    bid = ResourceBid(
        bidder_id="RCA:seg1",
        resource_type=ResourceType.QUARANTINE_SLOT,
        quantity=1,
        bid_value=0.91,
        justification_threat_id="t1",
    )
    assert bid.bid_id
    res = AuctionResult(granted={"RCA:seg1": 1}, denied=["RCA:seg2"])
    assert res.granted["RCA:seg1"] == 1
    assert "RCA:seg2" in res.denied


def test_vote_pair():
    req = VoteRequest(
        proposal=ResponseType.QUARANTINE,
        target_segment=Segment.SERVER,
        threat_id="t1",
        severity=0.85,
        deadline=datetime.now(timezone.utc),
    )
    resp = VoteResponse(
        vote_id=req.vote_id, voter_id="ACA:seg2", decision=VoteDecision.ACCEPT, rationale="local=0.88"
    )
    assert resp.vote_id == req.vote_id
    assert resp.decision is VoteDecision.ACCEPT


def test_coalition_and_resolution():
    inv = CoalitionInvite(threat_id="t1", segments=[Segment.SERVER, Segment.INTERNAL], required_roles=["ACA", "RCA"])
    rec = CoalitionRecord(coalition_id=inv.coalition_id, members=["ACA:seg1", "RCA:seg1"], lead_rca="RCA:seg1", threat_id="t1")
    assert rec.coalition_id == inv.coalition_id
    note = ResolutionNotice(threat_id="t1", segment=Segment.SERVER, outcome="neutralized")
    assert note.resolution_id


def test_error_payloads():
    f = Failure(in_reply_to="m1", sender="RCA:1", receiver="RAA:1", reason="TIMEOUT", failed_action="QUARANTINE", description="vote deadline exceeded", fallback_action="BLOCK")
    assert f.fallback_action == "BLOCK"
    nu = NotUnderstood(in_reply_to="m1", sender="ACA:2", receiver="TMA:1", reason="SCHEMA_VIOLATION", offending_field="anomaly_type", description="unknown enum")
    assert nu.offending_field == "anomaly_type"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/models/test_coordination_payloads.py -v`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/models/bid.py
"""Resource bidding payloads for the sealed-bid auction (SDD §3.2.3)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import ResourceType


class ResourceBid(BaseModel):
    bid_id: str = Field(default_factory=lambda: str(uuid4()))
    bidder_id: str
    resource_type: ResourceType
    quantity: int = 1
    bid_value: float = Field(ge=0.0, le=1.0)  # = threat severity (FR auction rule)
    justification_threat_id: str
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuctionResult(BaseModel):
    auction_id: str = Field(default_factory=lambda: str(uuid4()))
    granted: dict[str, int] = Field(default_factory=dict)  # bidder_id -> quantity
    denied: list[str] = Field(default_factory=list)
    closed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

```python
# src/cdmas/common/models/vote.py
"""Voting payloads for quarantine escalation (SDD §3.2.4)."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import ResponseType, Segment, VoteDecision


class VoteRequest(BaseModel):
    vote_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal: ResponseType
    target_segment: Segment
    threat_id: str
    severity: float = Field(ge=0.0, le=1.0)
    deadline: datetime


class VoteResponse(BaseModel):
    vote_id: str
    voter_id: str
    decision: VoteDecision
    rationale: str = ""
```

```python
# src/cdmas/common/models/coalition.py
"""Coalition formation payloads (SDD §4.3)."""

from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import Segment


class CoalitionInvite(BaseModel):
    coalition_id: str = Field(default_factory=lambda: str(uuid4()))
    threat_id: str
    segments: list[Segment] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)


class CoalitionRecord(BaseModel):
    coalition_id: str
    members: list[str] = Field(default_factory=list)
    lead_rca: str
    threat_id: str
```

```python
# src/cdmas/common/models/resolution.py
"""Resolution notice broadcast when a threat is neutralized (SDD §3.3.1)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import Segment


class ResolutionNotice(BaseModel):
    resolution_id: str = Field(default_factory=lambda: str(uuid4()))
    threat_id: str
    segment: Segment
    outcome: str
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

```python
# src/cdmas/common/models/errors.py
"""Error reply payloads: FAILURE and NOT-UNDERSTOOD (SDD §3.2.5, §3.2.6)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class Failure(BaseModel):
    failure_id: str = Field(default_factory=lambda: str(uuid4()))
    in_reply_to: str
    sender: str
    receiver: str
    reason: str  # TIMEOUT | RESOURCE_UNAVAILABLE | PLAN_PRECONDITION_FAILED
    failed_action: str
    description: str = ""
    fallback_action: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotUnderstood(BaseModel):
    not_understood_id: str = Field(default_factory=lambda: str(uuid4()))
    in_reply_to: str
    sender: str
    receiver: str
    reason: str  # UNKNOWN_PERFORMATIVE | SCHEMA_VIOLATION | MISSING_FIELD
    offending_field: str | None = None
    description: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/models/test_coordination_payloads.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/models/bid.py src/cdmas/common/models/vote.py src/cdmas/common/models/coalition.py src/cdmas/common/models/resolution.py src/cdmas/common/models/errors.py tests/common/models/test_coordination_payloads.py
git commit -m "feat(models): bid, vote, coalition, resolution, and error payloads"
```

---

## Task 5: Lamport logical clock

**Files:**
- Create: `src/cdmas/common/messaging/lamport.py`
- Test: `tests/common/messaging/test_lamport.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/messaging/test_lamport.py
from cdmas.common.messaging.lamport import LamportClock


def test_tick_monotonic():
    c = LamportClock()
    assert c.tick() == 1
    assert c.tick() == 2
    assert c.time == 2


def test_update_takes_max_plus_one():
    c = LamportClock()
    c.tick()  # 1
    assert c.update(5) == 6   # max(1,5)+1
    assert c.update(2) == 7   # max(6,2)+1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/messaging/test_lamport.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/messaging/lamport.py
"""Lamport logical clock for total message ordering (SDD §3.1.3)."""


class LamportClock:
    def __init__(self, initial: int = 0) -> None:
        self._time = initial

    @property
    def time(self) -> int:
        return self._time

    def tick(self) -> int:
        """Local event (e.g. a send). Increment and return."""
        self._time += 1
        return self._time

    def update(self, received: int) -> int:
        """Receive event. Advance past the received timestamp."""
        self._time = max(self._time, received) + 1
        return self._time
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/messaging/test_lamport.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/messaging/lamport.py tests/common/messaging/test_lamport.py
git commit -m "feat(messaging): Lamport logical clock"
```

---

## Task 6: Topic registry

**Files:**
- Create: `src/cdmas/common/messaging/topics.py`
- Test: `tests/common/messaging/test_topics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/messaging/test_topics.py
from cdmas.common.messaging.topics import TOPIC_REGISTRY, Topic, can_publish, can_subscribe


def test_topic_values():
    assert Topic.ALERTS == "alerts"
    assert Topic.THREAT_REPORTS == "threat-reports"


def test_registry_matches_sdd_table_2():
    # TMA publishes alerts; ACA subscribes.
    assert can_publish("TMA", Topic.ALERTS)
    assert can_subscribe("ACA", Topic.ALERTS)
    assert not can_publish("ACA", Topic.ALERTS)
    # RAA is the only subscriber of resource-bids.
    assert can_subscribe("RAA", Topic.RESOURCE_BIDS)
    assert can_publish("RCA", Topic.RESOURCE_BIDS)


def test_every_topic_registered():
    assert set(TOPIC_REGISTRY) == set(Topic)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/messaging/test_topics.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/messaging/topics.py
"""Pub/sub topic registry (SDD §3.1.2, Table 2).

Agent *types* (TMA, ACA, RCA, TIA, RAA) are the publish/subscribe principals.
"""

from enum import StrEnum


class Topic(StrEnum):
    ALERTS = "alerts"
    THREAT_REPORTS = "threat-reports"
    THREAT_INTEL = "threat-intel"
    RESOURCE_BIDS = "resource-bids"
    RESOURCE_GRANTS = "resource-grants"
    COALITION = "coalition"
    VOTES = "votes"
    RESOLUTION = "resolution"


# topic -> {"publishers": {...}, "subscribers": {...}}
TOPIC_REGISTRY: dict[Topic, dict[str, set[str]]] = {
    Topic.ALERTS: {"publishers": {"TMA"}, "subscribers": {"ACA"}},
    Topic.THREAT_REPORTS: {"publishers": {"ACA"}, "subscribers": {"RCA", "TIA"}},
    Topic.THREAT_INTEL: {"publishers": {"TIA", "ACA"}, "subscribers": {"ACA", "RCA", "RAA"}},
    Topic.RESOURCE_BIDS: {"publishers": {"TMA", "ACA", "RCA"}, "subscribers": {"RAA"}},
    Topic.RESOURCE_GRANTS: {"publishers": {"RAA"}, "subscribers": {"TMA", "ACA", "RCA", "TIA"}},
    Topic.COALITION: {"publishers": {"TIA"}, "subscribers": {"ACA", "RCA", "RAA"}},
    Topic.VOTES: {"publishers": {"RCA"}, "subscribers": {"ACA", "RCA", "TIA", "RAA"}},
    Topic.RESOLUTION: {"publishers": {"RCA"}, "subscribers": {"ACA", "RCA", "TIA", "RAA"}},
}


def can_publish(agent_type: str, topic: Topic) -> bool:
    return agent_type in TOPIC_REGISTRY[topic]["publishers"]


def can_subscribe(agent_type: str, topic: Topic) -> bool:
    return agent_type in TOPIC_REGISTRY[topic]["subscribers"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/messaging/test_topics.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/messaging/topics.py tests/common/messaging/test_topics.py
git commit -m "feat(messaging): topic registry per SDD Table 2"
```

---

## Task 7: ACL message envelope + validation

**Files:**
- Create: `src/cdmas/common/messaging/acl.py`
- Test: `tests/common/messaging/test_acl.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/messaging/test_acl.py
import pytest

from cdmas.common.messaging.acl import ACLMessage, SchemaViolation, parse_message
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


def test_build_and_serialize():
    m = ACLMessage(
        performative=Performative.INFORM,
        sender="TMA:seg1",
        receiver="BROADCAST",
        topic=Topic.ALERTS,
        content={"alert_id": "a1"},
    )
    assert m.msg_id
    assert m.lamport_ts == 0  # stamped by the bus on publish
    raw = m.model_dump_json()
    again = ACLMessage.model_validate_json(raw)
    assert again.sender == "TMA:seg1"
    assert again.topic is Topic.ALERTS


def test_parse_rejects_malformed():
    with pytest.raises(SchemaViolation):
        parse_message('{"performative": "INFORM"}')  # missing required fields


def test_parse_rejects_unknown_performative():
    bad = '{"performative":"FROBNICATE","sender":"a","receiver":"b","topic":"alerts","content":{}}'
    with pytest.raises(SchemaViolation):
        parse_message(bad)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/messaging/test_acl.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/messaging/acl.py
"""FIPA-ACL message envelope and schema validation (SDD §3.1.1, FR-32)."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


class SchemaViolation(Exception):
    """Raised when an inbound message fails schema validation (FR-32)."""


class ACLMessage(BaseModel):
    msg_id: str = Field(default_factory=lambda: str(uuid4()))
    performative: Performative
    sender: str
    receiver: str  # an agent id, or "BROADCAST"
    topic: Topic
    conversation_id: str | None = None
    reply_by: datetime | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    # Set by the agent on send (per-sender monotonic) for idempotent dedup.
    seq: int = 0
    # Set authoritatively by the bus on publish for total ordering.
    lamport_ts: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def parse_message(raw: str | bytes) -> ACLMessage:
    """Validate an inbound message; raise SchemaViolation on any problem."""
    try:
        return ACLMessage.model_validate_json(raw)
    except ValidationError as exc:
        raise SchemaViolation(str(exc)) from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/messaging/test_acl.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/messaging/acl.py tests/common/messaging/test_acl.py
git commit -m "feat(messaging): ACLMessage envelope + schema validation (FR-32)"
```

---

## Task 8: In-memory message bus (FIFO, dedup, deadlines)

**Files:**
- Create: `src/cdmas/common/messaging/bus.py`
- Test: `tests/common/messaging/test_bus.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/messaging/test_bus.py
import pytest

from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


def _msg(sender: str, seq: int, receiver: str = "BROADCAST") -> ACLMessage:
    return ACLMessage(
        performative=Performative.INFORM,
        sender=sender,
        receiver=receiver,
        topic=Topic.ALERTS,
        seq=seq,
        content={"n": seq},
    )


async def test_fifo_delivery_and_lamport_stamp():
    bus = InMemoryBus()
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    await bus.publish(_msg("TMA:seg1", 1))
    await bus.publish(_msg("TMA:seg1", 2))
    m1 = await sub.get(timeout=1)
    m2 = await sub.get(timeout=1)
    assert (m1.content["n"], m2.content["n"]) == (1, 2)  # FIFO
    assert m1.lamport_ts < m2.lamport_ts                  # bus-stamped total order


async def test_idempotent_dedup():
    bus = InMemoryBus()
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    await bus.publish(_msg("TMA:seg1", 1))
    await bus.publish(_msg("TMA:seg1", 1))  # duplicate seq -> dropped
    assert (await sub.get(timeout=0.1)).content["n"] == 1
    assert await sub.get(timeout=0.1) is None  # nothing more


async def test_no_self_echo_and_targeted_receiver():
    bus = InMemoryBus()
    tma = bus.subscribe(Topic.ALERTS, "TMA:seg1")
    aca = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    await bus.publish(_msg("TMA:seg1", 1, receiver="ACA:seg1"))
    assert (await aca.get(timeout=0.1)).content["n"] == 1
    assert await tma.get(timeout=0.1) is None  # sender does not receive own msg


async def test_deadline_returns_none_when_idle():
    bus = InMemoryBus()
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    with pytest.raises(Exception):  # placeholder replaced below
        raise Exception
```

> Note: delete the last test's placeholder body and assert `await sub.get(timeout=0.05) is None` once you see it fail meaningfully. (Kept explicit so the engineer writes the real assertion.)

Replace the final test body with:
```python
async def test_deadline_returns_none_when_idle():
    bus = InMemoryBus()
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    assert await sub.get(timeout=0.05) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/messaging/test_bus.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/messaging/bus.py
"""Asynchronous publish-subscribe bus (SDD §3.1).

Abstract ``MessageBus`` with an ``InMemoryBus`` implementation for tests and
single-process runs. Guarantees per-topic FIFO delivery, idempotent dedup on
(sender, seq), Lamport total ordering, and deadline-bounded receives. The Kafka
implementation (KafkaBus) is added in Phase 2 behind the same interface.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict

from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.lamport import LamportClock
from cdmas.common.messaging.topics import Topic


class Subscription:
    """A per-(topic, agent) inbox backed by an asyncio queue."""

    def __init__(self, topic: Topic, agent_id: str, queue: asyncio.Queue[ACLMessage]) -> None:
        self.topic = topic
        self.agent_id = agent_id
        self._queue = queue

    async def get(self, timeout: float | None = None) -> ACLMessage | None:
        """Return the next message, or None if `timeout` seconds elapse."""
        if timeout is None:
            return await self._queue.get()
        try:
            return await asyncio.wait_for(self._queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    def get_nowait(self) -> ACLMessage | None:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def __aiter__(self) -> Subscription:
        return self

    async def __anext__(self) -> ACLMessage:
        return await self._queue.get()


class MessageBus(ABC):
    @abstractmethod
    async def publish(self, message: ACLMessage) -> None: ...

    @abstractmethod
    def subscribe(self, topic: Topic, agent_id: str) -> Subscription: ...

    async def start(self) -> None:  # pragma: no cover - no-op for in-memory
        return None

    async def stop(self) -> None:  # pragma: no cover - no-op for in-memory
        return None


class InMemoryBus(MessageBus):
    def __init__(self) -> None:
        self._subs: dict[Topic, dict[str, asyncio.Queue[ACLMessage]]] = defaultdict(dict)
        self._seen: dict[str, int] = {}  # sender -> highest seq delivered (dedup)
        self._clock = LamportClock()
        self._lock = asyncio.Lock()

    def subscribe(self, topic: Topic, agent_id: str) -> Subscription:
        queue: asyncio.Queue[ACLMessage] = asyncio.Queue()
        self._subs[topic][agent_id] = queue
        return Subscription(topic, agent_id, queue)

    async def publish(self, message: ACLMessage) -> None:
        async with self._lock:
            # Idempotent dedup on (sender, seq); seq==0 means "unsequenced".
            if message.seq:
                if message.seq <= self._seen.get(message.sender, 0):
                    return
                self._seen[message.sender] = message.seq
            # Authoritative total-order stamp.
            message.lamport_ts = self._clock.tick()
            for agent_id, queue in self._subs.get(message.topic, {}).items():
                if agent_id == message.sender:
                    continue  # never echo to sender
                if message.receiver not in ("BROADCAST", agent_id):
                    continue  # targeted message for someone else
                queue.put_nowait(message)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/messaging/test_bus.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/messaging/bus.py tests/common/messaging/test_bus.py
git commit -m "feat(messaging): in-memory pub/sub bus (FIFO, dedup, deadlines)"
```

---

## Task 9: Structured event log

**Files:**
- Create: `src/cdmas/common/logging/event_log.py`
- Test: `tests/common/logging/test_event_log.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/logging/test_event_log.py
from cdmas.common.logging.event_log import DecisionTrace, EventLog, EventType, InMemorySink


async def test_sink_records_events():
    sink = InMemorySink()
    e = EventLog(
        lamport_ts=7,
        wall_ms=1234.5,
        event_type=EventType.THREAT_CLASSIFIED,
        agent_id="ACA:seg1",
        agent_type="ACA",
        segment="public-facing",
        payload={"severity": 0.91},
        latency_ms=178,
        decision_trace=DecisionTrace(
            inputs={"alert_id": "a1"},
            plan_selected="classify_alert",
            reasoning="0.91 > threshold",
            action="PUBLISH_THREAT_REPORT",
        ),
    )
    await sink.write(e)
    assert len(sink.events) == 1
    assert sink.events[0].event_type is EventType.THREAT_CLASSIFIED
    assert sink.events[0].decision_trace.action == "PUBLISH_THREAT_REPORT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/logging/test_event_log.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/logging/event_log.py
"""Structured JSON event log (SDD §7.1).

EventLog is the single record type written for every agent decision, inter-agent
message, and environment state change. Sinks persist it; the PostgreSQL sink is
added in Phase 6.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    ALERT_PUBLISHED = "ALERT_PUBLISHED"
    THREAT_CLASSIFIED = "THREAT_CLASSIFIED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    AUCTION_COMPLETED = "AUCTION_COMPLETED"
    VOTE_CAST = "VOTE_CAST"
    COALITION_FORMED = "COALITION_FORMED"
    AGENT_FAILED = "AGENT_FAILED"
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"


class DecisionTrace(BaseModel):
    inputs: dict = Field(default_factory=dict)
    plan_selected: str
    reasoning: str
    action: str


class EventLog(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    lamport_ts: int
    wall_ms: float
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str
    agent_type: str
    segment: str | None = None
    payload: dict = Field(default_factory=dict)
    latency_ms: int | None = None
    decision_trace: DecisionTrace | None = None


class EventSink(ABC):
    @abstractmethod
    async def write(self, event: EventLog) -> None: ...


class InMemorySink(EventSink):
    def __init__(self) -> None:
        self.events: list[EventLog] = []

    async def write(self, event: EventLog) -> None:
        self.events.append(event)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/logging/test_event_log.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/logging/event_log.py tests/common/logging/test_event_log.py
git commit -m "feat(logging): structured EventLog + in-memory sink"
```

---

## Task 10: Belief base + belief revision function

**Files:**
- Create: `src/cdmas/common/bdi/belief_base.py`
- Test: `tests/common/bdi/test_belief_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/bdi/test_belief_base.py
from cdmas.common.bdi.belief_base import Belief, BeliefBase


def test_add_and_query():
    bb = BeliefBase()
    bb.revise(Belief(predicate="traffic_rate", value=3902, source="sim", lamport_ts=1))
    assert bb.query("traffic_rate").value == 3902
    assert bb.value("missing", default=0) == 0
    assert "traffic_rate" in bb


def test_brf_keeps_newer_lamport():
    bb = BeliefBase()
    bb.revise(Belief(predicate="rate", value=10, source="a", lamport_ts=5))
    bb.revise(Belief(predicate="rate", value=99, source="b", lamport_ts=3))  # stale -> ignored
    assert bb.query("rate").value == 10
    bb.revise(Belief(predicate="rate", value=42, source="c", lamport_ts=9))  # newer -> wins
    assert bb.query("rate").value == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/bdi/test_belief_base.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/bdi/belief_base.py
"""Belief base and belief revision function (SDD §2.1, §5.2.1)."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Belief:
    predicate: str
    value: Any
    source: str
    lamport_ts: int = 0
    confidence: float = 1.0


class BeliefBase:
    """The agent's current knowledge, keyed by predicate."""

    def __init__(self) -> None:
        self._beliefs: dict[str, Belief] = {}

    def revise(self, belief: Belief) -> None:
        """BRF: accept a belief if it is at least as recent (Lamport) as the held one."""
        existing = self._beliefs.get(belief.predicate)
        if existing is None or belief.lamport_ts >= existing.lamport_ts:
            self._beliefs[belief.predicate] = belief

    def query(self, predicate: str) -> Belief | None:
        return self._beliefs.get(predicate)

    def value(self, predicate: str, default: Any = None) -> Any:
        belief = self._beliefs.get(predicate)
        return belief.value if belief is not None else default

    def __contains__(self, predicate: str) -> bool:
        return predicate in self._beliefs

    def __len__(self) -> int:
        return len(self._beliefs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/bdi/test_belief_base.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/bdi/belief_base.py tests/common/bdi/test_belief_base.py
git commit -m "feat(bdi): belief base with Lamport-aware revision function"
```

---

## Task 11: Goals & goal set

**Files:**
- Create: `src/cdmas/common/bdi/goals.py`
- Test: `tests/common/bdi/test_goals.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/bdi/test_goals.py
from cdmas.common.bdi.goals import Goal, GoalSet


def test_top_returns_highest_priority_active_goal():
    gs = GoalSet()
    gs.add(Goal(description="minimize FPR", priority=0.3))
    gs.add(Goal(description="maximize U_ACA", priority=0.9))
    held = Goal(description="refresh model", priority=1.0, status="held")
    gs.add(held)
    assert gs.top().description == "maximize U_ACA"  # held goal excluded despite priority


def test_drop_and_ranked():
    gs = GoalSet()
    g1 = Goal(description="a", priority=0.1)
    g2 = Goal(description="b", priority=0.5)
    gs.add(g1)
    gs.add(g2)
    assert [g.description for g in gs.ranked()] == ["b", "a"]
    gs.drop(g2)
    assert gs.top().description == "a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/bdi/test_goals.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/bdi/goals.py
"""Desires: utility-ranked goals (SDD §2.1, §5.2.1)."""

from collections.abc import Callable
from dataclasses import dataclass, field

from cdmas.common.bdi.belief_base import BeliefBase


@dataclass
class Goal:
    description: str
    priority: float
    utility_fn: Callable[[BeliefBase], float] | None = None
    status: str = "active"  # active | held | queued | satisfied | dropped


@dataclass
class GoalSet:
    _goals: list[Goal] = field(default_factory=list)

    def add(self, goal: Goal) -> None:
        self._goals.append(goal)

    def drop(self, goal: Goal) -> None:
        if goal in self._goals:
            self._goals.remove(goal)

    def ranked(self) -> list[Goal]:
        """Active goals, highest priority first."""
        active = [g for g in self._goals if g.status == "active"]
        return sorted(active, key=lambda g: g.priority, reverse=True)

    def top(self) -> Goal | None:
        ranked = self.ranked()
        return ranked[0] if ranked else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/bdi/test_goals.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/bdi/goals.py tests/common/bdi/test_goals.py
git commit -m "feat(bdi): goal set with priority ranking"
```

---

## Task 12: Plans & intentions

**Files:**
- Create: `src/cdmas/common/bdi/plan.py`
- Test: `tests/common/bdi/test_plan.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/bdi/test_plan.py
from cdmas.common.bdi.belief_base import Belief, BeliefBase
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Intention, Plan


def test_applicable_requires_trigger_and_precondition():
    bb = BeliefBase()
    bb.revise(Belief(predicate="anomaly", value=True, source="self", lamport_ts=1))

    async def body(agent):  # noqa: ARG001
        return "done"

    plan = Plan(
        plan_id="detect_anomaly",
        trigger=lambda b: b.value("anomaly") is True,
        precondition=lambda b: True,
        body=body,
        deadline_ms=100,
    )
    assert plan.applicable(bb) is True

    bb.revise(Belief(predicate="anomaly", value=False, source="self", lamport_ts=2))
    assert plan.applicable(bb) is False


def test_intention_binds_goal_and_plan():
    async def body(agent):  # noqa: ARG001
        return None

    plan = Plan(plan_id="p", trigger=lambda b: True, precondition=lambda b: True, body=body)
    goal = Goal(description="g", priority=1.0)
    intent = Intention(goal=goal, plan=plan, started_at=5)
    assert intent.plan.plan_id == "p"
    assert intent.started_at == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/bdi/test_plan.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/bdi/plan.py
"""Plans and intentions (SDD §2.1, §5.2.1).

A Plan is a conditional recipe: (trigger, precondition, body). An Intention is a
committed (goal, plan) pair the agent is currently executing.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cdmas.common.bdi.belief_base import BeliefBase
from cdmas.common.bdi.goals import Goal

if TYPE_CHECKING:
    from cdmas.common.bdi.base_agent import BaseAgent

Predicate = Callable[[BeliefBase], bool]
PlanBody = Callable[["BaseAgent"], Awaitable[Any]]


@dataclass
class Plan:
    plan_id: str
    trigger: Predicate
    precondition: Predicate
    body: PlanBody
    deadline_ms: int | None = None

    def applicable(self, beliefs: BeliefBase) -> bool:
        return self.trigger(beliefs) and self.precondition(beliefs)


@dataclass
class Intention:
    goal: Goal
    plan: Plan
    started_at: int  # Lamport timestamp at commitment
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/bdi/test_plan.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/bdi/plan.py tests/common/bdi/test_plan.py
git commit -m "feat(bdi): Plan (trigger/precondition/body) and Intention"
```

---

## Task 13: BaseAgent perceive→reason→act loop

**Files:**
- Create: `src/cdmas/common/bdi/base_agent.py`
- Test: `tests/common/bdi/test_base_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/common/bdi/test_base_agent.py
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.belief_base import Belief
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import InMemorySink
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


class _Echo(BaseAgent):
    """On any alert, set a belief and publish a threat-report."""

    def setup(self) -> None:
        self.subscribe(Topic.ALERTS)
        self.goals.add(Goal(description="respond", priority=1.0))

        async def respond(agent: BaseAgent) -> None:
            await agent.publish(
                ACLMessage(
                    performative=Performative.INFORM,
                    sender=agent.agent_id,
                    receiver="BROADCAST",
                    topic=Topic.THREAT_REPORTS,
                    content={"echoed": agent.beliefs.value("last_alert")},
                )
            )
            agent.beliefs.revise(Belief(predicate="responded", value=True, source=agent.agent_id))

        self.plans.append(
            Plan(
                plan_id="respond",
                trigger=lambda b: b.value("last_alert") is not None and not b.value("responded", False),
                precondition=lambda b: True,
                body=respond,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        self.beliefs.revise(
            Belief(predicate="last_alert", value=message.content.get("n"), source=message.sender, lamport_ts=message.lamport_ts)
        )


async def test_agent_id_parsing_and_seq():
    bus = InMemoryBus()
    agent = _Echo(agent_id="ACA:seg1", segment="public-facing", bus=bus)
    assert agent.agent_type == "ACA"


async def test_perceive_reason_act_cycle_and_dedup_seq():
    bus = InMemoryBus()
    producer_sub = bus.subscribe(Topic.THREAT_REPORTS, "OBSERVER")
    agent = _Echo(agent_id="ACA:seg1", segment="public-facing", bus=bus, event_sink=InMemorySink())
    agent.setup()

    # Inject an alert as if from a TMA.
    await bus.publish(
        ACLMessage(performative=Performative.INFORM, sender="TMA:seg1", receiver="BROADCAST", topic=Topic.ALERTS, seq=1, content={"n": 7})
    )

    await agent.step()  # perceive -> reason -> act

    out = await producer_sub.get(timeout=1)
    assert out.content["echoed"] == 7
    assert out.seq == 1  # agent's first outbound carries seq 1
    assert agent.beliefs.value("responded") is True

    # Second step with no new input does nothing (plan no longer applicable).
    await agent.step()
    assert await producer_sub.get(timeout=0.05) is None


async def test_outbound_lamport_advances_on_receive():
    bus = InMemoryBus()
    agent = _Echo(agent_id="ACA:seg1", segment="public-facing", bus=bus)
    agent.setup()
    await bus.publish(
        ACLMessage(performative=Performative.INFORM, sender="TMA:seg1", receiver="BROADCAST", topic=Topic.ALERTS, seq=1, content={"n": 1})
    )
    before = agent.clock.time
    await agent.step()
    assert agent.clock.time > before  # clock advanced from receive + send
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/common/bdi/test_base_agent.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cdmas/common/bdi/base_agent.py
"""BaseAgent: the BDI perceive->reason->act loop (SDD §2, §5.2)."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from cdmas.common.bdi.belief_base import BeliefBase
from cdmas.common.bdi.goals import GoalSet
from cdmas.common.bdi.plan import Intention, Plan
from cdmas.common.logging.event_log import EventSink, InMemorySink
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus, Subscription
from cdmas.common.messaging.lamport import LamportClock
from cdmas.common.messaging.topics import Topic


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        event_sink: EventSink | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.agent_type = agent_id.split(":")[0]
        self.segment = segment
        self.bus = bus
        self.beliefs = BeliefBase()
        self.goals = GoalSet()
        self.plans: list[Plan] = []
        self.intention: Intention | None = None
        self.clock = LamportClock()
        self.sink: EventSink = event_sink or InMemorySink()
        self._subs: list[Subscription] = []
        self._seq = 0
        self._running = False

    # --- subclass extension points ---------------------------------------
    @abstractmethod
    def setup(self) -> None:
        """Register subscriptions, goals, and plans. Called once before run()."""

    def on_message(self, message: ACLMessage) -> None:
        """Integrate an inbound message into the belief base. Override per agent."""

    # --- bus helpers ------------------------------------------------------
    def subscribe(self, topic: Topic) -> None:
        self._subs.append(self.bus.subscribe(topic, self.agent_id))

    async def publish(self, message: ACLMessage) -> None:
        self._seq += 1
        message.seq = self._seq
        message.sender = self.agent_id
        self.clock.tick()  # local send event
        await self.bus.publish(message)

    # --- BDI loop ---------------------------------------------------------
    async def perceive(self) -> list[ACLMessage]:
        """Drain all currently queued messages from every subscription."""
        percepts: list[ACLMessage] = []
        for sub in self._subs:
            while (msg := sub.get_nowait()) is not None:
                percepts.append(msg)
        return percepts

    def reason(self) -> Intention | None:
        """Pick the first applicable plan, bound to the top active goal."""
        goal = self.goals.top()
        if goal is None:
            return None
        for plan in self.plans:
            if plan.applicable(self.beliefs):
                return Intention(goal=goal, plan=plan, started_at=self.clock.time)
        return None

    async def act(self, intention: Intention) -> None:
        await intention.plan.body(self)

    async def step(self) -> None:
        for msg in await self.perceive():
            self.clock.update(msg.lamport_ts)
            self.on_message(msg)
        intention = self.reason()
        if intention is not None:
            self.intention = intention
            await self.act(intention)

    async def run(self, tick_seconds: float = 0.01) -> None:
        self._running = True
        self.setup()
        while self._running:
            await self.step()
            await asyncio.sleep(tick_seconds)

    def stop(self) -> None:
        self._running = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/common/bdi/test_base_agent.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cdmas/common/bdi/base_agent.py tests/common/bdi/test_base_agent.py
git commit -m "feat(bdi): BaseAgent perceive->reason->act loop with bus integration"
```

---

## Task 14: Full-suite green + lint + typecheck gate

**Files:** none (verification task)

- [ ] **Step 1: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: ALL tests pass (config, models, messaging, logging, bdi).

- [ ] **Step 2: Lint**

Run: `.venv/bin/ruff check src tests`
Expected: no errors (fix any with `.venv/bin/ruff check --fix src tests`).

- [ ] **Step 3: Type-check**

Run: `.venv/bin/mypy`
Expected: `Success: no issues found`. Fix any type errors before proceeding.

- [ ] **Step 4: Commit the green-gate state**

```bash
git add -A
git commit -m "test(foundations): full suite green, lint + mypy clean"
```

---

## Self-Review

**1. Spec coverage:**
- SDD §2 BDI architecture → Tasks 10–13 (belief base, goals, plans, BaseAgent loop). ✓
- SDD §3.1 communication (ACL, Lamport, async sync, dedup, FAILURE/NOT-UNDERSTOOD) → Tasks 5, 7, 8; FAILURE/NOT-UNDERSTOOD *payloads* in Task 4, error *replies on parse failure* via `SchemaViolation` (Task 7) — the generation of reply messages is wired in Phase 3 when agents handle inbound traffic. ✓ (noted, not a gap)
- SDD §3.2 payloads → Tasks 3–4 (Alert, ThreatReport, Bid, AuctionResult, Vote*, Coalition*, ResolutionNotice, Failure, NotUnderstood). ✓
- SDD §3.1.2 topic registry → Task 6. ✓
- SDD §7.1 event log → Task 9. ✓
- SRS FR-32 (structured schema, reject malformed, log rejection) → Task 7 (`parse_message`/`SchemaViolation`). The *logging* of the rejection is exercised when an agent uses it in Phase 3. ✓
- Config (CDMAS_* env) → Task 1. ✓

**2. Placeholder scan:** Task 8 Step 1 contains an intentional placeholder in the final test that the engineer must replace — flagged explicitly with the replacement code immediately below it. No other "TBD/TODO/handle edge cases" placeholders. ✓

**3. Type consistency:**
- `ACLMessage` field names (`msg_id`, `performative`, `sender`, `receiver`, `topic`, `conversation_id`, `reply_by`, `content`, `seq`, `lamport_ts`, `timestamp`) are used consistently in Tasks 7, 8, 13. ✓
- `Subscription.get(timeout)` / `get_nowait()` used identically in Tasks 8 and 13. ✓
- `BeliefBase.revise/query/value/__contains__` consistent across Tasks 10, 13. ✓
- `Plan(plan_id, trigger, precondition, body, deadline_ms)` and `Intention(goal, plan, started_at)` consistent across Tasks 12, 13. ✓
- `BaseAgent.subscribe(topic)`, `.publish(message)`, `.on_message`, `.step()` consistent in Task 13 test and impl. ✓
- `EventLog` / `DecisionTrace` field names consistent in Task 9. ✓

No gaps requiring new tasks.
