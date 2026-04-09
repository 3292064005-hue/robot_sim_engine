from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.domain.enums import JointType
from robot_sim.model.dh_row import DHRow
from robot_sim.model.articulated_robot_model import (
    ArticulatedJointModel,
    ArticulatedRobotModel,
    build_articulated_robot_model_from_canonical,
)
from robot_sim.model.robot_links import RobotJointLimit

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.model.robot_spec import RobotSpec


@dataclass(frozen=True)
class RuntimeRobotModel:
    """Structured runtime robot semantics consumed across execution, validation, and export.

    This model separates the runtime execution surface from the persisted/source robot payload so
    importer fidelity, diagnostics, and planning-scene generation all project from one explicit
    runtime semantic contract rather than reaching into legacy ``RobotSpec`` fields ad hoc.
    """

    name: str
    execution_rows: tuple[DHRow, ...]
    joint_names: tuple[str, ...]
    link_names: tuple[str, ...]
    joint_limits: tuple[RobotJointLimit, ...]
    base_T: np.ndarray
    tool_T: np.ndarray
    home_q: np.ndarray
    execution_adapter: str = 'robot_spec_execution_rows'
    source_surface: str = 'robot_spec'
    source_format: str = ''
    fidelity: str = ''
    semantic_family: str = 'serial_chain_execution'
    metadata: dict[str, object] = field(default_factory=dict)
    _joint_minima: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=float), init=False, repr=False, compare=False)
    _joint_maxima: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=float), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'name', str(self.name or ''))
        object.__setattr__(self, 'execution_rows', tuple(self.execution_rows))
        object.__setattr__(self, 'joint_names', tuple(str(name) for name in self.joint_names))
        object.__setattr__(self, 'link_names', tuple(str(name) for name in self.link_names))
        object.__setattr__(self, 'joint_limits', tuple(self.joint_limits))
        object.__setattr__(self, 'base_T', np.asarray(self.base_T, dtype=float).reshape(4, 4).copy())
        object.__setattr__(self, 'tool_T', np.asarray(self.tool_T, dtype=float).reshape(4, 4).copy())
        object.__setattr__(self, 'home_q', np.asarray(self.home_q, dtype=float).reshape(-1).copy())
        object.__setattr__(self, 'execution_adapter', str(self.execution_adapter or 'robot_spec_execution_rows'))
        object.__setattr__(self, 'source_surface', str(self.source_surface or 'robot_spec'))
        object.__setattr__(self, 'source_format', str(self.source_format or ''))
        object.__setattr__(self, 'fidelity', str(self.fidelity or ''))
        object.__setattr__(self, 'semantic_family', str(self.semantic_family or 'serial_chain_execution'))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        dof = len(self.execution_rows)
        if self.joint_names and len(self.joint_names) != dof:
            raise ValueError(f'runtime robot model joint_names mismatch: expected {dof}, got {len(self.joint_names)}')
        if self.joint_limits and len(self.joint_limits) != dof:
            raise ValueError(f'runtime robot model joint_limits mismatch: expected {dof}, got {len(self.joint_limits)}')
        if self.link_names and len(self.link_names) < dof:
            raise ValueError('runtime robot model link_names must contain at least one link per DOF chain')
        if self.home_q.shape != (dof,):
            raise ValueError(f'runtime robot model home_q mismatch: expected {(dof,)}, got {self.home_q.shape}')
        if not np.isfinite(self.base_T).all() or not np.isfinite(self.tool_T).all() or not np.isfinite(self.home_q).all():
            raise ValueError('runtime robot model contains non-finite base/tool/home values')
        object.__setattr__(self, '_joint_minima', np.asarray([limit.lower for limit in self.joint_limits], dtype=float))
        object.__setattr__(self, '_joint_maxima', np.asarray([limit.upper for limit in self.joint_limits], dtype=float))

    @property
    def dof(self) -> int:
        return len(self.execution_rows)

    @property
    def joint_minima(self) -> np.ndarray:
        return self._joint_minima

    @property
    def joint_maxima(self) -> np.ndarray:
        return self._joint_maxima

    @property
    def capability_badges(self) -> tuple[str, ...]:
        return (
            f'execution_adapter:{self.execution_adapter}',
            f'source_surface:{self.source_surface}',
            f'fidelity:{self.fidelity or "unknown"}',
            f'semantic_family:{self.semantic_family}',
        )

    def has_capability_badge(self, badge: str) -> bool:
        return str(badge or '') in set(self.capability_badges)

    def require_serial_chain_execution(self) -> None:
        expected = 'semantic_family:serial_chain_execution'
        if not self.has_capability_badge(expected):
            raise ValueError(
                'runtime robot model does not satisfy serial-chain execution semantics: '
                f'{self.semantic_family!r}'
            )

    @cached_property
    def articulated_model(self) -> ArticulatedRobotModel:
        payload = self.metadata.get('articulated_model_payload')
        if isinstance(payload, dict):
            articulated_model = ArticulatedRobotModel.from_dict(payload)
            if articulated_model is not None:
                return articulated_model
        return build_articulated_robot_model_from_runtime(self)

    def summary(self) -> dict[str, object]:
        capability_badges = list(self.capability_badges)
        articulated_model = self.articulated_model
        return {
            'name': self.name,
            'dof': int(self.dof),
            'joint_names': list(self.joint_names),
            'link_names': list(self.link_names),
            'execution_adapter': self.execution_adapter,
            'source_surface': self.source_surface,
            'source_format': self.source_format,
            'fidelity': self.fidelity,
            'semantic_family': self.semantic_family,
            'execution_row_count': int(len(self.execution_rows)),
            'joint_limit_count': int(len(self.joint_limits)),
            'execution_rows': [
                {
                    'a': float(row.a),
                    'alpha': float(row.alpha),
                    'd': float(row.d),
                    'theta_offset': float(row.theta_offset),
                    'joint_type': row.joint_type.value if hasattr(row.joint_type, 'value') else str(row.joint_type),
                    'q_min': float(row.q_min),
                    'q_max': float(row.q_max),
                }
                for row in self.execution_rows
            ],
            'joint_limits': [
                {
                    'lower': float(limit.lower),
                    'upper': float(limit.upper),
                    'velocity': None if limit.velocity is None else float(limit.velocity),
                    'effort': None if limit.effort is None else float(limit.effort),
                }
                for limit in self.joint_limits
            ],
            'has_base_transform': True,
            'has_tool_transform': True,
            'home_q_norm': float(np.linalg.norm(self.home_q)),
            'base_T': np.asarray(self.base_T, dtype=float).tolist(),
            'tool_T': np.asarray(self.tool_T, dtype=float).tolist(),
            'home_q': np.asarray(self.home_q, dtype=float).tolist(),
            'capability_badges': capability_badges,
            'provenance': dict(self.metadata),
            'articulated_model_summary': articulated_model.summary(),
        }


def build_articulated_robot_model_from_runtime(runtime_model: RuntimeRobotModel) -> ArticulatedRobotModel:
    """Project a runtime execution surface into an articulated robot model.

    Args:
        runtime_model: Structured runtime execution model.

    Returns:
        ArticulatedRobotModel: Articulated representation aligned to the current runtime surface.

    Raises:
        ValueError: If the runtime surface contains inconsistent joint/link data.
    """
    link_names = tuple(runtime_model.link_names) or tuple(f'link_{index}' for index in range(runtime_model.dof + 1))
    joint_models: list[ArticulatedJointModel] = []
    for index, row in enumerate(runtime_model.execution_rows):
        parent_link = link_names[index] if index < len(link_names) else f'link_{index}'
        child_link = link_names[index + 1] if index + 1 < len(link_names) else f'link_{index + 1}'
        limit = runtime_model.joint_limits[index]
        joint_models.append(
            ArticulatedJointModel(
                name=runtime_model.joint_names[index] if index < len(runtime_model.joint_names) else f'joint_{index}',
                parent_link=parent_link,
                child_link=child_link,
                joint_type=row.joint_type,
                axis=(0.0, 0.0, 1.0),
                origin_translation=(float(row.a), 0.0, float(row.d)),
                origin_rpy=(float(row.alpha), 0.0, float(row.theta_offset)),
                limit=limit,
                parent_index=None if index == 0 else index - 1,
                metadata={
                    'execution_adapter': runtime_model.execution_adapter,
                    'execution_convention': 'dh_row',
                    'dh_row': {
                        'a': float(row.a),
                        'alpha': float(row.alpha),
                        'd': float(row.d),
                        'theta_offset': float(row.theta_offset),
                        'joint_type': row.joint_type.value,
                        'q_min': float(row.q_min),
                        'q_max': float(row.q_max),
                    },
                },
            )
        )
    return ArticulatedRobotModel(
        name=runtime_model.name,
        root_link=link_names[0] if link_names else 'world',
        joint_models=tuple(joint_models),
        link_names=link_names,
        base_T=runtime_model.base_T,
        tool_T=runtime_model.tool_T,
        home_q=runtime_model.home_q,
        semantic_family='articulated_serial_tree',
        source_surface=runtime_model.source_surface,
        source_format=runtime_model.source_format,
        fidelity=runtime_model.fidelity,
        metadata={'derived_from_runtime_model': True, **dict(runtime_model.metadata or {})},
    )


def build_runtime_robot_model(spec: 'RobotSpec') -> RuntimeRobotModel:
    """Project a :class:`RobotSpec` into the stable runtime semantic contract."""
    metadata = dict(spec.metadata or {})
    canonical = spec.canonical_model
    if canonical is not None:
        execution_rows = tuple(canonical.execution_rows or spec.dh_rows)
        joint_names = tuple(canonical.joint_names or tuple(spec.joint_names) or tuple(f'joint_{index}' for index in range(len(execution_rows))))
        link_names = tuple(canonical.link_names or tuple(spec.link_names) or tuple(f'link_{index}' for index in range(len(execution_rows) + 1)))
        joint_limits = tuple(canonical.joint_limits or tuple(spec.joint_limits) or tuple(RobotJointLimit(lower=float(row.q_min), upper=float(row.q_max)) for row in execution_rows))
        execution_adapter = str(canonical.execution_adapter or metadata.get('execution_adapter', 'canonical_dh_chain'))
        source_surface = 'canonical_model'
        source_format = str(canonical.source_format or spec.model_source or spec.kinematic_source or '')
        fidelity = str(canonical.fidelity or metadata.get('import_fidelity', source_format or 'generated_proxy') or 'generated_proxy')
    else:
        execution_rows = tuple(spec.dh_rows)
        joint_names = tuple(spec.joint_names) or tuple(f'joint_{index}' for index in range(len(execution_rows)))
        link_names = tuple(spec.link_names) or tuple(f'link_{index}' for index in range(len(execution_rows) + 1))
        joint_limits = tuple(spec.joint_limits) or tuple(RobotJointLimit(lower=float(row.q_min), upper=float(row.q_max)) for row in execution_rows)
        execution_adapter = str(metadata.get('execution_adapter', 'robot_spec_execution_rows') or 'robot_spec_execution_rows')
        source_surface = str(metadata.get('execution_surface', 'robot_spec') or 'robot_spec')
        source_format = str(spec.model_source or spec.kinematic_source or 'dh_config')
        fidelity = str(metadata.get('import_fidelity', source_format or 'generated_proxy') or 'generated_proxy')
    semantic_family = str(metadata.get('runtime_semantic_family', 'serial_chain_execution') or 'serial_chain_execution')
    runtime_metadata = {
        'model_source': spec.model_source,
        'kinematic_source': spec.kinematic_source,
        'geometry_bundle_ref': spec.geometry_bundle_ref,
        'collision_bundle_ref': spec.collision_bundle_ref,
        'has_structured_model': bool(spec.has_structured_model),
        'has_canonical_model': bool(spec.has_canonical_model),
        'geometry_available': bool(spec.geometry_available),
        'collision_model': spec.collision_model,
    }
    if canonical is not None:
        articulated_model = build_articulated_robot_model_from_canonical(
            canonical,
            base_T=spec.base_T,
            tool_T=spec.tool_T,
            home_q=spec.home_q,
            source_surface=source_surface,
            fidelity=fidelity,
            metadata={'runtime_projection': True},
        )
        runtime_metadata['articulated_model_payload'] = articulated_model.to_dict()
    return RuntimeRobotModel(
        name=spec.name,
        execution_rows=execution_rows,
        joint_names=joint_names,
        link_names=link_names,
        joint_limits=joint_limits,
        base_T=spec.base_T,
        tool_T=spec.tool_T,
        home_q=spec.home_q,
        execution_adapter=execution_adapter,
        source_surface=source_surface,
        source_format=source_format,
        fidelity=fidelity,
        semantic_family=semantic_family,
        metadata=runtime_metadata,
    )


def deserialize_runtime_robot_model(payload: dict[str, object] | None) -> RuntimeRobotModel:
    if not isinstance(payload, dict) or not payload:
        raise ValueError('runtime robot model payload is required')
    rows_payload = payload.get('execution_rows') or payload.get('rows') or ()
    rows = []
    for item in rows_payload:
        rows.append(
            DHRow(
                a=float(item.get('a', 0.0)),
                alpha=float(item.get('alpha', 0.0)),
                d=float(item.get('d', 0.0)),
                theta_offset=float(item.get('theta_offset', 0.0)),
                joint_type=JointType(str(item.get('joint_type', 'revolute') or 'revolute')),
                q_min=float(item.get('q_min', -np.pi)),
                q_max=float(item.get('q_max', np.pi)),
            )
        )
    joint_limits = []
    for item in payload.get('joint_limits', ()) or ():
        joint_limits.append(
            RobotJointLimit(
                lower=float(item.get('lower', -np.pi)),
                upper=float(item.get('upper', np.pi)),
                velocity=None if item.get('velocity') is None else float(item.get('velocity')),
                effort=None if item.get('effort') is None else float(item.get('effort')),
            )
        )
    if not joint_limits:
        joint_limits = [RobotJointLimit(float(row.q_min), float(row.q_max)) for row in rows]
    return RuntimeRobotModel(
        name=str(payload.get('name', '') or ''),
        execution_rows=tuple(rows),
        joint_names=tuple(str(v) for v in payload.get('joint_names', ()) or ()),
        link_names=tuple(str(v) for v in payload.get('link_names', ()) or ()),
        joint_limits=tuple(joint_limits),
        base_T=np.asarray(payload.get('base_T', np.eye(4).tolist()), dtype=float),
        tool_T=np.asarray(payload.get('tool_T', np.eye(4).tolist()), dtype=float),
        home_q=np.asarray(payload.get('home_q', [0.0] * len(rows)), dtype=float),
        execution_adapter=str(payload.get('execution_adapter', 'robot_spec_execution_rows') or 'robot_spec_execution_rows'),
        source_surface=str(payload.get('source_surface', 'robot_spec') or 'robot_spec'),
        source_format=str(payload.get('source_format', '') or ''),
        fidelity=str(payload.get('fidelity', '') or ''),
        semantic_family=str(payload.get('semantic_family', 'serial_chain_execution') or 'serial_chain_execution'),
        metadata=dict(payload.get('provenance', payload.get('metadata', {})) or {}),
    )
