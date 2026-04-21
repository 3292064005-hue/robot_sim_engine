from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.domain.enums import AppExecutionState
from robot_sim.presentation.state_events import TrajectoryAppliedEvent
from robot_sim.presentation.trajectory_request_support import build_motion_trajectory_request
from robot_sim.model.solver_config import SolverSettings
from robot_sim.presentation.state_store import StateStore


class TrajectoryController:
    LEGACY_SURFACE_ID = 'compatibility.trajectory_controller.v1'

    """Legacy compatibility wrapper for trajectory planning interactions.

    Canonical GUI code should depend on :class:`robot_sim.presentation.workflow_services.MotionWorkflowService`.
    This controller is retained only for compatibility-facing surfaces and delegates request
    assembly to the same shared helper used by the canonical workflow so the contract cannot
    drift.
    """

    def __init__(
        self,
        state_store: StateStore,
        planner_uc: PlanTrajectoryUseCase,
        playback_service: PlaybackService,
        ik_builder,
        *,
        default_duration: float,
        default_dt: float,
        default_validation_layers: tuple[str, ...] | None,
        default_pipeline_id: str | None,
    ) -> None:
        """Initialize the compatibility trajectory controller with runtime-owned defaults.

        Args:
            state_store: Session-backed state store containing the loaded robot and planning scene.
            planner_uc: Use case that executes the canonical trajectory planning contract.
            playback_service: Service used to project resulting trajectories into playback state.
            ik_builder: Callable that builds canonical IK requests for Cartesian planning.
            default_duration: Runtime-owned default duration in seconds.
            default_dt: Runtime-owned default sample period in seconds.
            default_validation_layers: Runtime-owned default validation stage chain.
            default_pipeline_id: Runtime-owned default named trajectory pipeline.

        Raises:
            ValueError: If timing defaults are invalid.
        """
        self._state_store = state_store
        self._planner_uc = planner_uc
        self._playback_service = playback_service
        self._ik_builder = ik_builder
        self._default_duration = float(default_duration)
        self._default_dt = float(default_dt)
        self._default_validation_layers = tuple(str(item).strip() for item in (default_validation_layers or ())) or None
        self._default_pipeline_id = None if default_pipeline_id in (None, '') else str(default_pipeline_id)


    @classmethod
    def from_solver_settings(
        cls,
        state_store: StateStore,
        planner_uc: PlanTrajectoryUseCase,
        playback_service: PlaybackService,
        ik_builder,
        solver_settings: SolverSettings,
    ) -> 'TrajectoryController':
        """Create the controller from runtime solver settings.

        This is the canonical construction path for compatibility surfaces. It prevents
        callers from reintroducing hard-coded timing, validation, or pipeline defaults.
        """
        return cls(
            state_store,
            planner_uc,
            playback_service,
            ik_builder,
            default_duration=solver_settings.trajectory.duration,
            default_dt=solver_settings.trajectory.dt,
            default_validation_layers=solver_settings.trajectory.validation_layers,
            default_pipeline_id=solver_settings.trajectory.pipeline_id,
        )

    def trajectory_goal_or_raise(self) -> np.ndarray:
        result = self._state_store.state.ik_result
        if result is None or not result.success:
            raise RuntimeError('请先得到一个成功的 IK 解，再生成轨迹')
        return np.asarray(result.q_sol, dtype=float).copy()

    def build_trajectory_request(
        self,
        q_goal=None,
        duration=None,
        dt=None,
        *,
        mode: str = 'joint_space',
        target_values6=None,
        orientation_mode: str = 'rvec',
        ik_kwargs: dict | None = None,
        validation_layers: tuple[str, ...] | list[str] | None = None,
        planner_id: str | None = None,
        pipeline_id: str | None = None,
        execution_graph: dict[str, object] | None = None,
    ) -> TrajectoryRequest:
        """Build the canonical trajectory request for legacy controller callers.

        Args:
            q_goal: Optional explicit joint-space goal.
            duration: Optional requested trajectory duration in seconds. When omitted, the configured default is used.
            dt: Optional requested trajectory sample period in seconds. When omitted, the configured default is used.
            mode: ``joint_space`` or ``cartesian``.
            target_values6: Optional Cartesian target pose payload.
            orientation_mode: Rotation decoding mode forwarded to the IK builder.
            ik_kwargs: Optional IK override payload used only for Cartesian mode.
            validation_layers: Optional validation-stage override.
            planner_id: Optional planner identifier override.
            pipeline_id: Optional named pipeline override.
            execution_graph: Optional execution-scope descriptor payload.

        Returns:
            TrajectoryRequest: Typed request consumed by ``PlanTrajectoryUseCase``.

        Raises:
            RuntimeError: If no robot is loaded or Cartesian planning lacks a target pose.
            ValueError: If timing, validation layers, or joint vectors are invalid.
        """
        return build_motion_trajectory_request(
            state_store=self._state_store,
            ik_builder=self._ik_builder,
            trajectory_goal_provider=self.trajectory_goal_or_raise,
            default_duration=self._default_duration,
            default_dt=self._default_dt,
            default_validation_layers=self._default_validation_layers,
            default_pipeline_id=self._default_pipeline_id,
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

    def plan_trajectory(self, **kwargs):
        req = self.build_trajectory_request(**kwargs)
        result = self._planner_uc.execute(req)
        self.apply_trajectory(result)
        return result

    def apply_trajectory(self, traj) -> None:
        playback = self._playback_service.build_state(
            traj,
            frame_idx=0,
            speed_multiplier=self._state_store.state.playback.speed_multiplier,
            loop_enabled=self._state_store.state.playback.loop_enabled,
        )
        scene_revision = max(int(self._state_store.state.scene_revision), int(getattr(traj, 'scene_revision', 0)))
        scene_summary = {
            **dict(self._state_store.state.scene_summary),
            'scene_revision': int(getattr(traj, 'scene_revision', 0)),
            'trajectory_cache_status': str(getattr(traj, 'cache_status', 'none')),
        }
        self._state_store.dispatch(
            TrajectoryAppliedEvent(
                trajectory=traj,
                playback=playback,
                scene_revision=scene_revision,
                scene_summary=scene_summary,
                app_state=AppExecutionState.ROBOT_READY,
            )
        )
