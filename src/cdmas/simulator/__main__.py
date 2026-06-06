"""`cdmas-simulator` entrypoint: serve the FastAPI app with uvicorn."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from cdmas.common.config import get_settings
from cdmas.common.models.enums import Segment
from cdmas.common.timing.clock import WallClock
from cdmas.simulator.api import create_app
from cdmas.simulator.engine import InProcessSimulator


def build_app() -> FastAPI:
    settings = get_settings()
    engine = InProcessSimulator(
        clock=WallClock(), segments=list(Segment), seed=0, speed=settings.sim_speed
    )
    return create_app(engine=engine, token=settings.sim_api_token)


def main() -> None:
    settings = get_settings()
    uvicorn.run(build_app(), host=settings.sim_host, port=settings.sim_port)


if __name__ == "__main__":
    main()
