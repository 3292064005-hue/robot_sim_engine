from __future__ import annotations

import numpy as np

from robot_sim.application.validators.collision_validator import evaluate_collision_summary
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.core.collision.scene import PlanningScene, SceneObject
from robot_sim.model.trajectory import JointTrajectory


def _trajectory() -> JointTrajectory:
    joint_positions = np.array([
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0.2, 0.1, 0]],
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0.2, 0.1, 0]],
    ], dtype=float)
    return JointTrajectory(
        t=np.array([0.0, 1.0]),
        q=np.zeros((2, 3)),
        qd=np.zeros((2, 3)),
        qdd=np.zeros((2, 3)),
        joint_positions=joint_positions,
        ee_positions=np.array([[0, 0, 0], [1, 0, 0]], dtype=float),
    )


def test_collision_summary_reports_backend_and_cache_state():
    traj = _trajectory()
    obstacle = SceneObject('wall', aabb_from_points(np.array([[0.0, -0.1, -0.1], [1.1, 0.2, 0.1]], dtype=float), padding=0.0))
    scene = PlanningScene(obstacles=(obstacle,), revision=2)

    _, first_summary = evaluate_collision_summary(traj, planning_scene=scene)
    _, second_summary = evaluate_collision_summary(traj, planning_scene=scene)

    assert first_summary['resolved_backend'] == 'aabb'
    assert first_summary['requested_backend'] == 'aabb'
    assert first_summary['cache_hit'] is False
    assert first_summary['candidate_pair_count'] > 0
    assert first_summary['backend_evidence']['resolved_backend'] == 'aabb'
    assert first_summary['geometry_contract_evidence']['scene_geometry_contract'] == first_summary['scene_geometry_contract']
    assert second_summary['cache_hit'] is True


def test_collision_summary_preserves_stable_capsule_backend_selection():
    traj = _trajectory()
    obstacle = SceneObject('wall', aabb_from_points(np.array([[0.0, -0.1, -0.1], [1.1, 0.2, 0.1]], dtype=float), padding=0.0))
    scene = PlanningScene(obstacles=(obstacle,), revision=3).with_collision_backend('capsule')

    _, summary = evaluate_collision_summary(traj, planning_scene=scene)

    assert summary['resolved_backend'] == 'capsule'
    assert summary['requested_backend'] == 'capsule'
    assert summary['backend_evidence']['resolved_backend'] == 'capsule'
    assert 'collision_backend_warning' not in summary
