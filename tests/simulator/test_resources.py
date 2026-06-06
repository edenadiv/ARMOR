from cdmas.common.models.enums import ResourceType
from cdmas.simulator.resources import ResourcePool


def test_grant_within_capacity_and_cap():
    pool = ResourcePool(dpi_slots=10, host_capacity=100, cap=0.40)
    assert pool.grant(ResourceType.DPI_SLOT, 2) is True  # cost 6 -> 6%
    assert pool.utilization() == 0.06


def test_grant_rejected_over_host_cap():
    pool = ResourcePool(dpi_slots=100, host_capacity=100, cap=0.40)
    assert pool.grant(ResourceType.DPI_SLOT, 13) is True  # 39%
    assert pool.grant(ResourceType.DPI_SLOT, 1) is False  # would be 42% > 40%
    assert pool.utilization() == 0.39


def test_grant_rejected_over_resource_capacity():
    pool = ResourcePool(quarantine_slots=2, host_capacity=1000)
    assert pool.grant(ResourceType.QUARANTINE_SLOT, 2) is True
    assert pool.grant(ResourceType.QUARANTINE_SLOT, 1) is False  # capacity exhausted


def test_status_thresholds_and_release():
    pool = ResourcePool(dpi_slots=100, host_capacity=100, warn=0.35, cap=0.40)
    pool.grant(ResourceType.DPI_SLOT, 12)  # 36% -> WARNING
    assert pool.status() == "WARNING"
    pool.release(ResourceType.DPI_SLOT, 12)
    assert pool.status() == "OK"
