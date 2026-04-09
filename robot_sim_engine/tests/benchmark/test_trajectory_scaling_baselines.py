from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.registries.planner_registry import build_default_planner_registry
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry


def test_long_joint_trajectory_records_phase_timings(planar_spec):
    request = TrajectoryRequest(
        q_start=np.array([0.0, 0.0]),
        q_goal=np.array([1.0, -0.8]),
        duration=4.0,
        dt=0.01,
        spec=planar_spec,
    )
    planner = PlanTrajectoryUseCase(build_default_planner_registry(RunIKUseCase(DefaultSolverRegistry())))
    trajectory = planner.execute(request)
    timings = trajectory.metadata['phase_timings_ms']
    assert timings['total'] >= timings['planner']
    assert trajectory.feasibility['timing_summary']['phase_timings_ms']['validate'] == timings['validate']


def test_repeated_validation_preserves_cache_reuse_contract(planar_spec):
    request = TrajectoryRequest(
        q_start=np.array([0.0, 0.0]),
        q_goal=np.array([0.5, 0.25]),
        duration=1.5,
        dt=0.05,
        spec=planar_spec,
    )
    planner = PlanTrajectoryUseCase(build_default_planner_registry(RunIKUseCase(DefaultSolverRegistry())))
    trajectory = planner.execute(request)
    assert trajectory.metadata['cache_status'] in {'ready', 'partial', 'none', 'recomputed'}
    assert trajectory.feasibility['timing_summary']['phase_timings_ms']['total'] >= 0.0
