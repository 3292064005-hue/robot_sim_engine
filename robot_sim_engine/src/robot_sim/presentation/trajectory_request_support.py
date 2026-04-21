from __future__ import annotations

from collections.abc import Callable

import numpy as np

from robot_sim.application.dto import IKRequest, TrajectoryRequest
from robot_sim.application.request_builders import (
    build_execution_graph_descriptor,
    build_trajectory_request as build_trajectory_request_contract,
    normalize_validation_layers,
)
from robot_sim.domain.enums import TrajectoryMode
from robot_sim.presentation.validators.input_validator import InputValidator


def build_motion_trajectory_request(
    *,
    state_store,
    ik_builder: Callable[..., IKRequest],
    trajectory_goal_provider: Callable[[], np.ndarray],
    default_duration: float,
    default_dt: float,
    default_validation_layers: tuple[str, ...] | None,
    default_pipeline_id: str | None,
    q_goal=None,
    duration=None,
    dt=None,
    mode: str = 'joint_space',
    target_values6=None,
    orientation_mode: str = 'rvec',
    ik_kwargs: dict[str, object] | None = None,
    validation_layers: tuple[str, ...] | list[str] | None = None,
    planner_id: str | None = None,
    pipeline_id: str | None = None,
    execution_graph: dict[str, object] | None = None,
) -> TrajectoryRequest:
    """Build the canonical trajectory request for presentation-side workflows.

    This helper centralizes GUI-side trajectory request assembly so workflow services and
    legacy controller wrappers cannot drift apart. The returned DTO is always produced by
    :mod:`robot_sim.application.request_builders`, which remains the application-level
    contract truth.

    Args:
        state_store: Session-backed state store providing the loaded robot, current joints,
            and planning scene.
        ik_builder: Callable used to build the canonical IK request for Cartesian planning.
        trajectory_goal_provider: Callable returning the currently accepted IK joint goal
            when the caller does not provide ``q_goal`` explicitly.
        default_duration: Fallback duration applied when the caller omits ``duration``.
        default_dt: Fallback sampling period applied when the caller omits ``dt``.
        default_validation_layers: Runtime-default validation stages applied when the caller
            does not specify ``validation_layers``.
        default_pipeline_id: Runtime-default named pipeline used when the caller omits
            ``pipeline_id``.
        q_goal: Optional explicit joint-space goal.
        duration: Optional trajectory duration override.
        dt: Optional sample period override.
        mode: ``joint_space`` or ``cartesian``.
        target_values6: Optional Cartesian target payload ``[x, y, z, rx, ry, rz]``.
        orientation_mode: Rotation decoding mode forwarded to ``ik_builder``.
        ik_kwargs: Optional IK keyword arguments used only for Cartesian planning.
        validation_layers: Optional validation-stage override.
        planner_id: Optional planner identifier override.
        pipeline_id: Optional named pipeline override.
        execution_graph: Optional execution-scope descriptor payload.

    Returns:
        TrajectoryRequest: Canonical trajectory request threaded through the runtime.

    Raises:
        RuntimeError: If no robot is loaded or Cartesian mode lacks a target pose.
        ValueError: If duration / dt / joint vectors / validation layers are invalid.
    """
    state = state_store.state
    if state.q_current is None or state.robot_spec is None:
        raise RuntimeError('robot not loaded')

    resolved_duration = default_duration if duration is None else duration
    resolved_dt = default_dt if dt is None else dt
    resolved_duration, resolved_dt = InputValidator.validate_duration_and_dt(resolved_duration, resolved_dt)
    trajectory_mode = TrajectoryMode(str(mode))

    if validation_layers in (None, (), []):
        resolved_validation_layers = default_validation_layers
    else:
        resolved_validation_layers = normalize_validation_layers(validation_layers)

    descriptor = build_execution_graph_descriptor(state.robot_spec, execution_graph)
    common_kwargs = {
        'spec': state.robot_spec,
        'planning_scene': state.planning_scene,
        'validation_layers': resolved_validation_layers,
        'planner_id': None if planner_id in (None, '') else str(planner_id),
        'pipeline_id': str(default_pipeline_id or 'default') if pipeline_id in (None, '') else str(pipeline_id),
        'execution_graph': descriptor,
    }

    if trajectory_mode is TrajectoryMode.CARTESIAN:
        if target_values6 is None:
            raise RuntimeError('笛卡尔轨迹需要目标位姿')
        built_ik = ik_builder(target_values6, orientation_mode=str(orientation_mode), **dict(ik_kwargs or {}))
        return build_trajectory_request_contract(
            q_start=state.q_current.copy(),
            q_goal=None,
            duration=resolved_duration,
            dt=resolved_dt,
            mode=trajectory_mode,
            target_pose=built_ik.target,
            ik_config=built_ik.config,
            **common_kwargs,
        )

    goal = trajectory_goal_provider() if q_goal is None else q_goal
    validated_goal = InputValidator.validate_joint_vector(state.robot_spec, goal, clamp=True)
    return build_trajectory_request_contract(
        q_start=state.q_current.copy(),
        q_goal=np.asarray(validated_goal, dtype=float),
        duration=resolved_duration,
        dt=resolved_dt,
        mode=trajectory_mode,
        **common_kwargs,
    )
