from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

_EXECUTION_LEVEL_ORDER: tuple[str, ...] = (
    'l0_serial_tree',
    'l1_active_path_over_tree',
    'l2_full_tree',
    'l3_closed_loop_mobile_base',
)


@dataclass(frozen=True)
class ExecutionCapabilityMatrix:
    """Unified capability contract separating source fidelity from runtime execution support.

    The matrix is the canonical capability ontology projected into runtime summaries,
    request metadata, diagnostics, export/session bundles, and future provider selection.
    """

    import_fidelity: str = 'unknown'
    source_topology_family: str = 'unknown'
    scene_fidelity: str = 'unknown'
    collision_fidelity: str = 'unknown'
    execution_strategy: str = 'active_path_over_tree'
    selected_execution_level: str = 'l1_active_path_over_tree'
    supported_execution_levels: tuple[str, ...] = ('l0_serial_tree', 'l1_active_path_over_tree')
    supports_branched_tree_projection: bool = False
    supports_active_path_execution: bool = True
    supports_full_tree_execution: bool = False
    supports_closed_loop_execution: bool = False
    supports_mobile_base_execution: bool = False
    ontology_version: str = 'v2'
    notes: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_spec(cls, spec) -> 'ExecutionCapabilityMatrix':
        metadata = dict(getattr(spec, 'metadata', {}) or {})
        execution_summary = dict(getattr(spec, 'execution_summary', {}) or {})
        articulated_topology = dict(execution_summary.get('articulated_topology', {}) or {})
        scene_summary = dict(metadata.get('scene_fidelity_summary', {}) or {})
        collision_summary = dict(metadata.get('collision_fidelity_summary', {}) or {})
        notes = [str(item) for item in metadata.get('warnings', ()) or ()]
        strategy = str(
            execution_summary.get('branched_tree_execution_mode', execution_summary.get('execution_scope', 'active_path_over_tree'))
            or 'active_path_over_tree'
        )
        closed_loop = bool(execution_summary.get('closed_loop_supported', False))
        mobile_base = bool(execution_summary.get('mobile_base_supported', False))
        full_tree = bool(execution_summary.get('supports_full_tree_execution', False))
        return cls(
            import_fidelity=str(metadata.get('import_fidelity', 'unknown') or 'unknown'),
            source_topology_family=str(
                execution_summary.get(
                    'runtime_semantic_family',
                    getattr(getattr(spec, 'runtime_model', None), 'semantic_family', 'unknown'),
                )
                or 'unknown'
            ),
            scene_fidelity=str(
                scene_summary.get('scene_fidelity', metadata.get('scene_fidelity', 'unknown'))
                or metadata.get('scene_fidelity', 'unknown')
                or 'unknown'
            ),
            collision_fidelity=str(
                collision_summary.get('level', metadata.get('collision_level', 'unknown'))
                or metadata.get('collision_level', 'unknown')
                or 'unknown'
            ),
            execution_strategy=strategy,
            selected_execution_level=execution_level_for(
                strategy,
                closed_loop=closed_loop,
                mobile_base=mobile_base,
            ),
            supported_execution_levels=supported_execution_levels(
                full_tree=full_tree,
                closed_loop=closed_loop,
                mobile_base=mobile_base,
            ),
            supports_branched_tree_projection=bool(
                articulated_topology.get('supports_branched_tree_projection', metadata.get('branched_tree_supported', False))
            ),
            supports_active_path_execution=True,
            supports_full_tree_execution=full_tree,
            supports_closed_loop_execution=closed_loop,
            supports_mobile_base_execution=mobile_base,
            notes=tuple(notes),
            metadata={
                'execution_adapter': str(execution_summary.get('execution_adapter', '')),
                'execution_surface': str(execution_summary.get('execution_surface', '')),
                'source_model_retained': bool(metadata.get('source_model_retained', False)),
                'capability_ontology_version': 'v2',
                'level_order': list(_EXECUTION_LEVEL_ORDER),
            },
        )

    def as_dict(self) -> dict[str, object]:
        return {
            'import_fidelity': self.import_fidelity,
            'source_topology_family': self.source_topology_family,
            'scene_fidelity': self.scene_fidelity,
            'collision_fidelity': self.collision_fidelity,
            'execution_strategy': self.execution_strategy,
            'selected_execution_level': self.selected_execution_level,
            'supported_execution_levels': list(self.supported_execution_levels),
            'supports_branched_tree_projection': bool(self.supports_branched_tree_projection),
            'supports_active_path_execution': bool(self.supports_active_path_execution),
            'supports_full_tree_execution': bool(self.supports_full_tree_execution),
            'supports_closed_loop_execution': bool(self.supports_closed_loop_execution),
            'supports_mobile_base_execution': bool(self.supports_mobile_base_execution),
            'ontology_version': self.ontology_version,
            'notes': list(self.notes),
            'metadata': dict(self.metadata),
        }

    def with_runtime_support(
        self,
        *,
        strategy: str,
        full_tree: bool,
        closed_loop: bool,
        mobile_base: bool,
        selected_strategy: str | None = None,
        selected_closed_loop: bool | None = None,
        selected_mobile_base: bool | None = None,
    ) -> 'ExecutionCapabilityMatrix':
        selected_runtime_strategy = str(selected_strategy or strategy)
        selected_runtime_closed_loop = bool(closed_loop if selected_closed_loop is None else selected_closed_loop)
        selected_runtime_mobile_base = bool(mobile_base if selected_mobile_base is None else selected_mobile_base)
        return ExecutionCapabilityMatrix(
            import_fidelity=self.import_fidelity,
            source_topology_family=self.source_topology_family,
            scene_fidelity=self.scene_fidelity,
            collision_fidelity=self.collision_fidelity,
            execution_strategy=str(strategy),
            selected_execution_level=execution_level_for(
                selected_runtime_strategy,
                closed_loop=selected_runtime_closed_loop,
                mobile_base=selected_runtime_mobile_base,
            ),
            supported_execution_levels=supported_execution_levels(
                full_tree=bool(full_tree),
                closed_loop=bool(closed_loop),
                mobile_base=bool(mobile_base),
            ),
            supports_branched_tree_projection=bool(self.supports_branched_tree_projection),
            supports_active_path_execution=bool(self.supports_active_path_execution),
            supports_full_tree_execution=bool(full_tree),
            supports_closed_loop_execution=bool(closed_loop),
            supports_mobile_base_execution=bool(mobile_base),
            ontology_version=self.ontology_version,
            notes=self.notes,
            metadata=dict(self.metadata),
        )


def execution_level_for(
    strategy: str,
    *,
    closed_loop: bool = False,
    mobile_base: bool = False,
) -> str:
    """Project one runtime strategy into the canonical execution-level ladder."""
    normalized_strategy = str(strategy or 'active_path_over_tree').strip().lower() or 'active_path_over_tree'
    if bool(closed_loop) or bool(mobile_base):
        return 'l3_closed_loop_mobile_base'
    if normalized_strategy == 'full_tree':
        return 'l2_full_tree'
    if normalized_strategy == 'serial_tree':
        return 'l0_serial_tree'
    return 'l1_active_path_over_tree'


def supported_execution_levels(*, full_tree: bool, closed_loop: bool, mobile_base: bool) -> tuple[str, ...]:
    """Return the ordered execution levels supported by one runtime/provider surface."""
    levels = ['l0_serial_tree', 'l1_active_path_over_tree']
    if bool(full_tree):
        levels.append('l2_full_tree')
    if bool(closed_loop) or bool(mobile_base):
        if 'l2_full_tree' not in levels:
            levels.append('l2_full_tree')
        levels.append('l3_closed_loop_mobile_base')
    return tuple(levels)


def execution_capability_ontology(
    *,
    strategy: str,
    full_tree: bool,
    closed_loop: bool,
    mobile_base: bool,
    selected_strategy: str | None = None,
    selected_closed_loop: bool | None = None,
    selected_mobile_base: bool | None = None,
) -> dict[str, object]:
    """Return the cross-surface ontology payload consumed by runtime/export/session/docs."""
    supported_levels = supported_execution_levels(
        full_tree=bool(full_tree),
        closed_loop=bool(closed_loop),
        mobile_base=bool(mobile_base),
    )
    selected_level = execution_level_for(
        str(selected_strategy or strategy),
        closed_loop=bool(closed_loop if selected_closed_loop is None else selected_closed_loop),
        mobile_base=bool(mobile_base if selected_mobile_base is None else selected_mobile_base),
    )
    return {
        'ontology_version': 'v2',
        'supported_execution_levels': list(supported_levels),
        'selected_execution_level': selected_level,
        'level_order': list(_EXECUTION_LEVEL_ORDER),
        'execution_strategy': str(strategy),
        'selected_strategy': str(selected_strategy or strategy),
        'supports_full_tree_execution': bool(full_tree),
        'supports_closed_loop_execution': bool(closed_loop),
        'supports_mobile_base_execution': bool(mobile_base),
    }


def normalize_supported_strategies(raw: Sequence[object] | Mapping[str, object] | None = None) -> tuple[str, ...]:
    """Normalize explicit/implicit runtime-supported execution strategies."""
    strategies: list[str] = ['active_path_over_tree']
    if isinstance(raw, Mapping):
        raw_values = raw.get('supported_execution_strategies', ()) or ()
    else:
        raw_values = raw or ()
    for item in raw_values:
        token = str(item or '').strip()
        if not token or token in strategies:
            continue
        strategies.append(token)
    return tuple(strategies)
