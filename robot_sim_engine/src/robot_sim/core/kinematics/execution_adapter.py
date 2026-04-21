from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.model.articulated_robot_model import ArticulatedJointModel, ArticulatedRobotModel
    from robot_sim.model.robot_spec import RobotSpec


@dataclass(frozen=True)
class ExecutionAdapterDescriptor:
    """Stable description of the active articulated execution adapter.

    Attributes:
        adapter_id: Stable runtime adapter identifier.
        semantic_family: Source articulated semantic family.
        execution_semantics: Concrete execution scope used by FK/Jacobian/IK.
        execution_joint_indices: Dynamic-joint indices participating in the active execution path.
        execution_tip_joint_index: Terminal dynamic-joint index for the active execution path.
        supports_tree_projection: Whether the source graph preserves branched topology.
        supports_active_path_execution: Whether the adapter can execute one stable EE path.
        supports_full_tree_execution: Whether the runtime can solve against every leaf concurrently.
    """

    adapter_id: str
    semantic_family: str
    execution_semantics: str
    execution_joint_indices: tuple[int, ...]
    execution_tip_joint_index: int
    supports_tree_projection: bool
    supports_active_path_execution: bool
    supports_full_tree_execution: bool = False

    def summary(self) -> dict[str, object]:
        return {
            'adapter_id': self.adapter_id,
            'semantic_family': self.semantic_family,
            'execution_semantics': self.execution_semantics,
            'execution_joint_indices': [int(index) for index in self.execution_joint_indices],
            'execution_tip_joint_index': int(self.execution_tip_joint_index),
            'supports_tree_projection': bool(self.supports_tree_projection),
            'supports_active_path_execution': bool(self.supports_active_path_execution),
            'supports_full_tree_execution': bool(self.supports_full_tree_execution),
        }


class ExecutionAdapter:
    """Adapter exposing the active articulated execution path.

    The adapter keeps the full articulated graph available for diagnostics while presenting one
    deterministic end-effector path to FK/Jacobian/IK/benchmark callers. Serial chains map to the
    identity adapter; branched graphs resolve the strongest root-to-leaf dynamic path.
    """

    def __init__(self, articulated_model: 'ArticulatedRobotModel') -> None:
        self._articulated = articulated_model
        descriptor = articulated_model.execution_descriptor
        self._descriptor = descriptor
        if not descriptor.execution_joint_indices:
            raise ValueError('execution adapter requires at least one active execution joint')

    @property
    def articulated_model(self) -> 'ArticulatedRobotModel':
        return self._articulated

    @property
    def descriptor(self) -> ExecutionAdapterDescriptor:
        return self._descriptor

    @property
    def active_joint_indices(self) -> tuple[int, ...]:
        return self._descriptor.execution_joint_indices

    @property
    def tip_joint_index(self) -> int:
        return int(self._descriptor.execution_tip_joint_index)

    @property
    def joint_models(self) -> tuple['ArticulatedJointModel', ...]:
        return tuple(self._articulated.joint_models[index] for index in self.active_joint_indices)

    @property
    def graph_dof(self) -> int:
        return self._articulated.dof

    @property
    def dof(self) -> int:
        return len(self.active_joint_indices)

    @property
    def active_dof(self) -> int:
        return self.dof

    @property
    def joint_minima(self) -> np.ndarray:
        return np.asarray([joint.limit.lower for joint in self.joint_models], dtype=float)

    @property
    def joint_maxima(self) -> np.ndarray:
        return np.asarray([joint.limit.upper for joint in self.joint_models], dtype=float)

    def require_active_path_execution(self) -> None:
        if not self._descriptor.supports_active_path_execution:
            raise ValueError(
                'articulated robot model does not expose an active execution path: '
                f'{self._descriptor.semantic_family!r}'
            )

    def active_joint_mask(self) -> np.ndarray:
        return np.ones((self.dof,), dtype=bool)

    def _graph_q(self, q: np.ndarray) -> np.ndarray:
        q_arr = np.asarray(q, dtype=float).reshape(-1)
        if q_arr.shape == (self.graph_dof,):
            return q_arr.copy()
        if q_arr.shape != (self.dof,):
            raise ValueError(f'execution adapter joint vector mismatch: expected {(self.dof,)} or {(self.graph_dof,)}, got {q_arr.shape}')
        graph_q = np.asarray(self._articulated.home_q, dtype=float).reshape(self.graph_dof).copy()
        for local_index, graph_index in enumerate(self.active_joint_indices):
            graph_q[int(graph_index)] = float(q_arr[local_index])
        return graph_q

    def forward_graph_transforms(self, q: np.ndarray) -> tuple[np.ndarray, ...]:
        return self._articulated.graph_forward_transforms(self._graph_q(q))

    def forward_transforms(self, q: np.ndarray) -> tuple[np.ndarray, ...]:
        return self._articulated.execution_forward_transforms(self._graph_q(q))

    def world_joint_axes_origins(self, q: np.ndarray) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
        return self._articulated.graph_world_joint_axes_origins(self._graph_q(q))

    def active_path_axes_origins(self, q: np.ndarray) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
        pairs = self.world_joint_axes_origins(q)
        return tuple(pairs[index] for index in self.active_joint_indices)

    def rough_reach_radius(self) -> float:
        radius = 0.0
        for index in self.active_joint_indices:
            joint = self._articulated.joint_models[index]
            radius += float(np.linalg.norm(np.asarray(joint.origin_translation, dtype=float)))
        radius += float(np.linalg.norm(np.asarray(self._articulated.tool_T[:3, 3], dtype=float)))
        return radius if radius > 0.0 else 1.0


def resolve_execution_adapter(spec: 'RobotSpec') -> ExecutionAdapter:
    """Resolve the canonical articulated execution adapter for one robot specification.

    Args:
        spec: Robot specification exposing an articulated model.

    Returns:
        ExecutionAdapter: Adapter describing the active execution surface.

    Raises:
        ValueError: Propagates articulated-model invariants when no active execution path exists.
    """
    return ExecutionAdapter(spec.articulated_model)
