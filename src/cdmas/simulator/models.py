"""Request/response models for the simulator API and engine (SDD §6.1.2)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from cdmas.common.models.enums import ResponseType, Segment
from cdmas.simulator.attacks import AttackSpec


class ActionRequest(BaseModel):
    type: ResponseType
    segment: Segment
    params: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    accepted: bool
    effectiveness: float
    detail: str = ""


class SegmentState(BaseModel):
    segment: Segment
    health: str
    flows_per_s: float
    active_defenses: list[str] = Field(default_factory=list)


class StateSnapshot(BaseModel):
    sim_ms: float
    segments: list[SegmentState] = Field(default_factory=list)
    resource_overhead: float = 0.0
    auctions: list[dict[str, Any]] = Field(default_factory=list)


class TopologyView(BaseModel):
    segments: list[Segment]
    adjacency: dict[str, list[str]]


class InjectAttackRequest(BaseModel):
    spec: AttackSpec
