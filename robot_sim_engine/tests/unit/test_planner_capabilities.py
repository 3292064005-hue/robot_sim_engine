from __future__ import annotations

from robot_sim.application.planner_capabilities import (
    planner_capability_map,
    planner_descriptor_snapshot,
    planner_mode_options,
    resolve_default_planner_id,
)


def test_planner_capability_defaults_drive_ui_modes_and_resolution() -> None:
    assert planner_mode_options() == ('joint_space', 'cartesian_pose')
    assert resolve_default_planner_id('joint_space') == 'joint_quintic'
    assert resolve_default_planner_id('cartesian_pose') == 'cartesian_sampled'
    assert resolve_default_planner_id('joint_space', waypoint_graph_present=True) == 'waypoint_graph'


def test_planner_capability_snapshot_contains_hidden_registry_capabilities() -> None:
    snapshot = planner_descriptor_snapshot()
    assert snapshot['joint_trapezoidal']['ui_visible'] is False
    assert snapshot['waypoint_graph']['status'] == 'experimental'
    assert planner_capability_map()['cartesian_sampled'].as_metadata()['requires_ik'] is True
