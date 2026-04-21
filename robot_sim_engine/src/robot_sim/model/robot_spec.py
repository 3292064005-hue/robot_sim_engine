from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.domain.enums import JointType, KinematicConvention
from robot_sim.domain.types import FloatArray
from robot_sim.model.canonical_robot_model import CanonicalRobotModel
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec, RobotLinkSpec

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.model.articulated_robot_model import ArticulatedRobotModel
    from robot_sim.model.imported_robot_package import ImportedRobotPackage
    from robot_sim.model.runtime_robot_model import RuntimeRobotModel


@dataclass(frozen=True)
class RobotSpec:
    """Canonical robot specification used by the runtime.

    ``dh_rows`` remains the persisted serial-projection payload, but runtime execution now resolves
    through an explicit runtime model projection first when a canonical model is present. This keeps
    importers, persistence, diagnostics, and planning-scene generation anchored to one structured
    source of truth while the current solver surface still consumes a serial DH-like adapter chain.
    """

    name: str
    dh_rows: tuple[DHRow, ...]
    base_T: FloatArray
    tool_T: FloatArray
    home_q: FloatArray
    display_name: str | None = None
    description: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    joint_names: tuple[str, ...] = ()
    link_names: tuple[str, ...] = ()
    joint_types: tuple[JointType, ...] = ()
    joint_axes: tuple[tuple[float, float, float], ...] = ()
    joint_limits: tuple[RobotJointLimit, ...] = ()
    structured_joints: tuple[RobotJointSpec, ...] = ()
    structured_links: tuple[RobotLinkSpec, ...] = ()
    kinematic_source: str = ''
    geometry_bundle_ref: str = ''
    collision_bundle_ref: str = ''
    source_model_summary: dict[str, object] = field(default_factory=dict)
    canonical_model: CanonicalRobotModel | None = None
    imported_package: 'ImportedRobotPackage' | None = None
    _runtime_model: 'RuntimeRobotModel' | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        rows = tuple(self.dh_rows)
        base_T = np.asarray(self.base_T, dtype=float)
        tool_T = np.asarray(self.tool_T, dtype=float)
        home_q = np.asarray(self.home_q, dtype=float).reshape(-1)
        if not rows:
            raise ValueError('robot spec requires at least one DH row')
        if base_T.shape != (4, 4) or tool_T.shape != (4, 4):
            raise ValueError('base_T and tool_T must both be 4x4')
        if home_q.shape != (len(rows),):
            raise ValueError(f'home_q shape mismatch, expected {(len(rows),)}, got {home_q.shape}')
        if not np.isfinite(base_T).all() or not np.isfinite(tool_T).all() or not np.isfinite(home_q).all():
            raise ValueError('robot spec contains non-finite base/tool/home values')
        object.__setattr__(self, 'dh_rows', rows)
        object.__setattr__(self, 'base_T', base_T.copy())
        object.__setattr__(self, 'tool_T', tool_T.copy())
        object.__setattr__(self, 'home_q', home_q.copy())
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        object.__setattr__(self, 'source_model_summary', dict(self.source_model_summary or {}))
        if self.canonical_model is not None and self.canonical_model.dof != len(rows):
            raise ValueError(
                f'canonical_model DOF mismatch: expected {len(rows)}, got {self.canonical_model.dof}'
            )
        if self.canonical_model is not None and self.canonical_model.execution_rows and len(self.canonical_model.execution_rows) != len(rows):
            raise ValueError(
                f'canonical_model execution row mismatch: expected {len(rows)}, got {len(self.canonical_model.execution_rows)}'
            )
        self._validate_structured_lengths()
        from robot_sim.model.runtime_robot_model import build_runtime_robot_model

        object.__setattr__(self, '_runtime_model', build_runtime_robot_model(self))

    def _validate_structured_lengths(self) -> None:
        dof = len(self.dh_rows)
        def _check_optional(values: tuple[object, ...], label: str) -> None:
            if values and len(values) != dof:
                raise ValueError(f'{label} length mismatch: expected {dof}, got {len(values)}')
        _check_optional(tuple(self.joint_names), 'joint_names')
        _check_optional(tuple(self.joint_types), 'joint_types')
        _check_optional(tuple(self.joint_axes), 'joint_axes')
        _check_optional(tuple(self.joint_limits), 'joint_limits')
        _check_optional(tuple(self.structured_joints), 'structured_joints')
        if self.link_names and len(self.link_names) < dof:
            raise ValueError('link_names must contain at least one link per DOF chain')
        if self.structured_links and len(self.structured_links) < dof:
            raise ValueError('structured_links must contain at least one link per DOF chain')

    @property
    def dof(self) -> int:
        return len(self.dh_rows)

    @property
    def runtime_model(self):
        """Return the structured runtime semantic model derived from this spec.

        Returns:
            RuntimeRobotModel: Stable runtime semantic contract describing the effective execution
                surface, naming, and joint limits consumed by downstream services.

        Raises:
            ValueError: Propagates invalid runtime-model invariants.
        """
        runtime_model = self._runtime_model
        if runtime_model is None:  # defensive path for deserialization edge cases
            from robot_sim.model.runtime_robot_model import build_runtime_robot_model

            runtime_model = build_runtime_robot_model(self)
            object.__setattr__(self, '_runtime_model', runtime_model)
        return runtime_model

    @property
    def articulated_model(self):
        """Return the articulated robot semantics projected from the strongest structured source.

        Returns:
            ArticulatedRobotModel: Structured articulated robot model aligned to the current
                runtime execution surface. Imported packages and canonical models take priority
                over legacy runtime DH projections so source joint axes/origins remain intact.

        Raises:
            ValueError: Propagates invalid articulated-model invariants.
        """
        imported_package = self.imported_package
        if imported_package is not None and imported_package.articulated_model is not None:
            return imported_package.articulated_model
        canonical_model = self.canonical_model
        if canonical_model is not None:
            from robot_sim.model.articulated_robot_model import build_articulated_robot_model_from_canonical

            return build_articulated_robot_model_from_canonical(
                canonical_model,
                base_T=self.base_T,
                tool_T=self.tool_T,
                home_q=self.home_q,
                source_surface='canonical_model',
                fidelity=str(canonical_model.fidelity or self.metadata.get('import_fidelity', '') or ''),
                metadata={'robot_spec_name': self.name},
            )
        return self.runtime_model.articulated_model

    @property
    def execution_rows(self) -> tuple[DHRow, ...]:
        """Return the canonical runtime execution rows consumed by solver surfaces.

        Returns:
            tuple[DHRow, ...]: Canonical execution rows when available, otherwise the legacy
                persisted ``dh_rows`` payload.

        Boundary behavior:
            Legacy persisted robots that predate canonical execution rows continue to run from
            ``dh_rows`` without migration.
        """
        return self.runtime_model.execution_rows

    @property
    def label(self) -> str:
        return self.display_name or self.name

    @property
    def kinematic_convention(self) -> str:
        return str(self.metadata.get('kinematic_convention', KinematicConvention.DH.value))

    @property
    def model_source(self) -> str:
        return str(self.metadata.get('model_source', self.kinematic_source or 'dh_config'))

    @property
    def geometry_available(self) -> bool:
        return bool(self.metadata.get('geometry_available', bool(self.geometry_bundle_ref)))

    @property
    def collision_model(self) -> str:
        return str(self.metadata.get('collision_model', 'none' if not self.collision_bundle_ref else 'structured'))

    @property
    def has_structured_model(self) -> bool:
        return bool(self.structured_joints or self.structured_links or self.source_model_summary)


    @property
    def has_canonical_model(self) -> bool:
        return self.canonical_model is not None

    @property
    def execution_summary(self) -> dict[str, object]:
        """Return the canonical runtime execution contract for this spec.

        Returns:
            dict[str, object]: Stable execution metadata consumed by runtime asset builders,
                diagnostics, persistence, and export-facing summaries.

        Boundary behavior:
            Older specs that predate explicit execution metadata still resolve a consistent
            summary from the runtime semantic projection rather than requiring downstream
            services to inspect legacy ``RobotSpec`` fields directly.
        """
        metadata = dict(self.metadata or {})
        base_summary = metadata.get('execution_summary')
        summary: dict[str, object]
        if isinstance(base_summary, Mapping):
            summary = dict(base_summary)
        else:
            summary = {}
        runtime_model = self.runtime_model
        summary.setdefault('execution_adapter', runtime_model.execution_adapter)
        summary.setdefault('execution_surface', runtime_model.source_surface)
        summary.setdefault('primary_execution_surface', 'articulated_model')
        summary['execution_row_count'] = int(runtime_model.dof)
        summary['runtime_semantic_family'] = runtime_model.semantic_family
        summary['runtime_source_format'] = runtime_model.source_format
        summary['runtime_fidelity'] = runtime_model.fidelity
        summary['execution_contract_version'] = str(runtime_model.summary().get('execution_contract_version', 'v2'))
        summary['execution_layers'] = dict(runtime_model.execution_layers)
        summary['articulated_topology'] = dict(self.articulated_model.topology_summary)
        return summary

    @property
    def runtime_joint_names(self) -> tuple[str, ...]:
        """Return canonical runtime joint names aligned to the execution surface."""
        return self.runtime_model.joint_names

    @property
    def runtime_link_names(self) -> tuple[str, ...]:
        """Return canonical runtime link names aligned to the execution surface."""
        return self.runtime_model.link_names

    @property
    def runtime_joint_limits(self) -> tuple[RobotJointLimit, ...]:
        """Return canonical runtime joint limits aligned to the execution surface."""
        return self.runtime_model.joint_limits

    def q_mid(self) -> FloatArray:
        return np.array([(r.q_min + r.q_max) * 0.5 for r in self.execution_rows], dtype=float)
