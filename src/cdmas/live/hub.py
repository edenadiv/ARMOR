"""Process-global event hub: fans live frames out to every connected dashboard client.

Each subscriber gets its own bounded queue; on overflow the oldest frame is dropped (a
slow client never blocks the simulation) and a counter is bumped. Frames carry a
monotonic ``server_seq`` so the UI can detect gaps.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_MAX_QUEUE = 256

# Frame kinds streamed to the dashboard.
KIND_AGENT_EVENT = "agent_event"
KIND_SIM_EVENT = "sim_event"
KIND_CONNECTION_STATUS = "connection_status"
KIND_SIMULATION_STATE = "simulation_state"
KIND_METRICS = "metrics"
KIND_PACKETS = "packets"


class StreamFrame(BaseModel):
    kind: str
    server_seq: int
    ts_ms: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)


class EventHub:
    def __init__(self, *, max_queue: int = DEFAULT_MAX_QUEUE) -> None:
        self._subs: set[asyncio.Queue[StreamFrame]] = set()
        self._seq = 0
        self._dropped = 0
        self._max_queue = max_queue

    def subscribe(self) -> asyncio.Queue[StreamFrame]:
        q: asyncio.Queue[StreamFrame] = asyncio.Queue(maxsize=self._max_queue)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[StreamFrame]) -> None:
        self._subs.discard(q)

    def publish(self, kind: str, payload: dict[str, Any], *, ts_ms: float = 0.0) -> StreamFrame:
        self._seq += 1
        frame = StreamFrame(kind=kind, server_seq=self._seq, ts_ms=ts_ms, payload=payload)
        for q in list(self._subs):
            self._offer(q, frame)
        return frame

    def _offer(self, q: asyncio.Queue[StreamFrame], frame: StreamFrame) -> None:
        try:
            q.put_nowait(frame)
        except asyncio.QueueFull:
            try:
                q.get_nowait()  # drop oldest
                self._dropped += 1
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(frame)
            except asyncio.QueueFull:
                self._dropped += 1

    @property
    def dropped(self) -> int:
        return self._dropped

    @property
    def subscribers(self) -> int:
        return len(self._subs)
