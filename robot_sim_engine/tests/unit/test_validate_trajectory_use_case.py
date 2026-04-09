from __future__ import annotations

import numpy as np
<<<<<<< HEAD
import pytest
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

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
<<<<<<< HEAD



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
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
