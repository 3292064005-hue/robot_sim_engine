from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from robot_sim.domain.enums import JointType
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec, RobotLinkSpec


@dataclass(frozen=True)
class CanonicalRobotModel:
    """Structured source robot model retained alongside the runtime execution adapter.

    The runtime no longer has to read ``RobotSpec.dh_rows`` directly. Instead it resolves a
    deterministic serial execution chain from this canonical model first and only falls back to
    the legacy spec-level rows when the canonical payload predates the execution-surface upgrade.

    Attributes:
        name: Stable robot identifier.
        joints: Full source joint graph retained from the importer or registry.
        links: Full source link table retained from the importer or registry.
        root_link: Declared root link for the structured source graph.
        source_format: Source model family such as ``yaml`` or ``urdf``.
        execution_adapter: Declared runtime execution adapter label.
        execution_rows: Runtime serial execution rows consumed by FK / IK / planning today.
        fidelity: Importer fidelity or registry synthesis fidelity.
        metadata: Structured extension metadata preserved across persistence.
    """

    name: str
    joints: tuple[RobotJointSpec, ...] = ()
    links: tuple[RobotLinkSpec, ...] = ()
    root_link: str = ''
    source_format: str = ''
    execution_adapter: str = 'canonical_dh_chain'
    execution_rows: tuple[DHRow, ...] = ()
    fidelity: str = ''
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'joints', tuple(self.joints))
        object.__setattr__(self, 'links', tuple(self.links))
        object.__setattr__(self, 'execution_rows', tuple(self.execution_rows))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        dynamic_joints = self.dynamic_joints
        if dynamic_joints and len(dynamic_joints) > len(self.joints):
            raise ValueError('canonical robot model dynamic joint count is invalid')
        if self.execution_rows and len(self.execution_rows) != len(dynamic_joints):
            raise ValueError(
                f'canonical execution row count mismatch: expected {len(dynamic_joints)}, got {len(self.execution_rows)}'
            )
        link_names = {link.name for link in self.links}
        for joint in self.joints:
            if link_names and joint.parent_link and joint.parent_link not in link_names:
                raise ValueError(f'canonical joint {joint.name!r} parent link {joint.parent_link!r} missing from links')
            if link_names and joint.child_link and joint.child_link not in link_names:
                raise ValueError(f'canonical joint {joint.name!r} child link {joint.child_link!r} missing from links')

    @property
    def dynamic_joints(self) -> tuple[RobotJointSpec, ...]:
        return tuple(joint for joint in self.joints if joint.joint_type in (JointType.REVOLUTE, JointType.PRISMATIC))

    @property
    def dof(self) -> int:
        return len(self.dynamic_joints)

    @property
    def joint_names(self) -> tuple[str, ...]:
        return tuple(joint.name for joint in self.dynamic_joints)

    @property
    def link_names(self) -> tuple[str, ...]:
        if self.links:
            return tuple(link.name for link in self.links)
        if not self.joints:
            return ()
        ordered: list[str] = []
        seen: set[str] = set()
        if self.root_link:
            ordered.append(self.root_link)
            seen.add(self.root_link)
        for joint in self.joints:
            for link_name in (joint.parent_link, joint.child_link):
                if link_name and link_name not in seen:
                    seen.add(link_name)
                    ordered.append(link_name)
        return tuple(ordered)

    @property
    def joint_limits(self) -> tuple[RobotJointLimit, ...]:
        limits: list[RobotJointLimit] = []
        for index, joint in enumerate(self.dynamic_joints):
            if joint.limit is not None:
                limits.append(joint.limit)
                continue
            if index < len(self.execution_rows):
                row = self.execution_rows[index]
                limits.append(RobotJointLimit(lower=float(row.q_min), upper=float(row.q_max)))
                continue
            limits.append(RobotJointLimit(lower=-float(np.pi), upper=float(np.pi)))
        return tuple(limits)

    @property
    def has_visual(self) -> bool:
        return any(link.has_visual for link in self.links)

    @property
    def has_collision(self) -> bool:
        return any(link.has_collision for link in self.links)

    def summary(self) -> dict[str, object]:
        return {
            'name': self.name,
            'root_link': self.root_link,
            'source_format': self.source_format,
            'execution_adapter': self.execution_adapter,
            'execution_surface': 'canonical_model',
            'execution_row_count': int(len(self.execution_rows)),
            'fidelity': self.fidelity,
            'joint_count': int(self.dof),
            'link_count': int(len(self.link_names)),
            'has_visual': bool(self.has_visual),
            'has_collision': bool(self.has_collision),
        }



def serialize_canonical_robot_model(model: CanonicalRobotModel | None) -> dict[str, object] | None:
    """Serialize a canonical robot model into a JSON/YAML-safe payload."""
    if model is None:
        return None
    return {
        'name': str(model.name),
        'root_link': str(model.root_link),
        'source_format': str(model.source_format),
        'execution_adapter': str(model.execution_adapter),
        'execution_rows': [
            {
                'a': float(row.a),
                'alpha': float(row.alpha),
                'd': float(row.d),
                'theta_offset': float(row.theta_offset),
                'joint_type': row.joint_type.value,
                'q_min': float(row.q_min),
                'q_max': float(row.q_max),
            }
            for row in model.execution_rows
        ],
        'fidelity': str(model.fidelity),
        'metadata': dict(model.metadata),
        'joints': [
            {
                'name': joint.name,
                'parent_link': joint.parent_link,
                'child_link': joint.child_link,
                'joint_type': joint.joint_type.value,
                'axis': np.asarray(joint.axis, dtype=float).tolist(),
                'limit': None if joint.limit is None else {
                    'lower': float(joint.limit.lower),
                    'upper': float(joint.limit.upper),
                    'velocity': None if joint.limit.velocity is None else float(joint.limit.velocity),
                    'effort': None if joint.limit.effort is None else float(joint.limit.effort),
                },
                'origin_translation': np.asarray(joint.origin_translation, dtype=float).tolist(),
                'origin_rpy': np.asarray(joint.origin_rpy, dtype=float).tolist(),
                'metadata': dict(joint.metadata),
            }
            for joint in model.joints
        ],
        'links': [
            {
                'name': link.name,
                'parent_joint': link.parent_joint,
                'inertial_mass': None if link.inertial_mass is None else float(link.inertial_mass),
                'inertial_origin': None if link.inertial_origin is None else np.asarray(link.inertial_origin, dtype=float).tolist(),
                'has_visual': bool(link.has_visual),
                'has_collision': bool(link.has_collision),
                'metadata': dict(link.metadata),
            }
            for link in model.links
        ],
    }



def deserialize_canonical_robot_model(payload: dict[str, object] | None) -> CanonicalRobotModel | None:
    """Deserialize a JSON/YAML-safe canonical robot model payload."""
    if not payload:
        return None
    joints = tuple(
        RobotJointSpec(
            name=str(item.get('name', 'joint')),
            parent_link=str(item.get('parent_link', '')),
            child_link=str(item.get('child_link', '')),
            joint_type=JointType(str(item.get('joint_type', JointType.REVOLUTE.value))),
            axis=np.asarray(item.get('axis', [0.0, 0.0, 1.0]), dtype=float),
            limit=None if item.get('limit') is None else RobotJointLimit(
                lower=float((item.get('limit') or {}).get('lower', -np.pi)),
                upper=float((item.get('limit') or {}).get('upper', np.pi)),
                velocity=float((item.get('limit') or {}).get('velocity')) if (item.get('limit') or {}).get('velocity') is not None else None,
                effort=float((item.get('limit') or {}).get('effort')) if (item.get('limit') or {}).get('effort') is not None else None,
            ),
            origin_translation=np.asarray(item.get('origin_translation', [0.0, 0.0, 0.0]), dtype=float),
            origin_rpy=np.asarray(item.get('origin_rpy', [0.0, 0.0, 0.0]), dtype=float),
            metadata=dict(item.get('metadata') or {}),
        )
        for item in payload.get('joints') or ()
    )
    links = tuple(
        RobotLinkSpec(
            name=str(item.get('name', 'link')),
            parent_joint=str(item.get('parent_joint')) if item.get('parent_joint') is not None else None,
            inertial_mass=float(item['inertial_mass']) if item.get('inertial_mass') is not None else None,
            inertial_origin=np.asarray(item.get('inertial_origin', [0.0, 0.0, 0.0]), dtype=float) if item.get('inertial_origin') is not None else None,
            has_visual=bool(item.get('has_visual', False)),
            has_collision=bool(item.get('has_collision', False)),
            metadata=dict(item.get('metadata') or {}),
        )
        for item in payload.get('links') or ()
    )
    execution_rows = tuple(
        DHRow(
            a=float(item.get('a', 0.0)),
            alpha=float(item.get('alpha', 0.0)),
            d=float(item.get('d', 0.0)),
            theta_offset=float(item.get('theta_offset', 0.0)),
            joint_type=JointType(str(item.get('joint_type', JointType.REVOLUTE.value))),
            q_min=float(item.get('q_min', -np.pi)),
            q_max=float(item.get('q_max', np.pi)),
        )
        for item in payload.get('execution_rows') or ()
    )
    return CanonicalRobotModel(
        name=str(payload.get('name', 'robot')),
        joints=joints,
        links=links,
        root_link=str(payload.get('root_link', '') or ''),
        source_format=str(payload.get('source_format', '') or ''),
        execution_adapter=str(payload.get('execution_adapter', 'canonical_dh_chain') or 'canonical_dh_chain'),
        execution_rows=execution_rows,
        fidelity=str(payload.get('fidelity', '') or ''),
        metadata=dict(payload.get('metadata') or {}),
    )
