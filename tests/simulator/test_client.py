import httpx

from cdmas.common.models.enums import ResponseType, Segment
from cdmas.common.timing.clock import WallClock
from cdmas.simulator.api import create_app
from cdmas.simulator.client import SimClient, SimClientProtocol
from cdmas.simulator.engine import InProcessSimulator
from cdmas.simulator.models import ActionRequest


def _client() -> SimClient:
    engine = InProcessSimulator(clock=WallClock(), segments=[Segment.PUBLIC_FACING], seed=0)
    app = create_app(engine=engine, token="t")
    http = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer t", "X-Agent-Id": "TMA:seg1"},
    )
    return SimClient(http=http)


def test_inprocess_and_httpx_satisfy_protocol():
    engine = InProcessSimulator(clock=WallClock(), segments=[Segment.PUBLIC_FACING])
    assert isinstance(engine, SimClientProtocol)
    assert isinstance(_client(), SimClientProtocol)


async def test_simclient_roundtrip_over_asgi():
    client = _client()
    topo = await client.get_topology()
    assert Segment.PUBLIC_FACING in topo.segments

    pkts = await client.get_packets(Segment.PUBLIC_FACING, 50)
    assert len(pkts) > 0

    res = await client.apply_action(
        ActionRequest(type=ResponseType.THROTTLE, segment=Segment.PUBLIC_FACING)
    )
    assert res.accepted is True

    state = await client.get_state()
    assert state.segments
    await client.aclose()
