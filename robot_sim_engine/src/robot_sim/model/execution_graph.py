from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from robot_sim.model.execution_capability_matrix import execution_level_for, normalize_supported_strategies


@dataclass(frozen=True)
class ExecutionGraphDescriptor:
    """Stable execution-graph descriptor threaded through IK, planning, and benchmark flows.

    The descriptor now carries the selected execution level together with the runtime-supported
    level ladder. Callers can therefore negotiate future full-tree / closed-loop / mobile-base
    providers without fabricating support when the active runtime remains narrower.
    """

    descriptor_id: str = 'active_path_default'
    strategy: str = 'active_path_over_tree'
    source_surface: str = 'robot_spec'
    frame_ids: tuple[str, ...] = ()
    active_joint_names: tuple[str, ...] = ()
    target_links: tuple[str, ...] = ()
    supports_branched_tree_projection: bool = False
    closed_loop_supported: bool = False
    selected_execution_level: str = 'l1_active_path_over_tree'
    supported_execution_levels: tuple[str, ...] = ('l0_serial_tree', 'l1_active_path_over_tree')
    source_topology: dict[str, object] = field(default_factory=dict)
    selected_scope: dict[str, object] = field(default_factory=dict)
    supported_scope: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'frame_ids', tuple(str(item) for item in self.frame_ids if str(item)))
        object.__setattr__(self, 'active_joint_names', tuple(str(item) for item in self.active_joint_names if str(item)))
        object.__setattr__(self, 'target_links', tuple(str(item) for item in self.target_links if str(item)))
        object.__setattr__(self, 'supported_execution_levels', tuple(str(item) for item in self.supported_execution_levels if str(item)))
        object.__setattr__(self, 'source_topology', dict(self.source_topology or {}))
        object.__setattr__(self, 'selected_scope', dict(self.selected_scope or {}))
        object.__setattr__(self, 'supported_scope', dict(self.supported_scope or {}))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))

    def summary(self) -> dict[str, object]:
        """Return a JSON-serializable execution-graph summary."""
        return {
            'descriptor_id': str(self.descriptor_id),
            'strategy': str(self.strategy),
            'source_surface': str(self.source_surface),
            'frame_ids': list(self.frame_ids),
            'active_joint_names': list(self.active_joint_names),
            'target_links': list(self.target_links),
            'supports_branched_tree_projection': bool(self.supports_branched_tree_projection),
            'closed_loop_supported': bool(self.closed_loop_supported),
            'selected_execution_level': str(self.selected_execution_level),
            'supported_execution_levels': list(self.supported_execution_levels),
            'source_topology': dict(self.source_topology),
            'selected_scope': dict(self.selected_scope),
            'supported_scope': dict(self.supported_scope),
            'metadata': dict(self.metadata),
        }


def default_execution_graph_descriptor(spec, payload: Mapping[str, object] | None = None) -> ExecutionGraphDescriptor:
    """Build the canonical execution-graph descriptor for the current runtime surface.

    Args:
        spec: Canonical robot specification providing runtime/execution metadata.
        payload: Optional caller overrides for active joints, target links, or descriptor labels.

    Returns:
        ExecutionGraphDescriptor: Stable descriptor that documents the current execution scope.

    Raises:
        ValueError: If caller-provided joint or link selectors reference unknown runtime names.
    """
    raw = dict(payload or {})
    execution_summary = dict(getattr(spec, 'execution_summary', {}) or {})
    execution_layers = dict(execution_summary.get('execution_layers', {}) or {})
    articulated_layer = dict(execution_layers.get('articulated_graph', {}) or {})
    known_joint_names = tuple(str(item) for item in getattr(spec, 'runtime_joint_names', ()) or ())
    known_link_names = tuple(str(item) for item in getattr(spec, 'runtime_link_names', ()) or ())
    requested_joint_names = tuple(str(item) for item in raw.get('active_joint_names', ()) or ())
    requested_target_links = tuple(str(item) for item in raw.get('target_links', ()) or ())
    if requested_joint_names:
        unknown = sorted(set(requested_joint_names) - set(known_joint_names))
        if unknown:
            raise ValueError(f'unknown execution_graph.active_joint_names: {unknown}')
        active_joint_names = requested_joint_names
    else:
        active_joint_names = known_joint_names
    if requested_target_links:
        unknown = sorted(set(requested_target_links) - set(known_link_names))
        if unknown:
            raise ValueError(f'unknown execution_graph.target_links: {unknown}')
        target_links = requested_target_links
    elif known_link_names:
        target_links = (known_link_names[-1],)
    else:
        target_links = ()
    frame_ids = tuple(str(item) for item in raw.get('frame_ids', ()) or ()) or tuple(dict.fromkeys(('world', *known_link_names)))
    supported_strategy = str(
        execution_summary.get('branched_tree_execution_mode', execution_summary.get('execution_scope', 'active_path_over_tree'))
        or 'active_path_over_tree'
    )
    selected_strategy = str(raw.get('strategy', supported_strategy) or supported_strategy)
    selected_closed_loop = bool(raw.get('closed_loop_requested', False))
    selected_mobile_base = bool(raw.get('mobile_base_requested', False))
    metadata = {
        'execution_adapter': str(execution_summary.get('execution_adapter', 'robot_spec_execution_rows') or 'robot_spec_execution_rows'),
        'execution_surface': str(execution_summary.get('execution_surface', 'robot_spec') or 'robot_spec'),
        'execution_row_count': int(execution_summary.get('execution_row_count', getattr(spec, 'dof', 0)) or getattr(spec, 'dof', 0)),
        'primary_execution_surface': str(execution_summary.get('primary_execution_surface', 'articulated_model') or 'articulated_model'),
        'runtime_semantic_family': str(execution_summary.get('runtime_semantic_family', getattr(spec.runtime_model, 'semantic_family', '')) or getattr(spec.runtime_model, 'semantic_family', '')),
        'articulated_topology': dict(execution_summary.get('articulated_topology', {}) or {}),
        'supports_branched_tree_projection': bool(articulated_layer.get('supports_branched_tree_projection', False)),
        'branching_link_names': [str(item) for item in articulated_layer.get('branching_link_names', ()) or ()],
        'graph_edge_pairs': [list(item) for item in articulated_layer.get('graph_edge_pairs', ()) or ()],
        'capability_ontology_version': 'v2',
    }
    metadata.update(dict(raw.get('metadata', {}) or {}))
    supported_full_tree = bool(execution_summary.get('supports_full_tree_execution', False))
    supported_closed_loop = bool(execution_summary.get('closed_loop_supported', False))
    supported_mobile_base = bool(execution_summary.get('mobile_base_supported', False))
    supported_execution_levels = ['l0_serial_tree', 'l1_active_path_over_tree']
    if supported_full_tree:
        supported_execution_levels.append('l2_full_tree')
    if supported_closed_loop or supported_mobile_base:
        if 'l2_full_tree' not in supported_execution_levels:
            supported_execution_levels.append('l2_full_tree')
        supported_execution_levels.append('l3_closed_loop_mobile_base')
    source_topology = {
        'semantic_family': str(getattr(spec.runtime_model, 'semantic_family', '') or metadata.get('runtime_semantic_family', '')),
        'root_link': str(articulated_layer.get('root_link', (known_link_names[0] if known_link_names else 'world')) or (known_link_names[0] if known_link_names else 'world')),
        'joint_names': list(known_joint_names),
        'link_names': list(known_link_names),
        'graph_edge_pairs': [list(item) for item in articulated_layer.get('graph_edge_pairs', ()) or []],
        'supports_branched_tree_projection': bool(articulated_layer.get('supports_branched_tree_projection', False)),
        'supported_execution_strategies': list(
            normalize_supported_strategies(
                execution_summary.get('supported_execution_strategies', (('full_tree',) if supported_full_tree else ()))
            )
        ),
    }
    selected_scope = {
        'strategy': selected_strategy,
        'active_joint_names': list(active_joint_names),
        'target_links': list(target_links),
        'frame_ids': list(frame_ids),
        'selection_source': 'request_payload' if raw else 'runtime_default',
        'closed_loop_requested': selected_closed_loop,
        'mobile_base_requested': selected_mobile_base,
        'selected_execution_level': execution_level_for(
            selected_strategy,
            closed_loop=selected_closed_loop,
            mobile_base=selected_mobile_base,
        ),
    }
    supported_scope = {
        'strategy': supported_strategy,
        'supported_execution_strategies': list(
            normalize_supported_strategies(
                execution_summary.get('supported_execution_strategies', (('full_tree',) if supported_full_tree else ()))
            )
        ),
        'supports_full_tree_execution': supported_full_tree,
        'closed_loop_supported': supported_closed_loop,
        'mobile_base_supported': supported_mobile_base,
        'allow_joint_subset_selection': True,
        'allow_target_link_subset_selection': True,
        'supported_execution_levels': list(supported_execution_levels),
    }
    return ExecutionGraphDescriptor(
        descriptor_id=str(raw.get('descriptor_id', 'active_path_default') or 'active_path_default'),
        strategy=selected_strategy,
        source_surface=str(raw.get('source_surface', execution_summary.get('execution_surface', 'robot_spec')) or execution_summary.get('execution_surface', 'robot_spec')),
        frame_ids=frame_ids,
        active_joint_names=active_joint_names,
        target_links=target_links,
        supports_branched_tree_projection=bool(metadata.get('supports_branched_tree_projection', False)),
        closed_loop_supported=supported_closed_loop,
        selected_execution_level=str(selected_scope['selected_execution_level']),
        supported_execution_levels=tuple(supported_execution_levels),
        source_topology=source_topology,
        selected_scope=selected_scope,
        supported_scope=supported_scope,
        metadata=metadata,
    )
