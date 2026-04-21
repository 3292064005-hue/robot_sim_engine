from __future__ import annotations

from robot_sim.infra.compatibility_usage import compatibility_usage_counts, compatibility_usage_snapshot, reset_compatibility_usage_counts


def test_compatibility_usage_snapshot_is_empty_when_no_retained_surfaces_exist() -> None:
    reset_compatibility_usage_counts()
    assert compatibility_usage_counts() == {}
    snapshot = compatibility_usage_snapshot()
    assert snapshot['surface_counts'] == {}
    assert snapshot['detail_counts'] == {}
