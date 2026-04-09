from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_joint_trajectory import PlanJointTrajectoryUseCase
from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.model.trajectory import JointTrajectory


def test_validate_trajectory_reports_cache_recompute_metadata(planar_spec) -> None:
    req = TrajectoryRequest(
        q_start=np.array([0.0, 0.0]),
        q_goal=np.array([0.4, -0.1]),
        duration=1.0,
        dt=0.2,
        spec=planar_spec,
    )
    traj = PlanJointTrajectoryUseCase().execute(req)
    partial = JointTrajectory(
        t=traj.t,
        q=traj.q,
        qd=traj.qd,
        qdd=traj.qdd,
        ee_positions=traj.ee_positions[:-1],
        metadata={'cache_status': 'partial'},
    )
    report = ValidateTrajectoryUseCase().execute(partial, spec=planar_spec, q_goal=req.q_goal)

    assert report.metadata['cache_used'] is False
    assert report.metadata['cache_miss_reason'] == 'shape_mismatch'
    assert report.metadata['fk_recompute_samples'] == partial.q.shape[0]
    assert 'ee_positions_length_mismatch' in report.metadata['cache_integrity_errors']
    assert report.metadata['validation_layers'][-1] == 'limits'
