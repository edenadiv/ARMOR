"""`python -m cdmas.live` — serve the live single-process MAS demo with uvicorn.

Override the port with ``CDMAS_LIVE_PORT`` (default: the simulator port). The dashboard's
Live mode connects to ``ws://<host>:<port>/ws/events?token=<sim_api_token>``.
"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

from cdmas.common.config import get_settings
from cdmas.common.models.enums import Segment
from cdmas.live.app import create_live_app
from cdmas.live.session import LiveSession


def build_app() -> FastAPI:
    settings = get_settings()
    session = LiveSession(segments=list(Segment))
    return create_live_app(session, token=settings.sim_api_token)


def main() -> None:
    settings = get_settings()
    port = int(os.environ.get("CDMAS_LIVE_PORT", settings.sim_port))
    uvicorn.run(build_app(), host=settings.sim_host, port=port)


if __name__ == "__main__":
    main()
