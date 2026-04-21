from __future__ import annotations

import numpy as np

from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.registries.planner_registry import build_default_planner_registry
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.ik_result import IKResult
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.ik_controller import IKController
from robot_sim.presentation.controllers.trajectory_controller import TrajectoryController
from robot_sim.presentation.state_store import StateStore


def test_trajectory_controller_builds_joint_request(project_root):
    cfg = ConfigService(project_root / 'configs')
    state = StateStore(SessionState())
    fk_uc = RunFKUseCase()
    spec = None
    from robot_sim.application.services.robot_registry import RobotRegistry
    spec = RobotRegistry(project_root / 'configs' / 'robots').load('planar_2dof')
    fk = fk_uc.execute(type('FKReq', (), {'spec': spec, 'q': spec.home_q.copy()})())
    state.patch(robot_spec=spec, q_current=spec.home_q.copy(), fk_result=fk, ik_result=IKResult(True, np.array([0.1, -0.1]), tuple(), 'ok'))
    ik_uc = RunIKUseCase(DefaultSolverRegistry())
    traj_uc = PlanTrajectoryUseCase(build_default_planner_registry(ik_uc))
    ik_ctrl = IKController(state, cfg.load_solver_config()['ik'], fk_uc, ik_uc)
    traj_ctrl = TrajectoryController.from_solver_settings(state, traj_uc, PlaybackService(), ik_ctrl.build_ik_request, cfg.load_solver_settings())
    req = traj_ctrl.build_trajectory_request(duration=1.0, dt=0.1)
    assert req.q_goal is not None
    assert req.mode.value == 'joint_space'


def test_trajectory_controller_uses_configured_default_validation_layers(project_root):
    cfg = ConfigService(project_root / 'configs', profile='release')
    state = StateStore(SessionState())
    fk_uc = RunFKUseCase()
    from robot_sim.application.services.robot_registry import RobotRegistry
    spec = RobotRegistry(project_root / 'configs' / 'robots').load('planar_2dof')
    fk = fk_uc.execute(type('FKReq', (), {'spec': spec, 'q': spec.home_q.copy()})())
    state.patch(robot_spec=spec, q_current=spec.home_q.copy(), fk_result=fk, ik_result=IKResult(True, np.array([0.1, -0.1]), tuple(), 'ok'))
    ik_uc = RunIKUseCase(DefaultSolverRegistry())
    traj_uc = PlanTrajectoryUseCase(build_default_planner_registry(ik_uc))
    ik_ctrl = IKController(state, cfg.load_solver_config()['ik'], fk_uc, ik_uc)
    traj_ctrl = TrajectoryController.from_solver_settings(
        state,
        traj_uc,
        PlaybackService(),
        ik_ctrl.build_ik_request,
        cfg.load_solver_settings(),
    )
    req = traj_ctrl.build_trajectory_request(duration=1.0, dt=0.1)
    assert req.validation_layers == cfg.load_solver_settings().trajectory.validation_layers


def test_trajectory_controller_uses_configured_default_timing(project_root):
    cfg = ConfigService(project_root / 'configs', profile='research')
    state = StateStore(SessionState())
    fk_uc = RunFKUseCase()
    from robot_sim.application.services.robot_registry import RobotRegistry
    spec = RobotRegistry(project_root / 'configs' / 'robots').load('planar_2dof')
    fk = fk_uc.execute(type('FKReq', (), {'spec': spec, 'q': spec.home_q.copy()})())
    state.patch(robot_spec=spec, q_current=spec.home_q.copy(), fk_result=fk, ik_result=IKResult(True, np.array([0.1, -0.1]), tuple(), 'ok'))
    ik_uc = RunIKUseCase(DefaultSolverRegistry())
    traj_uc = PlanTrajectoryUseCase(build_default_planner_registry(ik_uc))
    ik_ctrl = IKController(state, cfg.load_solver_config()['ik'], fk_uc, ik_uc)
    solver_settings = cfg.load_solver_settings()
    traj_ctrl = TrajectoryController.from_solver_settings(
        state,
        traj_uc,
        PlaybackService(),
        ik_ctrl.build_ik_request,
        solver_settings,
    )
    req = traj_ctrl.build_trajectory_request()
    assert req.duration == solver_settings.trajectory.duration
    assert req.dt == solver_settings.trajectory.dt
    assert req.pipeline_id == solver_settings.trajectory.pipeline_id
