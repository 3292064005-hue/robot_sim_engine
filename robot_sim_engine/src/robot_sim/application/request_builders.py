from __future__ import annotations

from collections.abc import Mapping
from typing import Callable

import numpy as np

from robot_sim.application.dto import IKRequest, TrajectoryRequest
from robot_sim.core.math.so3 import exp_so3
from robot_sim.core.math.transforms import rot_x, rot_y, rot_z
from robot_sim.domain.enums import IKSolverMode, TrajectoryMode
from robot_sim.application.services.execution_scope_service import ExecutionScopeService
from robot_sim.model.execution_graph import ExecutionGraphDescriptor, default_execution_graph_descriptor
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig


ErrorFactory = Callable[[str], Exception]


def _raise(error_factory: type[Exception] | ErrorFactory, message: str):
    raise error_factory(message)


def build_pose_from_values6(values6: object, *, orientation_mode: str = 'rvec', error_factory: type[Exception] | ErrorFactory = ValueError) -> Pose:
    """Build a pose from a 6-value GUI/session target payload.

    Args:
        values6: Sequence of ``[x, y, z, rx, ry, rz]`` or Euler-zyx values.
        orientation_mode: ``rvec`` or ``euler_zyx``.
        error_factory: Exception type/factory used for validation failures.

    Returns:
        Pose: Canonical pose value object.

    Raises:
        ValueError: When the payload is malformed, non-numeric, or non-finite.
    """
    try:
        flat = np.asarray(values6, dtype=float).reshape(6)
    except (TypeError, ValueError) as exc:
        _raise(error_factory, f'target values must be a numeric 6-vector: {exc}')
    if not np.isfinite(flat).all():
        _raise(error_factory, 'target values contain non-finite numbers')
    position = np.asarray(flat[:3], dtype=float)
    if str(orientation_mode) == 'euler_zyx':
        yaw, pitch, roll = flat[3:]
        rotation = rot_z(float(yaw)) @ rot_y(float(pitch)) @ rot_x(float(roll))
    else:
        rotation = exp_so3(np.asarray(flat[3:], dtype=float))
    return Pose(p=position, R=rotation)


def build_pose_from_mapping(raw: Mapping[str, object], *, error_factory: type[Exception] | ErrorFactory = ValueError) -> Pose:
    """Build a pose from a machine-readable mapping payload."""
    position_raw = raw.get('position', raw.get('p'))
    if position_raw is None:
        _raise(error_factory, 'pose.position must be present')
    try:
        position = np.asarray(position_raw, dtype=float).reshape(3)
    except (TypeError, ValueError) as exc:
        _raise(error_factory, f'pose.position must be a numeric 3-vector: {exc}')
    if raw.get('rotation_matrix') is not None:
        try:
            rotation = np.asarray(raw['rotation_matrix'], dtype=float).reshape(3, 3)
        except (TypeError, ValueError) as exc:
            _raise(error_factory, f'pose.rotation_matrix must be a numeric 3x3 matrix: {exc}')
    elif raw.get('rotation_rvec') is not None:
        try:
            rotation = exp_so3(np.asarray(raw['rotation_rvec'], dtype=float).reshape(3))
        except (TypeError, ValueError) as exc:
            _raise(error_factory, f'pose.rotation_rvec must be a numeric 3-vector: {exc}')
    elif raw.get('euler_zyx') is not None:
        try:
            yaw, pitch, roll = np.asarray(raw['euler_zyx'], dtype=float).reshape(3)
        except (TypeError, ValueError) as exc:
            _raise(error_factory, f'pose.euler_zyx must be a numeric 3-vector: {exc}')
        rotation = rot_z(float(yaw)) @ rot_y(float(pitch)) @ rot_x(float(roll))
    else:
        rotation = np.eye(3, dtype=float)
    if not np.isfinite(position).all() or not np.isfinite(rotation).all():
        _raise(error_factory, 'pose contains non-finite values')
    return Pose(p=position, R=rotation)


def build_ik_config(raw: object, *, defaults: IKConfig, error_factory: type[Exception] | ErrorFactory = ValueError) -> IKConfig:
    """Build an ``IKConfig`` by overlaying a mapping onto typed defaults."""
    payload = defaults.as_dict()
    if raw not in (None, ''):
        if not isinstance(raw, Mapping):
            _raise(error_factory, 'config must be a mapping object')
        payload.update({str(key): value for key, value in raw.items()})
    default_mode = getattr(defaults.mode, 'value', str(defaults.mode))
    mode_value = str(payload.get('mode', default_mode) or default_mode)
    try:
        payload['mode'] = IKSolverMode(mode_value)
    except ValueError as exc:
        _raise(error_factory, f'unsupported IK solver mode: {mode_value}')
    try:
        return IKConfig(**payload)
    except (TypeError, ValueError) as exc:
        _raise(error_factory, f'invalid IK config: {exc}')


def build_execution_graph_descriptor(spec, raw: object = None, *, error_factory: type[Exception] | ErrorFactory = ValueError) -> ExecutionGraphDescriptor:
    """Build the canonical execution-scope descriptor carried through runtime workflows.

    The descriptor is now resolved through :class:`ExecutionScopeService`, which keeps the
    active-path-over-tree runtime fail-closed. Callers may refine joint/link subsets, but they
    cannot silently opt into unsupported execution strategies such as closed-loop or full-tree
    execution.
    """
    if raw in (None, ''):
        payload: dict[str, object] = {}
    elif isinstance(raw, Mapping):
        payload = {str(key): value for key, value in raw.items()}
    else:
        _raise(error_factory, 'execution_graph must be a mapping object')
    try:
        return ExecutionScopeService().resolve_descriptor(spec, payload)
    except ValueError as exc:
        _raise(error_factory, str(exc))


def normalize_validation_layers(raw: object, *, error_factory: type[Exception] | ErrorFactory = ValueError) -> tuple[str, ...] | None:
    """Normalize optional validation-layer payloads into a stable tuple."""
    if raw in (None, ''):
        return None
    if not isinstance(raw, (list, tuple)):
        _raise(error_factory, 'validation_layers must be a list of strings')
    return tuple(str(item).strip() for item in raw if str(item).strip())


def build_ik_request(
    *,
    spec,
    q0,
    target: Pose,
    config: IKConfig,
    execution_graph: ExecutionGraphDescriptor | None = None,
) -> IKRequest:
    """Build a canonical IK request with normalized execution-graph metadata."""
    descriptor = execution_graph or default_execution_graph_descriptor(spec)
    metadata = {'execution_graph': descriptor.summary()}
    return IKRequest(spec=spec, target=target, q0=np.asarray(q0, dtype=float).copy(), config=config, execution_graph=descriptor, request_metadata=metadata)


def build_trajectory_request(
    *,
    q_start,
    q_goal,
    duration: float,
    dt: float,
    spec=None,
    mode: TrajectoryMode | str = TrajectoryMode.JOINT,
    target_pose: Pose | None = None,
    ik_config: IKConfig | None = None,
    planner_id: str | None = None,
    waypoint_graph=None,
    max_velocity: float | None = None,
    max_acceleration: float | None = None,
    planning_scene=None,
    validation_layers: tuple[str, ...] | None = None,
    pipeline_id: str | None = None,
    execution_graph: ExecutionGraphDescriptor | None = None,
) -> TrajectoryRequest:
    """Build a canonical trajectory request from normalized workflow inputs."""
    descriptor = execution_graph if execution_graph is not None or spec is None else default_execution_graph_descriptor(spec)
    return TrajectoryRequest(
        q_start=np.asarray(q_start, dtype=float).copy(),
        q_goal=None if q_goal is None else np.asarray(q_goal, dtype=float).copy(),
        duration=float(duration),
        dt=float(dt),
        spec=spec,
        mode=TrajectoryMode(str(getattr(mode, 'value', mode))),
        target_pose=target_pose,
        ik_config=ik_config,
        planner_id=None if planner_id in (None, '') else str(planner_id),
        waypoint_graph=waypoint_graph,
        max_velocity=max_velocity,
        max_acceleration=max_acceleration,
        planning_scene=planning_scene,
        validation_layers=validation_layers,
        pipeline_id=None if pipeline_id in (None, '') else str(pipeline_id),
        execution_graph=descriptor,
    )
