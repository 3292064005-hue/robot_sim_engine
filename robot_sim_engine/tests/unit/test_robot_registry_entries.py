from __future__ import annotations

from robot_sim.application.services.robot_registry import RobotRegistry


def test_robot_registry_entries_use_loadable_identifiers(project_root):
    registry = RobotRegistry(project_root / "configs" / "robots")

    entries = registry.list_entries()

    assert entries
    for entry in entries:
        spec = registry.load(entry.name)
        assert spec.name == entry.name
        assert spec.label == entry.label
