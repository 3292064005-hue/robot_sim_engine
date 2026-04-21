from __future__ import annotations

import numpy as np
import pytest

from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.model.trajectory import JointTrajectory


def test_validate_trajectory_reports_quality_metrics():
    t = np.linspace(0.0, 1.0, 5)
    q = np.column_stack([t, t ** 2])
    qd = np.gradient(q, t, axis=0)
    qdd = np.gradient(qd, t, axis=0)
    ee = np.column_stack([t, np.zeros_like(t), np.zeros_like(t)])
    rots = np.repeat(np.eye(3)[None, :, :], t.shape[0], axis=0)
    traj = JointTrajectory(t=t, q=q, qd=qd, qdd=qdd, ee_positions=ee, ee_rotations=rots)

    report = ValidateTrajectoryUseCase().execute(traj)

    assert report.feasible is True
    assert report.path_length > 0.0
    assert report.max_velocity > 0.0
    assert report.metadata['num_samples'] == 5


def test_validate_trajectory_flags_non_monotonic_time():
    traj = JointTrajectory(
        t=np.array([0.0, 0.3, 0.2]),
        q=np.zeros((3, 1)),
        qd=np.zeros((3, 1)),
        qdd=np.zeros((3, 1)),
    )
    report = ValidateTrajectoryUseCase().execute(traj)
    assert report.feasible is False
    assert 'non_monotonic_time' in report.reasons



def test_validate_trajectory_supports_explicit_validation_layers() -> None:
    traj = JointTrajectory(
        t=np.array([0.0, 0.1, 0.2], dtype=float),
        q=np.array([[0.0, 0.0], [0.1, 0.1], [0.2, 0.2]], dtype=float),
        qd=np.zeros((3, 2), dtype=float),
        qdd=np.zeros((3, 2), dtype=float),
    )
    report = ValidateTrajectoryUseCase().execute(traj, validation_layers=('timing', 'limits'))
    assert report.metadata['validation_layers'] == ['timing', 'limits']
    assert report.metadata['collision_summary'] == {}



def test_validate_trajectory_rejects_unknown_validation_layers() -> None:
    traj = JointTrajectory(
        t=np.array([0.0, 0.1], dtype=float),
        q=np.array([[0.0, 0.0], [0.1, 0.1]], dtype=float),
        qd=np.zeros((2, 2), dtype=float),
        qdd=np.zeros((2, 2), dtype=float),
    )
    with pytest.raises(ValueError, match='unsupported validation layer'):
        ValidateTrajectoryUseCase().execute(traj, validation_layers=('timing', 'bogus'))



def test_validate_trajectory_rejects_shape_mismatch() -> None:
    traj = JointTrajectory(
        t=np.array([0.0, 0.1], dtype=float),
        q=np.array([[0.0, 0.0], [0.1, 0.1]], dtype=float),
        qd=np.zeros((1, 2), dtype=float),
        qdd=np.zeros((2, 2), dtype=float),
    )
    with pytest.raises(ValueError, match='trajectory.qd shape must match trajectory.q'):
        ValidateTrajectoryUseCase().execute(traj)



def test_validate_trajectory_projects_scene_validation_summary_for_planning_scene() -> None:
    from robot_sim.core.collision.geometry import AABB
    from robot_sim.core.collision.scene import PlanningScene

    traj = JointTrajectory(
        t=np.array([0.0, 0.1], dtype=float),
        q=np.zeros((2, 2), dtype=float),
        qd=np.zeros((2, 2), dtype=float),
        qdd=np.zeros((2, 2), dtype=float),
        joint_positions=np.array(
            [
                [[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.8, 0.0, 0.0]],
                [[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.8, 0.0, 0.0]],
            ],
            dtype=float,
        ),
    )
    scene = PlanningScene().add_obstacle('box', AABB(np.array([0.2, -0.1, -0.1], dtype=float), np.array([0.6, 0.1, 0.1], dtype=float)))
    report = ValidateTrajectoryUseCase().execute(traj, planning_scene=scene)
    summary = report.metadata['scene_validation_summary']
    assert summary['scene_source'] == 'planning_scene'
    assert report.metadata['collision_summary']['collision_input'] == 'planning_scene'


def test_validate_trajectory_reports_no_scene_validation_when_scene_is_missing() -> None:
    traj = JointTrajectory(
        t=np.array([0.0, 0.1], dtype=float),
        q=np.zeros((2, 2), dtype=float),
        qd=np.zeros((2, 2), dtype=float),
        qdd=np.zeros((2, 2), dtype=float),
        joint_positions=np.array(
            [
                [[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.8, 0.0, 0.0]],
                [[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.8, 0.0, 0.0]],
            ],
            dtype=float,
        ),
    )
    report = ValidateTrajectoryUseCase().execute(traj)
    summary = report.metadata['scene_validation_summary']
    assert summary['scene_validation_effective'] is False
    assert summary['scene_validation_mode'] == 'none'
    assert summary['scene_validation_precision'] == 'none'
    assert summary['scene_source'] == 'none'
    assert report.metadata['collision_summary']['collision_input'] == 'none'
