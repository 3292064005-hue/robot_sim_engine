from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from robot_sim.model.execution_capability_matrix import (
    ExecutionCapabilityMatrix,
    execution_capability_ontology,
    normalize_supported_strategies,
)
from robot_sim.model.execution_graph import ExecutionGraphDescriptor, default_execution_graph_descriptor

_ALLOWED_EXECUTION_STRATEGIES = {'serial_tree', 'active_path_over_tree', 'full_tree'}


@dataclass(frozen=True)
class ExecutionScopeService:
    """Resolve the runtime execution scope into one stable, fail-closed descriptor.

    The runtime may now advertise a wider execution ladder, but negotiation remains strict:
    callers only obtain a descriptor when the selected strategy/closed-loop/mobile-base flags are
    explicitly supported by the runtime/provider surface exposed by the loaded robot spec.
    """

    def resolve_descriptor(self, spec, payload: Mapping[str, object] | None = None) -> ExecutionGraphDescriptor:
        """Materialize the canonical execution-scope descriptor for a workflow request.

        Args:
            spec: Canonical robot specification providing runtime execution metadata.
            payload: Optional caller overrides for the negotiated execution descriptor.

        Returns:
            ExecutionGraphDescriptor: Descriptor enriched with capability/support metadata.

        Raises:
            ValueError: If the caller requests unsupported execution semantics or references
                unknown joints/links.
        """
        raw = {str(key): value for key, value in dict(payload or {}).items()}
        self._validate_requested_surface(raw)
        descriptor = default_execution_graph_descriptor(spec, raw)
        execution_summary = dict(getattr(spec, 'execution_summary', {}) or {})
        runtime_strategy = str(execution_summary.get('branched_tree_execution_mode', descriptor.supported_scope.get('strategy', descriptor.strategy)) or descriptor.strategy)
        runtime_full_tree = bool(execution_summary.get('supports_full_tree_execution', False))
        runtime_closed_loop = bool(execution_summary.get('closed_loop_supported', False))
        runtime_mobile_base = bool(execution_summary.get('mobile_base_supported', False))
        selected_strategy = str(descriptor.selected_scope.get('strategy', descriptor.strategy) or descriptor.strategy)
        selected_closed_loop = bool(descriptor.selected_scope.get('closed_loop_requested', False))
        selected_mobile_base = bool(descriptor.selected_scope.get('mobile_base_requested', False))
        capability_matrix = ExecutionCapabilityMatrix.from_spec(spec).with_runtime_support(
            strategy=runtime_strategy,
            full_tree=runtime_full_tree,
            closed_loop=runtime_closed_loop,
            mobile_base=runtime_mobile_base,
            selected_strategy=selected_strategy,
            selected_closed_loop=selected_closed_loop,
            selected_mobile_base=selected_mobile_base,
        )
        ontology = execution_capability_ontology(
            strategy=runtime_strategy,
            full_tree=runtime_full_tree,
            closed_loop=runtime_closed_loop,
            mobile_base=runtime_mobile_base,
            selected_strategy=selected_strategy,
            selected_closed_loop=selected_closed_loop,
            selected_mobile_base=selected_mobile_base,
        )
        supported_scope = {
            **dict(descriptor.supported_scope or {}),
            'supports_full_tree_execution': runtime_full_tree,
            'strategy': runtime_strategy,
            'supported_execution_strategies': list(
                normalize_supported_strategies(
                    execution_summary.get('supported_execution_strategies', descriptor.supported_scope)
                )
            ),
            'closed_loop_supported': runtime_closed_loop,
            'mobile_base_supported': runtime_mobile_base,
            'execution_scope_policy': 'fail_closed',
            'capability_ontology': ontology,
        }
        selected_scope = {
            **dict(descriptor.selected_scope or {}),
            'selected_active_joint_count': len(descriptor.active_joint_names),
            'selected_target_link_count': len(descriptor.target_links),
            'selected_execution_level': ontology['selected_execution_level'],
        }
        source_topology = {
            **dict(descriptor.source_topology or {}),
            'execution_adapter': str(execution_summary.get('execution_adapter', descriptor.metadata.get('execution_adapter', 'robot_spec_execution_rows'))),
            'execution_surface': str(execution_summary.get('execution_surface', descriptor.source_surface or 'robot_spec') or descriptor.source_surface or 'robot_spec'),
            'execution_row_count': int(execution_summary.get('execution_row_count', getattr(spec, 'dof', 0)) or getattr(spec, 'dof', 0)),
            'capability_matrix': capability_matrix.as_dict(),
            'capability_ontology': ontology,
        }
        self._validate_negotiated_scope(source_topology, selected_scope, supported_scope)
        metadata = {
            **dict(descriptor.metadata),
            'execution_scope_policy': 'fail_closed',
            'selected_active_joint_count': len(descriptor.active_joint_names),
            'selected_target_link_count': len(descriptor.target_links),
            'supports_full_tree_execution': runtime_full_tree,
            'branched_tree_execution_mode': runtime_strategy,
            'closed_loop_supported': runtime_closed_loop,
            'mobile_base_supported': runtime_mobile_base,
            'solver_capability_negotiated': True,
            'execution_capability_matrix': capability_matrix.as_dict(),
            'execution_capability_ontology': ontology,
        }
        return replace(
            descriptor,
            strategy=selected_strategy,
            closed_loop_supported=runtime_closed_loop,
            selected_execution_level=str(ontology['selected_execution_level']),
            supported_execution_levels=tuple(ontology['supported_execution_levels']),
            source_topology=source_topology,
            selected_scope=selected_scope,
            supported_scope=supported_scope,
            metadata=metadata,
        )

    @staticmethod
    def _validate_negotiated_scope(
        source_topology: Mapping[str, object],
        selected_scope: Mapping[str, object],
        supported_scope: Mapping[str, object],
    ) -> None:
        strategy = str(selected_scope.get('strategy', 'active_path_over_tree') or 'active_path_over_tree')
        supported_strategies = tuple(
            str(item) for item in supported_scope.get('supported_execution_strategies', (supported_scope.get('strategy', 'active_path_over_tree'),)) or ()
        )
        if strategy not in supported_strategies:
            raise ValueError(
                'requested execution scope is incompatible with the current runtime: '
                f'{strategy!r} requested but supported={list(supported_strategies)!r}'
            )
        if bool(supported_scope.get('supports_full_tree_execution', False)) is False and strategy == 'full_tree':
            raise ValueError('full-tree execution is not supported by the current runtime')
        if bool(supported_scope.get('closed_loop_supported', False)) is False and bool(selected_scope.get('closed_loop_requested', False)):
            raise ValueError('closed-loop execution is not supported by the current runtime')
        if bool(supported_scope.get('mobile_base_supported', False)) is False and bool(selected_scope.get('mobile_base_requested', False)):
            raise ValueError('mobile-base execution is not supported by the current runtime')
        if not tuple(str(item) for item in source_topology.get('joint_names', ()) or ()):  # pragma: no cover - defensive contract guard
            raise ValueError('execution scope source topology is missing joint_names')

    @staticmethod
    def _validate_requested_surface(raw: Mapping[str, object]) -> None:
        strategy = str(raw.get('strategy', 'active_path_over_tree') or 'active_path_over_tree')
        if strategy not in _ALLOWED_EXECUTION_STRATEGIES:
            raise ValueError(
                'unsupported execution_graph.strategy: '
                f'{strategy!r}; supported_request_values={sorted(_ALLOWED_EXECUTION_STRATEGIES)!r}'
            )
        if bool(raw.get('closed_loop_supported', False)):
            raise ValueError(
                'execution_graph.closed_loop_supported is runtime-owned metadata and cannot be '
                'asserted by callers'
            )
        if bool(raw.get('mobile_base_supported', False)):
            raise ValueError(
                'execution_graph.mobile_base_supported is runtime-owned metadata and cannot be '
                'asserted by callers'
            )
