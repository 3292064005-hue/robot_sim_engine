from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.domain.enums import JointType
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_links import RobotJointLimit

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.model.canonical_robot_model import CanonicalRobotModel


def _rpy_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = float(np.cos(roll)), float(np.sin(roll))
    cp, sp = float(np.cos(pitch)), float(np.sin(pitch))
    cy, sy = float(np.cos(yaw)), float(np.sin(yaw))
    return np.asarray([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ], dtype=float)



def _homogeneous(rotation: np.ndarray, translation: tuple[float, float, float] | np.ndarray) -> np.ndarray:
    T = np.eye(4, dtype=float)
    T[:3, :3] = np.asarray(rotation, dtype=float).reshape(3, 3)
    T[:3, 3] = np.asarray(translation, dtype=float).reshape(3)
    return T



def _axis_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = np.asarray(axis, dtype=float).reshape(3)
    norm = float(np.linalg.norm(axis))
    if norm <= 1.0e-12:
        return np.eye(3, dtype=float)
    axis = axis / norm
    x, y, z = axis
    c, s = float(np.cos(angle)), float(np.sin(angle))
    C = 1.0 - c
    return np.asarray([
        [x * x * C + c, x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, y * y * C + c, y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, z * z * C + c],
    ], dtype=float)



def _normalize_axis(axis: tuple[float, float, float] | np.ndarray) -> tuple[float, float, float]:
    arr = np.asarray(axis, dtype=float).reshape(3)
    norm = float(np.linalg.norm(arr))
    if norm <= 1.0e-12:
        arr = np.array([0.0, 0.0, 1.0], dtype=float)
    else:
        arr = arr / norm
    return tuple(float(v) for v in arr.tolist())



def _dh_row_from_joint_metadata(joint: 'ArticulatedJointModel') -> DHRow | None:
    payload = dict(joint.metadata.get('dh_row', {}) or {})
    if not payload:
        return None
    return DHRow(
        a=float(payload.get('a', 0.0)),
        alpha=float(payload.get('alpha', 0.0)),
        d=float(payload.get('d', 0.0)),
        theta_offset=float(payload.get('theta_offset', 0.0)),
        joint_type=JointType(str(payload.get('joint_type', joint.joint_type.value) or joint.joint_type.value)),
        q_min=float(payload.get('q_min', joint.limit.lower)),
        q_max=float(payload.get('q_max', joint.limit.upper)),
    )


def _joint_uses_dh_execution(joint: 'ArticulatedJointModel') -> bool:
    return str((joint.metadata or {}).get('execution_convention', '') or '') == 'dh_row'


@dataclass(frozen=True)
class ArticulatedJointModel:
    """Structured articulated joint description independent from legacy DH rows.

    Attributes:
        name: Stable joint identifier.
        parent_link: Parent link name.
        child_link: Child link name.
        joint_type: Runtime joint type.
        axis: Joint axis expressed in the joint frame after ``origin_transform``.
        origin_translation: Parent-to-joint origin translation.
        origin_rpy: Parent-to-joint origin Euler rotation.
        limit: Runtime joint limits.
        parent_index: Optional parent joint index for tree traversal. ``None`` for a root joint.
    """

    name: str
    parent_link: str
    child_link: str
    joint_type: JointType
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    origin_translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    origin_rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)
    limit: RobotJointLimit = field(default_factory=lambda: RobotJointLimit(lower=-float(np.pi), upper=float(np.pi)))
    parent_index: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'name', str(self.name or ''))
        object.__setattr__(self, 'parent_link', str(self.parent_link or ''))
        object.__setattr__(self, 'child_link', str(self.child_link or ''))
        object.__setattr__(self, 'axis', _normalize_axis(self.axis))
        object.__setattr__(self, 'origin_translation', tuple(float(v) for v in np.asarray(self.origin_translation, dtype=float).reshape(3).tolist()))
        object.__setattr__(self, 'origin_rpy', tuple(float(v) for v in np.asarray(self.origin_rpy, dtype=float).reshape(3).tolist()))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        if self.parent_index is not None and int(self.parent_index) < 0:
            raise ValueError('articulated joint parent_index must be >= 0 or None')

    def to_dict(self) -> dict[str, object]:
        return self.summary()

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> 'ArticulatedJointModel | None':
        if not isinstance(payload, dict) or not payload:
            return None
        limit_payload = dict(payload.get('limit', {}) or {})
        return cls(
            name=str(payload.get('name', '') or ''),
            parent_link=str(payload.get('parent_link', '') or ''),
            child_link=str(payload.get('child_link', '') or ''),
            joint_type=JointType(str(payload.get('joint_type', JointType.REVOLUTE.value) or JointType.REVOLUTE.value)),
            axis=tuple(float(v) for v in payload.get('axis', (0.0, 0.0, 1.0)) or (0.0, 0.0, 1.0)),
            origin_translation=tuple(float(v) for v in payload.get('origin_translation', (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
            origin_rpy=tuple(float(v) for v in payload.get('origin_rpy', (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
            limit=RobotJointLimit(
                lower=float(limit_payload.get('lower', -np.pi)),
                upper=float(limit_payload.get('upper', np.pi)),
                velocity=None if limit_payload.get('velocity') is None else float(limit_payload.get('velocity')),
                effort=None if limit_payload.get('effort') is None else float(limit_payload.get('effort')),
            ),
            parent_index=None if payload.get('parent_index') is None else int(payload.get('parent_index')),
            metadata=dict(payload.get('metadata', {}) or {}),
        )

    def summary(self) -> dict[str, object]:
        return {
            'name': str(self.name),
            'parent_link': str(self.parent_link),
            'child_link': str(self.child_link),
            'joint_type': self.joint_type.value,
            'axis': [float(v) for v in self.axis],
            'origin_translation': [float(v) for v in self.origin_translation],
            'origin_rpy': [float(v) for v in self.origin_rpy],
            'limit': {
                'lower': float(self.limit.lower),
                'upper': float(self.limit.upper),
                'velocity': None if self.limit.velocity is None else float(self.limit.velocity),
                'effort': None if self.limit.effort is None else float(self.limit.effort),
            },
            'parent_index': None if self.parent_index is None else int(self.parent_index),
            'metadata': dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class ArticulatedRobotModel:
    """Structured articulated robot model.

    Unlike the legacy DH adapter payload, this model is now a real execution surface for serial
    articulated robots: FK, Jacobian, and numeric IK read transforms, axes, and joint origins from
    ``origin_transform`` + ``motion_transform`` instead of silently re-projecting back to DH.
    """

    name: str
    root_link: str
    joint_models: tuple[ArticulatedJointModel, ...]
    link_names: tuple[str, ...]
    base_T: np.ndarray
    tool_T: np.ndarray
    home_q: np.ndarray
    semantic_family: str = 'articulated_serial_tree'
    source_surface: str = 'canonical_model'
    source_format: str = ''
    fidelity: str = ''
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'name', str(self.name or ''))
        object.__setattr__(self, 'root_link', str(self.root_link or 'world'))
        object.__setattr__(self, 'joint_models', tuple(self.joint_models))
        object.__setattr__(self, 'link_names', tuple(str(item) for item in self.link_names))
        object.__setattr__(self, 'base_T', np.asarray(self.base_T, dtype=float).reshape(4, 4).copy())
        object.__setattr__(self, 'tool_T', np.asarray(self.tool_T, dtype=float).reshape(4, 4).copy())
        object.__setattr__(self, 'home_q', np.asarray(self.home_q, dtype=float).reshape(-1).copy())
        object.__setattr__(self, 'semantic_family', str(self.semantic_family or 'articulated_serial_tree'))
        object.__setattr__(self, 'source_surface', str(self.source_surface or 'canonical_model'))
        object.__setattr__(self, 'source_format', str(self.source_format or ''))
        object.__setattr__(self, 'fidelity', str(self.fidelity or ''))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        if self.home_q.shape != (len(self.joint_models),):
            raise ValueError(f'articulated home_q mismatch: expected {(len(self.joint_models),)}, got {self.home_q.shape}')
        if not np.isfinite(self.base_T).all() or not np.isfinite(self.tool_T).all() or not np.isfinite(self.home_q).all():
            raise ValueError('articulated robot model contains non-finite base/tool/home values')
        for index, joint in enumerate(self.joint_models):
            if joint.parent_index is not None and int(joint.parent_index) >= index:
                raise ValueError(
                    'articulated joint parent_index must reference an earlier joint to preserve '
                    f'topological execution order: joint={joint.name!r}, parent_index={joint.parent_index!r}, index={index}'
                )

    @property
    def dof(self) -> int:
        return len(self.joint_models)

    @property
    def joint_names(self) -> tuple[str, ...]:
        return tuple(joint.name for joint in self.joint_models)

    @property
    def capability_badges(self) -> tuple[str, ...]:
        return (
            f'semantic_family:{self.semantic_family}',
            f'source_surface:{self.source_surface}',
            f'source_format:{self.source_format or "unknown"}',
            f'fidelity:{self.fidelity or "unknown"}',
            f'dof:{self.dof}',
        )

    @cached_property
    def _serial_child_counts(self) -> tuple[int, ...]:
        counts = [0] * self.dof
        for joint in self.joint_models:
            if joint.parent_index is not None:
                counts[int(joint.parent_index)] += 1
        return tuple(counts)

    @cached_property
    def _serial_leaf_joint_index(self) -> int:
        leaf_indices = [index for index, child_count in enumerate(self._serial_child_counts) if child_count == 0]
        if len(leaf_indices) != 1:
            raise ValueError(
                'articulated serial-tree execution requires exactly one terminal dynamic joint; '
                f'got leaves={leaf_indices!r}'
            )
        return int(leaf_indices[0])

    def require_serial_tree_execution(self) -> None:
        if self.semantic_family != 'articulated_serial_tree':
            raise ValueError(f'articulated robot model does not satisfy serial-tree execution semantics: {self.semantic_family!r}')
        root_count = sum(1 for joint in self.joint_models if joint.parent_index is None)
        if root_count != 1:
            raise ValueError(
                'articulated serial-tree execution requires exactly one root joint; '
                f'got root_count={root_count}'
            )
        _ = self._serial_leaf_joint_index

    @cached_property
    def serial_projection_rows(self) -> tuple[DHRow, ...]:
        """Compatibility DH rows used only by legacy analytic adapters.

        Boundary behavior:
            This projection is intentionally lossy. Runtime FK/Jacobian/IK must use the articulated
            transforms directly rather than assuming these rows are geometrically equivalent.
        """
        rows: list[DHRow] = []
        for joint in self.joint_models:
            lower = float(joint.limit.lower)
            upper = float(joint.limit.upper)
            origin_translation = tuple(float(v) for v in joint.origin_translation)
            origin_rpy = tuple(float(v) for v in joint.origin_rpy)
            rows.append(
                DHRow(
                    a=float(origin_translation[0]),
                    alpha=float(origin_rpy[0]),
                    d=float(origin_translation[2]),
                    theta_offset=float(origin_rpy[2]),
                    joint_type=joint.joint_type,
                    q_min=lower,
                    q_max=upper,
                )
            )
        return tuple(rows)

    @cached_property
    def joint_minima(self) -> np.ndarray:
        return np.asarray([float(joint.limit.lower) for joint in self.joint_models], dtype=float)

    @cached_property
    def joint_maxima(self) -> np.ndarray:
        return np.asarray([float(joint.limit.upper) for joint in self.joint_models], dtype=float)

    def origin_transform(self, index: int) -> np.ndarray:
        """Return the fixed parent-to-joint transform for one joint."""
        joint = self.joint_models[index]
        rotation = _rpy_matrix(*joint.origin_rpy)
        return _homogeneous(rotation, joint.origin_translation)

    def motion_transform(self, index: int, q_value: float) -> np.ndarray:
        """Return the joint motion transform for one configuration value.

        Revolute joints rotate about ``joint.axis`` in the joint frame after
        :meth:`origin_transform`. Prismatic joints translate along the same axis.
        """
        joint = self.joint_models[index]
        axis = np.asarray(joint.axis, dtype=float)
        if joint.joint_type is JointType.REVOLUTE:
            return _homogeneous(_axis_rotation(axis, float(q_value)), (0.0, 0.0, 0.0))
        if joint.joint_type is JointType.PRISMATIC:
            return _homogeneous(np.eye(3, dtype=float), axis * float(q_value))
        return np.eye(4, dtype=float)

    def _validated_q(self, q: np.ndarray) -> np.ndarray:
        q_arr = np.asarray(q, dtype=float).reshape(-1)
        if q_arr.shape != (self.dof,):
            raise ValueError(f'articulated joint vector mismatch: expected {(self.dof,)}, got {q_arr.shape}')
        if not np.isfinite(q_arr).all():
            raise ValueError('articulated joint vector contains non-finite values')
        return q_arr

    def _parent_child_link_frames(self, q: np.ndarray) -> tuple[tuple[np.ndarray, ...], tuple[np.ndarray, ...]]:
        self.require_serial_tree_execution()
        q_arr = self._validated_q(q)
        child_frames: list[np.ndarray] = []
        joint_origin_frames: list[np.ndarray] = []
        for index, (joint, value) in enumerate(zip(self.joint_models, q_arr)):
            parent_frame = np.asarray(self.base_T, dtype=float) if joint.parent_index is None else child_frames[int(joint.parent_index)]
            if _joint_uses_dh_execution(joint):
                from robot_sim.core.kinematics.dh import dh_transform

                joint_origin = np.asarray(parent_frame, dtype=float).copy()
                row = _dh_row_from_joint_metadata(joint)
                if row is None:
                    raise ValueError(f'articulated joint {joint.name!r} declared dh_row execution without dh_row metadata')
                child_frame = parent_frame @ dh_transform(row, float(value))
            else:
                joint_origin = parent_frame @ self.origin_transform(index)
                child_frame = joint_origin @ self.motion_transform(index, float(value))
            joint_origin_frames.append(np.asarray(joint_origin, dtype=float).copy())
            child_frames.append(np.asarray(child_frame, dtype=float).copy())
        return tuple(joint_origin_frames), tuple(child_frames)

    def forward_transforms(self, q: np.ndarray) -> tuple[np.ndarray, ...]:
        """Return world transforms for the root link and each articulated child link.

        Returns:
            tuple[np.ndarray, ...]: ``(root_link_T, child_link_0_T, ..., tool_T_world)`` where the
            last frame includes the tool transform applied on the terminal articulated link.

        Raises:
            ValueError: If ``q`` shape is invalid, contains non-finite values, or the articulated
                hierarchy is not topologically ordered.
        """
        _joint_origins, child_frames = self._parent_child_link_frames(q)
        frames = [np.asarray(self.base_T, dtype=float).copy()]
        frames.extend(np.asarray(frame, dtype=float).copy() for frame in child_frames)
        if frames:
            terminal_index = self._serial_leaf_joint_index + 1
            frames[terminal_index] = frames[terminal_index] @ np.asarray(self.tool_T, dtype=float)
        return tuple(frames)

    def world_joint_axes_origins(self, q: np.ndarray) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
        """Return each joint axis and origin in world coordinates.

        Returns:
            tuple[tuple[np.ndarray, np.ndarray], ...]: One ``(axis_world, origin_world)`` tuple per
            joint, with the axis resolved after the joint origin transform and before the joint
            motion transform.
        """
        joint_origin_frames, _child_frames = self._parent_child_link_frames(q)
        pairs: list[tuple[np.ndarray, np.ndarray]] = []
        for joint, joint_origin in zip(self.joint_models, joint_origin_frames):
            if _joint_uses_dh_execution(joint):
                axis_world = joint_origin[:3, 2].copy()
            else:
                axis_world = joint_origin[:3, :3] @ np.asarray(joint.axis, dtype=float)
                axis_norm = float(np.linalg.norm(axis_world))
                if axis_norm > 1.0e-12:
                    axis_world = axis_world / axis_norm
            origin_world = joint_origin[:3, 3].copy()
            pairs.append((np.asarray(axis_world, dtype=float).copy(), np.asarray(origin_world, dtype=float).copy()))
        return tuple(pairs)

    def rough_reach_radius(self) -> float:
        radius = 0.0
        for joint in self.joint_models:
            radius += float(np.linalg.norm(np.asarray(joint.origin_translation, dtype=float)))
        radius += float(np.linalg.norm(np.asarray(self.tool_T[:3, 3], dtype=float)))
        return radius if radius > 0.0 else 1.0

    def to_dict(self) -> dict[str, object]:
        return self.summary()

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> 'ArticulatedRobotModel | None':
        if not isinstance(payload, dict) or not payload:
            return None
        joints = [joint for item in payload.get('joints', ()) or () if (joint := ArticulatedJointModel.from_dict(item)) is not None]
        return cls(
            name=str(payload.get('name', '') or ''),
            root_link=str(payload.get('root_link', 'world') or 'world'),
            joint_models=tuple(joints),
            link_names=tuple(str(v) for v in payload.get('link_names', ()) or ()),
            base_T=np.asarray(payload.get('base_T', np.eye(4).tolist()), dtype=float),
            tool_T=np.asarray(payload.get('tool_T', np.eye(4).tolist()), dtype=float),
            home_q=np.asarray(payload.get('home_q', [0.0] * len(joints)), dtype=float),
            semantic_family=str(payload.get('semantic_family', 'articulated_serial_tree') or 'articulated_serial_tree'),
            source_surface=str(payload.get('source_surface', '') or ''),
            source_format=str(payload.get('source_format', '') or ''),
            fidelity=str(payload.get('fidelity', '') or ''),
            metadata=dict(payload.get('metadata', {}) or {}),
        )

    def summary(self) -> dict[str, object]:
        return {
            'name': self.name,
            'root_link': self.root_link,
            'dof': int(self.dof),
            'joint_names': list(self.joint_names),
            'link_names': list(self.link_names),
            'semantic_family': self.semantic_family,
            'source_surface': self.source_surface,
            'source_format': self.source_format,
            'fidelity': self.fidelity,
            'capability_badges': list(self.capability_badges),
            'base_T': np.asarray(self.base_T, dtype=float).tolist(),
            'tool_T': np.asarray(self.tool_T, dtype=float).tolist(),
            'home_q': np.asarray(self.home_q, dtype=float).tolist(),
            'joints': [joint.summary() for joint in self.joint_models],
            'metadata': dict(self.metadata or {}),
        }



def build_articulated_robot_model_from_canonical(
    canonical_model: 'CanonicalRobotModel',
    *,
    base_T: np.ndarray,
    tool_T: np.ndarray,
    home_q: np.ndarray,
    source_surface: str = 'canonical_model',
    fidelity: str = '',
    metadata: dict[str, object] | None = None,
) -> ArticulatedRobotModel:
    """Project a canonical source model into a true articulated execution model.

    Args:
        canonical_model: Canonical source robot model.
        base_T: Base transform for the runtime robot.
        tool_T: Tool transform for the runtime robot.
        home_q: Home joint vector aligned to the dynamic joints.
        source_surface: Source surface label propagated into the articulated model summary.
        fidelity: Optional fidelity override.
        metadata: Optional metadata merged into the articulated model.

    Returns:
        ArticulatedRobotModel: Structured articulated model preserving source joint axes and
            origin transforms.

    Raises:
        ValueError: If the canonical model is inconsistent with the supplied runtime transforms.
    """
    dynamic_joints = tuple(canonical_model.dynamic_joints)
    child_link_to_joint_index: dict[str, int] = {}
    joint_models: list[ArticulatedJointModel] = []
    for index, joint in enumerate(dynamic_joints):
        limit = joint.limit if joint.limit is not None else RobotJointLimit(lower=-float(np.pi), upper=float(np.pi))
        parent_index = child_link_to_joint_index.get(joint.parent_link)
        if parent_index is None and index > 0 and str(joint.parent_link) != str(canonical_model.root_link or ''):
            raise ValueError(
                'canonical articulated projection requires an explicit serial parent chain; '
                f'could not resolve parent link {joint.parent_link!r} for joint {joint.name!r}'
            )
        joint_models.append(
            ArticulatedJointModel(
                name=str(joint.name),
                parent_link=str(joint.parent_link),
                child_link=str(joint.child_link),
                joint_type=joint.joint_type,
                axis=tuple(float(v) for v in np.asarray(joint.axis, dtype=float).reshape(3).tolist()),
                origin_translation=tuple(float(v) for v in np.asarray(joint.origin_translation, dtype=float).reshape(3).tolist()),
                origin_rpy=tuple(float(v) for v in np.asarray(joint.origin_rpy, dtype=float).reshape(3).tolist()),
                limit=limit,
                parent_index=parent_index,
                metadata={
                    'source_joint_metadata': dict(joint.metadata or {}),
                    'execution_adapter': str(canonical_model.execution_adapter or ''),
                    **(
                        {
                            'execution_convention': 'dh_row',
                            'dh_row': {
                                'a': float(canonical_model.execution_rows[index].a),
                                'alpha': float(canonical_model.execution_rows[index].alpha),
                                'd': float(canonical_model.execution_rows[index].d),
                                'theta_offset': float(canonical_model.execution_rows[index].theta_offset),
                                'joint_type': canonical_model.execution_rows[index].joint_type.value,
                                'q_min': float(canonical_model.execution_rows[index].q_min),
                                'q_max': float(canonical_model.execution_rows[index].q_max),
                            },
                        }
                        if str((joint.metadata or {}).get('source_projection', '') or '') == 'dh_rows' and index < len(canonical_model.execution_rows)
                        else {}
                    ),
                },
            )
        )
        child_link_to_joint_index[str(joint.child_link)] = index
    link_names = tuple(canonical_model.link_names) or tuple(
        [str(canonical_model.root_link or 'world'), *[str(joint.child_link) for joint in dynamic_joints]]
    )
    return ArticulatedRobotModel(
        name=str(canonical_model.name),
        root_link=str(canonical_model.root_link or (link_names[0] if link_names else 'world')),
        joint_models=tuple(joint_models),
        link_names=link_names,
        base_T=np.asarray(base_T, dtype=float),
        tool_T=np.asarray(tool_T, dtype=float),
        home_q=np.asarray(home_q, dtype=float),
        semantic_family='articulated_serial_tree',
        source_surface=str(source_surface or 'canonical_model'),
        source_format=str(canonical_model.source_format or ''),
        fidelity=str(fidelity or canonical_model.fidelity or ''),
        metadata={
            'derived_from_canonical_model': True,
            'execution_adapter': str(canonical_model.execution_adapter or ''),
            **dict(canonical_model.metadata or {}),
            **dict(metadata or {}),
        },
    )
