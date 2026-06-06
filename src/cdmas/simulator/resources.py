"""Defensive resource pool with the 40% host-overhead cap (FR-23; SDD §2.6)."""

from __future__ import annotations

from cdmas.common.models.enums import ResourceType

# Host-capacity cost per allocated unit of each resource type.
_COST: dict[ResourceType, float] = {
    ResourceType.DPI_SLOT: 3.0,
    ResourceType.QUARANTINE_SLOT: 5.0,
    ResourceType.CPU_BUDGET: 1.0,
}


class ResourcePool:
    def __init__(
        self,
        *,
        dpi_slots: int = 10,
        quarantine_slots: int = 4,
        cpu_budget: int = 50,
        host_capacity: float = 100.0,
        warn: float = 0.35,
        cap: float = 0.40,
    ) -> None:
        self.capacity: dict[ResourceType, int] = {
            ResourceType.DPI_SLOT: dpi_slots,
            ResourceType.QUARANTINE_SLOT: quarantine_slots,
            ResourceType.CPU_BUDGET: cpu_budget,
        }
        self.allocated: dict[ResourceType, int] = dict.fromkeys(self.capacity, 0)
        self.host_capacity = host_capacity
        self.warn = warn
        self.cap = cap

    def _used_cost(self) -> float:
        return sum(self.allocated[t] * _COST[t] for t in self.allocated)

    def utilization(self) -> float:
        return self._used_cost() / self.host_capacity

    def grant(self, rtype: ResourceType, qty: int = 1) -> bool:
        if self.allocated[rtype] + qty > self.capacity[rtype]:
            return False
        projected = (self._used_cost() + qty * _COST[rtype]) / self.host_capacity
        if projected > self.cap:
            return False
        self.allocated[rtype] += qty
        return True

    def release(self, rtype: ResourceType, qty: int = 1) -> None:
        self.allocated[rtype] = max(0, self.allocated[rtype] - qty)

    def status(self) -> str:
        util = self.utilization()
        if util > self.cap:
            return "CRITICAL"
        if util > self.warn:
            return "WARNING"
        return "OK"
