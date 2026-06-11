import pytest

from cdmas.validator.export import build_export
from cdmas.validator.scenarios import SCENARIOS


@pytest.mark.slow
async def test_build_export_structure():
    data = await build_export()

    assert [r["scenario"] for r in data["replays"]] == [name for name, _, _ in SCENARIOS]
    for replay in data["replays"]:
        assert replay["events"]
        assert "metrics" in replay
        assert replay["duration_ms"] > 0
        assert set(replay["topology"]["adjacency"]) == set(replay["topology"]["segments"])

    assert data["replays"][0]["topology"]["segments"] == ["public-facing"]
    contention = next(r for r in data["replays"] if "Contention" in r["scenario"])
    assert set(contention["topology"]["segments"]) == {
        "internal",
        "server",
        "public-facing",
        "sec-mon",
    }

    assert len(data["validation"]) == 6
    assert all("constraints" in v for v in data["validation"])
