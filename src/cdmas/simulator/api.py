"""FastAPI simulation API + WebSocket state feed (SDD §6.1.2, Table 5).

Wraps an ``InProcessSimulator``. ``GET /packets`` ticks the engine on demand so each agent
poll advances the sim and returns fresh traffic (deterministic, no background ticker).
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect

from cdmas.common.models.enums import Segment
from cdmas.common.models.metrics import MetricsSnapshot
from cdmas.common.timing.clock import WallClock
from cdmas.simulator.auth import RateLimiter, token_ok
from cdmas.simulator.engine import InProcessSimulator
from cdmas.simulator.models import (
    ActionRequest,
    ActionResult,
    InjectAttackRequest,
    StateSnapshot,
    TopologyView,
)
from cdmas.simulator.packet import Packet


def create_app(
    *,
    engine: InProcessSimulator | None = None,
    token: str = "changeme",
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    sim = engine or InProcessSimulator(clock=WallClock())
    limiter = rate_limiter or RateLimiter()
    app = FastAPI(title="CDMAS Simulator")

    def auth(
        authorization: str | None = Header(default=None),
        x_agent_id: str = Header(default="anon"),
    ) -> str:
        if not token_ok(authorization, token):
            raise HTTPException(status_code=401, detail="invalid token")
        if not limiter.allow(x_agent_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        return x_agent_id

    def _segment(segment: str) -> Segment:
        try:
            return Segment(segment)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="unknown segment") from exc

    @app.get("/topology")
    async def topology(_agent: str = Depends(auth)) -> TopologyView:
        return await sim.get_topology()

    @app.get("/packets/{segment}")
    async def packets(segment: str, n: int = 100, _agent: str = Depends(auth)) -> list[Packet]:
        seg = _segment(segment)
        sim.tick()
        return await sim.get_packets(seg, n)

    @app.post("/action")
    async def action(req: ActionRequest, _agent: str = Depends(auth)) -> ActionResult:
        return await sim.apply_action(req)

    @app.get("/state")
    async def state(_agent: str = Depends(auth)) -> StateSnapshot:
        return await sim.get_state()

    @app.get("/metrics")
    async def metrics(_agent: str = Depends(auth)) -> MetricsSnapshot:
        snap = await sim.get_state()
        return MetricsSnapshot(resource_overhead=snap.resource_overhead)

    @app.post("/inject-attack")
    async def inject_attack(
        req: InjectAttackRequest, _agent: str = Depends(auth)
    ) -> dict[str, str]:
        sim.inject(req.spec)
        return {"status": "injected"}

    @app.websocket("/ws/state")
    async def ws_state(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                sim.tick()
                snap = await sim.get_state()
                await ws.send_json(snap.model_dump(mode="json"))
                await sim.clock.sleep(sim.simclock.tick_ms)
        except WebSocketDisconnect:
            return

    return app
