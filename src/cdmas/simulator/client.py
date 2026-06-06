"""SimClientProtocol and the httpx-backed SimClient (SDD §5.3).

Agents depend on ``SimClientProtocol``; in tests/harness they use ``InProcessSimulator``,
in production the ``SimClient`` hitting the FastAPI REST API.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx

from cdmas.common.models.enums import Segment
from cdmas.simulator.models import ActionRequest, ActionResult, StateSnapshot, TopologyView
from cdmas.simulator.packet import Packet


@runtime_checkable
class SimClientProtocol(Protocol):
    async def get_packets(self, segment: Segment, n: int) -> list[Packet]: ...
    async def apply_action(self, req: ActionRequest) -> ActionResult: ...
    async def get_topology(self) -> TopologyView: ...
    async def get_state(self) -> StateSnapshot: ...


class SimClient:
    """httpx async client implementing SimClientProtocol against the REST API."""

    def __init__(
        self,
        base_url: str = "",
        token: str = "",
        agent_id: str = "anon",
        *,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._http = http or httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}", "X-Agent-Id": agent_id},
        )

    async def get_packets(self, segment: Segment, n: int) -> list[Packet]:
        r = await self._http.get(f"/packets/{segment.value}", params={"n": n})
        r.raise_for_status()
        return [Packet(**p) for p in r.json()]

    async def apply_action(self, req: ActionRequest) -> ActionResult:
        r = await self._http.post("/action", json=req.model_dump(mode="json"))
        r.raise_for_status()
        return ActionResult(**r.json())

    async def get_topology(self) -> TopologyView:
        r = await self._http.get("/topology")
        r.raise_for_status()
        return TopologyView(**r.json())

    async def get_state(self) -> StateSnapshot:
        r = await self._http.get("/state")
        r.raise_for_status()
        return StateSnapshot(**r.json())

    async def aclose(self) -> None:
        await self._http.aclose()
