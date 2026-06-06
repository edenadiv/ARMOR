from fastapi.testclient import TestClient

from cdmas.common.models.enums import Segment
from cdmas.common.timing.clock import WallClock
from cdmas.simulator.api import create_app
from cdmas.simulator.engine import InProcessSimulator

_AUTH = {"Authorization": "Bearer t", "X-Agent-Id": "TMA:seg1"}


def _client() -> TestClient:
    engine = InProcessSimulator(clock=WallClock(), segments=[Segment.PUBLIC_FACING], seed=0)
    return TestClient(create_app(engine=engine, token="t"))


def test_auth_required():
    c = _client()
    assert c.get("/topology").status_code == 401
    assert c.get("/topology", headers=_AUTH).status_code == 200


def test_topology_endpoint():
    r = _client().get("/topology", headers=_AUTH)
    body = r.json()
    assert "public-facing" in body["adjacency"]


def test_inject_then_packets_then_action_flow():
    c = _client()
    c.post(
        "/inject-attack",
        headers=_AUTH,
        json={"spec": {"type": "DDOS", "segment": "public-facing", "intensity": 2.0}},
    )
    pkts = c.get("/packets/public-facing", headers=_AUTH, params={"n": 10_000}).json()
    assert any(p["src_ip"].startswith("203.0.") for p in pkts)  # malicious traffic present

    r = c.post("/action", headers=_AUTH, json={"type": "THROTTLE", "segment": "public-facing"})
    assert r.json()["accepted"] is True

    state = c.get("/state", headers=_AUTH).json()
    assert state["segments"][0]["health"] == "UNDER_ATTACK"

    metrics = c.get("/metrics", headers=_AUTH).json()
    assert "resource_overhead" in metrics


def test_unknown_segment_404():
    assert _client().get("/packets/nope", headers=_AUTH).status_code == 404


def test_websocket_state_feed():
    c = _client()
    with c.websocket_connect("/ws/state") as ws:
        snap = ws.receive_json()
        assert "segments" in snap and "sim_ms" in snap
