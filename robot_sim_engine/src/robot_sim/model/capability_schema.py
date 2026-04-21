from __future__ import annotations

from typing import Mapping


def _coerce_mapping(payload: Mapping[str, object] | dict[str, object] | None) -> dict[str, object]:
    return dict(payload or {})


def build_runtime_capability_schema(
    *,
    execution_summary: Mapping[str, object] | None = None,
    imported_package_summary: Mapping[str, object] | None = None,
    scene_fidelity_summary: Mapping[str, object] | None = None,
    scene_snapshot: Mapping[str, object] | None = None,
    plugin_snapshot: Mapping[str, object] | None = None,
    capability_snapshot: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the unified runtime capability schema projected across export/session surfaces.

    Args:
        execution_summary: Robot execution/runtime summary produced during import/runtime negotiation.
        imported_package_summary: Import/package fidelity summary.
        scene_fidelity_summary: Session/export scene fidelity projection.
        scene_snapshot: Authoritative environment snapshot.
        plugin_snapshot: Plugin governance/runtime-provider snapshot.
        capability_snapshot: Full capability matrix snapshot.

    Returns:
        dict[str, object]: Unified, cross-surface capability ontology.

    Raises:
        None: Defensive normalization only.
    """
    execution_payload = _coerce_mapping(execution_summary)
    descriptor = _coerce_mapping(execution_payload.get('descriptor'))
    selected_scope = _coerce_mapping(descriptor.get('selected_scope'))
    supported_scope = _coerce_mapping(descriptor.get('supported_scope'))
    source_topology = _coerce_mapping(descriptor.get('source_topology'))
    execution_ontology = _coerce_mapping(
        execution_payload.get('capability_ontology')
        or execution_payload.get('execution_capability_ontology')
        or selected_scope.get('capability_ontology')
        or source_topology.get('capability_ontology')
    )

    import_payload = _coerce_mapping(imported_package_summary)
    fidelity_breakdown = _coerce_mapping(import_payload.get('fidelity_breakdown'))
    scene_payload = _coerce_mapping(scene_fidelity_summary)
    environment_payload = _coerce_mapping(scene_snapshot)
    environment_contract = _coerce_mapping(environment_payload.get('environment_contract'))
    plugin_payload = _coerce_mapping(plugin_snapshot)
    plugin_counts = _coerce_mapping(plugin_payload.get('catalog_counts'))
    capability_payload = _coerce_mapping(capability_snapshot)

    return {
        'ontology_version': 'v2',
        'execution': {
            'selected_strategy': str(selected_scope.get('strategy', execution_ontology.get('selected_strategy', '')) or ''),
            'selected_execution_level': str(execution_ontology.get('selected_execution_level', descriptor.get('selected_execution_level', '')) or ''),
            'supported_execution_levels': list(execution_ontology.get('supported_execution_levels', descriptor.get('supported_execution_levels', ())) or []),
            'supports_full_tree_execution': bool(execution_ontology.get('supports_full_tree_execution', supported_scope.get('supports_full_tree_execution', False))),
            'supports_closed_loop_execution': bool(execution_ontology.get('supports_closed_loop_execution', supported_scope.get('supports_closed_loop_execution', False))),
            'mobile_base_supported': bool(execution_ontology.get('mobile_base_supported', source_topology.get('mobile_base_supported', False))),
            'topology_family': str(execution_ontology.get('topology_family', source_topology.get('topology_family', source_topology.get('source_topology_family', '')) ) or ''),
            'ontology': execution_ontology,
        },
        'import': {
            'fidelity_breakdown': fidelity_breakdown,
            'source_format': str(import_payload.get('source_format', '') or ''),
            'source_topology': _coerce_mapping(import_payload.get('source_topology')),
            'geometry_model': _coerce_mapping(import_payload.get('geometry_model')),
        },
        'scene': {
            'scene_fidelity': str(scene_payload.get('scene_fidelity', environment_payload.get('scene_fidelity', '')) or ''),
            'scene_geometry_contract': str(scene_payload.get('scene_geometry_contract', environment_payload.get('scene_geometry_contract', '')) or ''),
            'environment_contract': environment_contract,
            'supports_clone': bool(environment_contract.get('supports_clone', False)),
            'supports_replay': bool(environment_contract.get('supports_replay', False)),
            'supports_diff_replication': bool(environment_contract.get('supports_diff_replication', False)),
            'supports_concurrent_snapshots': bool(environment_contract.get('supports_concurrent_snapshots', False)),
            'revision': int(environment_payload.get('revision', 0) or 0),
        },
        'collision': {
            'collision_backend': str(scene_payload.get('collision_backend', environment_payload.get('collision_backend', '')) or ''),
            'collision_level': str(scene_payload.get('collision_level', '') or ''),
            'precision': str(scene_payload.get('precision', '') or ''),
            'backend_family': str(scene_payload.get('backend_family', '') or ''),
            'supported_collision_levels': list(scene_payload.get('supported_collision_levels', ()) or []),
        },
        'plugins': {
            'policy': _coerce_mapping(plugin_payload.get('policy')),
            'catalog_counts': plugin_counts,
            'runtime_provider_count': int(plugin_counts.get('capability_total', 0) or 0),
            'runtime_provider_enabled_count': int(plugin_counts.get('capability_enabled', 0) or 0),
            'governance_registration_count': int(plugin_counts.get('total', 0) or 0),
        },
        'capability_matrix': {
            'version': 'v1',
            'solver_count': len(tuple(capability_payload.get('solvers', ()) or ())),
            'planner_count': len(tuple(capability_payload.get('planners', ()) or ())),
            'importer_count': len(tuple(capability_payload.get('importers', ()) or ())),
        },
    }
