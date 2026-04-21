from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.application.dto import FKRequest, IKRequest
from robot_sim.application.request_builders import (
    build_execution_graph_descriptor,
    build_ik_config,
    build_ik_request as build_ik_request_contract,
    build_pose_from_values6,
    build_trajectory_request as build_trajectory_request_contract,
    normalize_validation_layers,
)
from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS
from robot_sim.application.services.playback_service import PlaybackFrame, PlaybackService
from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.domain.enums import AppExecutionState, IKSolverMode, TrajectoryMode
from robot_sim.model.imported_robot_result import ImportedRobotResult
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.pose import Pose
from robot_sim.model.runtime_snapshots import EnvironmentSnapshot
from robot_sim.model.solver_config import IKConfig, SolverSettings
from robot_sim.presentation.runtime_projection_service import RuntimeProjectionService
from robot_sim.presentation.trajectory_request_support import build_motion_trajectory_request
from robot_sim.presentation.state_events import (
    BenchmarkReportProjectedEvent,
    FKProjectedEvent,
    IKResultAppliedEvent,
    PlaybackStateChangedEvent,
    TrajectoryAppliedEvent,
    WarningProjectedEvent,
)
from robot_sim.presentation.validators.input_validator import InputValidator
from robot_sim.presentation.view_contracts import ExportWorkflowContract, MotionWorkflowContract, RobotWorkflowContract

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.application.registries.importer_registry import ImporterRegistry
    from robot_sim.application.services.export_service import ExportService
    from robot_sim.application.services.robot_registry import RobotRegistry
    from robot_sim.application.use_cases.export_package import ExportPackageUseCase
    from robot_sim.application.use_cases.export_report import ExportReportUseCase
    from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
    from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
    from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
    from robot_sim.application.use_cases.run_fk import RunFKUseCase
    from robot_sim.application.use_cases.run_ik import RunIKUseCase
    from robot_sim.application.use_cases.save_session import SaveSessionUseCase
    from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
    from robot_sim.app.workflow_facade import ApplicationWorkflowFacade
    from robot_sim.model.benchmark_report import BenchmarkReport
    from robot_sim.model.robot_spec import RobotSpec
    from robot_sim.model.trajectory import JointTrajectory
    from robot_sim.presentation.controllers.robot_controller import RobotController
    from robot_sim.presentation.facades import RuntimeFacade
    from robot_sim.presentation.state_store import StateStore


@dataclass(frozen=True)
class MotionWorkflowService(MotionWorkflowContract):
    """Canonical motion capability port consumed by Qt tasks and widgets.

    The workflow owns IK, trajectory, playback, and benchmark logic directly so new
    presentation code does not need controller pass-through layers to reach the runtime.
    Legacy controller wrappers must delegate back into this workflow or shared helpers rather
    than rebuilding trajectory DTOs independently.
    """

    solver_settings: 'SolverSettings'
    state_store: 'StateStore'
    fk_uc: 'RunFKUseCase'
    ik_use_case: 'RunIKUseCase'
    trajectory_use_case: 'PlanTrajectoryUseCase'
    benchmark_use_case: 'RunBenchmarkUseCase'
    playback_service: 'PlaybackService'
    playback_use_case: 'StepPlaybackUseCase'
    runtime_asset_service: object | None = None
    application_workflow: 'ApplicationWorkflowFacade | None' = None

    def _application_workflow_or_raise(self):
        if self.application_workflow is None:
            raise RuntimeError('application workflow facade is not configured')
        return self.application_workflow

    @staticmethod
    def _parse_mode(value: object) -> IKSolverMode | str:
        token = str(value)
        try:
            return IKSolverMode(token)
        except ValueError:
            return token

    def solver_defaults(self) -> dict[str, object]:
        """Return the canonical IK defaults projected from ``SolverSettings``."""
        return self.solver_settings.ik.as_dict()

    def trajectory_defaults(self) -> dict[str, object]:
        """Return the canonical trajectory defaults projected from ``SolverSettings``."""
        return self.solver_settings.trajectory.as_dict()

    def build_target_pose(self, values6, orientation_mode: str = 'rvec') -> Pose:
        """Build a typed target pose from the UI/session 6-vector payload."""
        values6 = InputValidator.validate_target_values(values6)
        return build_pose_from_values6(values6, orientation_mode=orientation_mode, error_factory=ValueError)

    def _ik_config_payload_from_kwargs(self, kwargs: dict[str, object]) -> dict[str, object]:
        defaults = self.solver_settings.ik.as_dict()
        payload = {
            'mode': kwargs.get('mode', defaults.get('mode', 'dls')),
            'max_iters': kwargs.get('max_iters', defaults.get('max_iters', 150)),
            'step_scale': kwargs.get('step_scale', defaults.get('step_scale', 0.5)),
            'damping_lambda': kwargs.get('damping', defaults.get('damping_lambda', 0.05)),
            'enable_nullspace': kwargs.get('enable_nullspace', defaults.get('enable_nullspace', True)),
            'position_only': kwargs.get('position_only', defaults.get('position_only', False)),
            'pos_tol': kwargs.get('pos_tol', defaults.get('pos_tol', 1e-4)),
            'ori_tol': kwargs.get('ori_tol', defaults.get('ori_tol', 1e-4)),
            'max_step_norm': kwargs.get('max_step_norm', defaults.get('max_step_norm', 0.35)),
            'fallback_to_dls_when_singular': kwargs.get('auto_fallback', defaults.get('fallback_to_dls_when_singular', True)),
            'reachability_precheck': kwargs.get('reachability_precheck', defaults.get('reachability_precheck', True)),
            'retry_count': max(int(kwargs.get('retry_count', defaults.get('retry_count', 0))), 0),
            'random_seed': defaults.get('random_seed', 7),
            'joint_limit_weight': defaults.get('joint_limit_weight', 0.03) if kwargs.get('joint_limit_weight') is None else kwargs['joint_limit_weight'],
            'manipulability_weight': defaults.get('manipulability_weight', 0.0) if kwargs.get('manipulability_weight') is None else kwargs['manipulability_weight'],
            'orientation_weight': defaults.get('orientation_weight', 1.0) if kwargs.get('orientation_weight') is None else kwargs['orientation_weight'],
            'adaptive_damping': defaults.get('adaptive_damping', True) if kwargs.get('adaptive_damping') is None else kwargs['adaptive_damping'],
            'min_damping_lambda': defaults.get('min_damping_lambda', 1.0e-4),
            'max_damping_lambda': defaults.get('max_damping_lambda', 1.5),
            'use_weighted_least_squares': defaults.get('use_weighted_least_squares', True) if kwargs.get('use_weighted_least_squares') is None else kwargs['use_weighted_least_squares'],
            'clamp_seed_to_joint_limits': defaults.get('clamp_seed_to_joint_limits', True) if kwargs.get('clamp_seed_to_joint_limits') is None else kwargs['clamp_seed_to_joint_limits'],
            'normalize_target_rotation': defaults.get('normalize_target_rotation', True) if kwargs.get('normalize_target_rotation') is None else kwargs['normalize_target_rotation'],
            'allow_orientation_relaxation': defaults.get('allow_orientation_relaxation', False) if kwargs.get('allow_orientation_relaxation') is None else kwargs['allow_orientation_relaxation'],
            'orientation_relaxation_pos_multiplier': defaults.get('orientation_relaxation_pos_multiplier', 5.0) if kwargs.get('orientation_relaxation_pos_multiplier') is None else kwargs['orientation_relaxation_pos_multiplier'],
            'orientation_relaxation_ori_multiplier': defaults.get('orientation_relaxation_ori_multiplier', 25.0) if kwargs.get('orientation_relaxation_ori_multiplier') is None else kwargs['orientation_relaxation_ori_multiplier'],
        }
        return payload

    def build_ik_request(self, values6, **kwargs) -> IKRequest:
        """Build the canonical IK request for the currently loaded robot.

        Args:
            values6: Target pose payload ``[x, y, z, rx, ry, rz]``.
            **kwargs: Optional IK override fields such as ``mode``, tolerances, retry policy,
                and ``execution_graph``.

        Returns:
            IKRequest: Typed request consumed by ``RunIKUseCase``.

        Raises:
            RuntimeError: If no robot is loaded into the state store.
            ValueError: If target values or IK configuration are invalid.
        """
        spec = self.state_store.state.robot_spec
        q0 = self.state_store.state.q_current
        if spec is None or q0 is None:
            raise RuntimeError('robot not loaded')
        target = self.build_target_pose(values6, orientation_mode=str(kwargs.get('orientation_mode', 'rvec')))
        config = build_ik_config(self._ik_config_payload_from_kwargs(kwargs), defaults=self.solver_settings.ik)
        execution_graph = build_execution_graph_descriptor(spec, kwargs.get('execution_graph'))
        return build_ik_request_contract(spec=spec, q0=q0.copy(), target=target, config=config, execution_graph=execution_graph)

    def build_benchmark_config(self, **kwargs):
        """Build the benchmark IK config anchored at the current FK end-effector pose."""
        pose = self.state_store.state.fk_result.ee_pose if self.state_store.state.fk_result is not None else None
        values6 = [0.0] * 6 if pose is None else list(np.asarray(pose.p, dtype=float)) + [0.0, 0.0, 0.0]
        request = self.build_ik_request(values6, **kwargs)
        return request.config

    def run_benchmark(self, config=None, *, execution_graph=None):
        """Execute the benchmark use case against the loaded robot and project the result."""
        spec = self.state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        resolved = config or self.build_benchmark_config(execution_graph=execution_graph)
        descriptor = build_execution_graph_descriptor(spec, execution_graph)
        workflow = self._application_workflow_or_raise()
        report = workflow.run_benchmark(spec, config=resolved, execution_graph=descriptor)
        self.state_store.dispatch(BenchmarkReportProjectedEvent(benchmark_report=report))
        return report

    def trajectory_goal_or_raise(self) -> np.ndarray:
        """Return the accepted IK joint solution used as the default trajectory goal."""
        result = self.state_store.state.ik_result
        if result is None or not result.success:
            raise RuntimeError('请先得到一个成功的 IK 解，再生成轨迹')
        return np.asarray(result.q_sol, dtype=float).copy()

    def build_trajectory_request(self, **kwargs):
        """Build the canonical trajectory request for GUI tasks and widgets.

        Supported keyword arguments are ``q_goal``, ``duration``, ``dt``, ``mode``,
        ``target_values6``, ``orientation_mode``, ``ik_kwargs``, ``validation_layers``,
        ``planner_id``, ``pipeline_id``, and ``execution_graph``.

        Returns:
            TrajectoryRequest: Typed request consumed by ``PlanTrajectoryUseCase``.

        Raises:
            RuntimeError: If no robot is loaded or Cartesian planning lacks a target pose.
            ValueError: If timing, validation layers, or joint vectors are invalid.
            TypeError: If unsupported keyword arguments are supplied.
        """
        q_goal = kwargs.pop('q_goal', None)
        duration = kwargs.pop('duration', None)
        dt = kwargs.pop('dt', None)
        mode = str(kwargs.pop('mode', 'joint_space'))
        planner_id = kwargs.pop('planner_id', None)
        pipeline_id = kwargs.pop('pipeline_id', None)
        target_values6 = kwargs.pop('target_values6', None)
        orientation_mode = str(kwargs.pop('orientation_mode', 'rvec'))
        ik_kwargs = kwargs.pop('ik_kwargs', None)
        validation_layers = kwargs.pop('validation_layers', None)
        execution_graph = kwargs.pop('execution_graph', None)
        if kwargs:
            raise TypeError(f'unsupported trajectory workflow kwargs: {sorted(kwargs)}')
        return build_motion_trajectory_request(
            state_store=self.state_store,
            ik_builder=self.build_ik_request,
            trajectory_goal_provider=self.trajectory_goal_or_raise,
            default_duration=self.solver_settings.trajectory.duration,
            default_dt=self.solver_settings.trajectory.dt,
            default_validation_layers=self.solver_settings.trajectory.validation_layers,
            default_pipeline_id=self.solver_settings.trajectory.pipeline_id,
            q_goal=q_goal,
            duration=duration,
            dt=dt,
            mode=mode,
            target_values6=target_values6,
            orientation_mode=orientation_mode,
            ik_kwargs=ik_kwargs,
            validation_layers=validation_layers,
            planner_id=planner_id,
            pipeline_id=pipeline_id,
            execution_graph=execution_graph,
        )

    def apply_ik_result(self, req, result) -> None:
        """Project IK results back into session state and refresh FK."""
        q_current = result.q_sol.copy() if result.success else (result.best_q.copy() if result.best_q is not None else req.q0.copy())
        fk_result = self.fk_uc.execute(FKRequest(req.spec, q_current))
        self.state_store.dispatch(
            IKResultAppliedEvent(
                target_pose=req.target,
                ik_result=result,
                q_current=q_current,
                fk_result=fk_result,
                scene_revision=self.state_store.state.scene_revision + 1,
            )
        )

    def run_ik(self, values6, **kwargs):
        """Execute IK and immediately project the resulting state transition."""
        request = self.build_ik_request(values6, **kwargs)
        workflow = self._application_workflow_or_raise()
        result = workflow.run_ik(request.spec, target=request.target, q0=request.q0, config=request.config, execution_graph=request.execution_graph)
        self.apply_ik_result(request, result)
        return result

    def plan_trajectory(self, **kwargs):
        """Execute trajectory planning and project playback/cache state."""
        request = self.build_trajectory_request(**kwargs)
        workflow = self._application_workflow_or_raise()
        result = workflow.plan_trajectory(request.spec, q_start=request.q_start, q_goal=request.q_goal, duration=request.duration, dt=request.dt, mode=request.mode, target_pose=request.target_pose, ik_config=request.ik_config, planner_id=request.planner_id, max_velocity=request.max_velocity, max_acceleration=request.max_acceleration, validation_layers=request.validation_layers, pipeline_id=request.pipeline_id, execution_graph=request.execution_graph)
        self.apply_trajectory(result)
        return result

    def apply_trajectory(self, traj) -> None:
        """Project a planned trajectory into playback-ready session state."""
        playback = self.playback_service.build_state(
            traj,
            frame_idx=0,
            speed_multiplier=self.state_store.state.playback.speed_multiplier,
            loop_enabled=self.state_store.state.playback.loop_enabled,
        )
        scene_revision = max(int(self.state_store.state.scene_revision), int(getattr(traj, 'scene_revision', 0)))
        scene_summary = {
            **dict(self.state_store.state.scene_summary),
            'scene_revision': int(getattr(traj, 'scene_revision', 0)),
            'trajectory_cache_status': str(getattr(traj, 'cache_status', 'none')),
        }
        self.state_store.dispatch(
            TrajectoryAppliedEvent(
                trajectory=traj,
                playback=playback,
                scene_revision=scene_revision,
                scene_summary=scene_summary,
                app_state=AppExecutionState.ROBOT_READY,
            )
        )

    def current_playback_frame(self) -> PlaybackFrame:
        """Return the current playback frame for the active trajectory."""
        trajectory = self._trajectory_or_raise(strict=True)
        return self.playback_use_case.current(trajectory, self.state_store.state.playback)

    def set_playback_frame(self, frame_idx: int):
        """Move playback to a specific frame and project the resulting state."""
        trajectory = self._trajectory_or_raise(strict=True)
        state = self.state_store.state.playback.with_frame(frame_idx)
        frame = self.playback_service.frame(trajectory, state.frame_idx)
        self.state_store.dispatch(PlaybackStateChangedEvent(playback=state))
        return frame

    def next_playback_frame(self):
        """Advance playback by one step and return the projected frame."""
        trajectory = self._trajectory_or_raise(strict=True)
        state, frame = self.playback_use_case.next(trajectory, self.state_store.state.playback)
        self.state_store.dispatch(PlaybackStateChangedEvent(playback=state))
        return frame

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None:
        """Update playback speed/loop flags while preserving the current frame."""
        playback = self.state_store.state.playback
        if speed_multiplier is not None:
            playback = PlaybackState(
                is_playing=playback.is_playing,
                frame_idx=playback.frame_idx,
                total_frames=playback.total_frames,
                speed_multiplier=max(float(speed_multiplier), 0.05),
                loop_enabled=playback.loop_enabled if loop_enabled is None else bool(loop_enabled),
            )
        elif loop_enabled is not None:
            playback = PlaybackState(
                is_playing=playback.is_playing,
                frame_idx=playback.frame_idx,
                total_frames=playback.total_frames,
                speed_multiplier=playback.speed_multiplier,
                loop_enabled=bool(loop_enabled),
            )
        self.state_store.dispatch(PlaybackStateChangedEvent(playback=playback))

    def ensure_playback_ready(self, strict: bool = True) -> None:
        """Validate that the active trajectory exposes playback-critical caches."""
        trajectory = self._trajectory_or_raise(strict=strict)
        self.playback_service.ensure_playback_ready(trajectory, strict=strict)

    def _trajectory_or_raise(self, *, strict: bool = True):
        trajectory = self.state_store.state.trajectory
        if trajectory is None:
            raise RuntimeError('trajectory not available')
        if strict:
            self.playback_service.ensure_playback_ready(trajectory, strict=True)
        elif not trajectory.has_cached_joint_positions and trajectory.cache_status in {'ready', 'partial', 'recomputed'}:
            raise RuntimeError('trajectory cache is inconsistent: missing joint_positions')
        return trajectory


