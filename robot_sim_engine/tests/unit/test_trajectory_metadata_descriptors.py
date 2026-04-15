from __future__ import annotations

from robot_sim.application.trajectory_metadata import build_planner_metadata, resolve_planner_metadata


def test_resolve_planner_metadata_enriches_descriptor_fields() -> None:
    resolved = resolve_planner_metadata({'planner_id': 'cartesian_sampled'})
    assert resolved['planner_label'] == 'Cartesian sampled planner'
    assert resolved['trajectory_mode'] == 'cartesian_pose'
    assert resolved['requires_ik'] is True
    assert resolved['stable_surface'] is True


def test_build_planner_metadata_preserves_descriptor_defaults() -> None:
    payload = build_planner_metadata(planner_id='joint_quintic', goal_source='joint_space')
    assert payload['planner_label'] == 'Joint quintic planner'
    assert payload['family'] == 'joint'
    assert payload['status'] == 'stable'
    assert payload['ui_visible'] is True
