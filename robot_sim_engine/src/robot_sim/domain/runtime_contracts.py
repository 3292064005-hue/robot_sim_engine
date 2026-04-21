from __future__ import annotations

from collections.abc import Mapping

from robot_sim.domain.capabilities import CapabilityDescriptor, CapabilityMatrix
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.collision_fidelity import validation_backend_capability_matrix
from robot_sim.domain.enums import ModuleStatus
from robot_sim.domain.module_governance import governance_for_module


MODULE_STATUSES: dict[str, object] = {
    'core.collision.scene': ModuleStatus.STABLE.value,
    'render.picking': ModuleStatus.EXPERIMENTAL.value,
    'render.plot_sync': ModuleStatus.EXPERIMENTAL.value,
    'presentation.experimental.widgets.collision_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.experimental.widgets.export_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.experimental.widgets.scene_options_panel': ModuleStatus.EXPERIMENTAL.value,
    'render.experimental.picking': ModuleStatus.EXPERIMENTAL.value,
    'render.experimental.plot_sync': ModuleStatus.EXPERIMENTAL.value,
    'application.importers.urdf_model_importer': ModuleStatus.STABLE.value,
    'application.importers.urdf_skeleton_importer': ModuleStatus.STABLE.value,
    'core.collision.capsule_backend': ModuleStatus.STABLE.value,
}

_collision_registry = default_collision_backend_registry()
SCENE_CAPABILITIES: tuple[CapabilityDescriptor, ...] = (
    CapabilityDescriptor(
        'planning_scene',
        'Planning scene',
        owner_module='collision.scene',
        status=ModuleStatus.STABLE,
        metadata={
            'ui_surface': 'stable_scene_toolbar',
            'integration_scope': 'validation_export_session_scene_toolbar',
            'edit_surface': 'stable_scene_editor',
            'stable_surface_version': 'v3',
            'scene_geometry_contract': 'declaration_validation_render',
            'scene_geometry_contract_version': 'v1',
            'scene_validation_capability_matrix_version': 'v1',
            'supported_scene_shapes': ['box', 'cylinder', 'sphere'],
            'declared_backends': list(_collision_registry.declared_backend_ids()),
            'active_backends': list(_collision_registry.active_backend_ids(experimental_enabled=False)),
            'fallback_backend': _collision_registry.default_backend,
            'experimental_backends': [
                descriptor.backend_id for descriptor in _collision_registry.descriptors() if descriptor.is_experimental
            ],
            'validation_backend_capabilities': validation_backend_capability_matrix(experimental_enabled=False),
        },
    ),
    *_collision_registry.scene_capabilities(experimental_enabled=False),
)


def render_module_status_markdown(module_statuses: Mapping[str, object] | None = None) -> str:
    """Render deterministic module-status markdown from the shared runtime contract.

    Args:
        module_statuses: Optional mapping override. Values may be plain status strings
            or detail mappings containing ``status`` and ``enabled``.

    Returns:
        str: Deterministic markdown used by docs and regression checks.

    Raises:
        None: Rendering is a pure formatting operation.
    """
    normalized: dict[str, dict[str, object]] = {}
    source = dict(module_statuses or MODULE_STATUSES)
    for module_id, payload in source.items():
        if isinstance(payload, Mapping):
            status = str(payload.get('status', 'unknown'))
            enabled = bool(payload.get('enabled', True))
            availability = str(payload.get('availability', '') or '')
            entry_notes = tuple(str(item) for item in payload.get('notes', ()) or ())
        else:
            status = str(payload)
            enabled = True
            availability = ''
            entry_notes = ()
        governance = governance_for_module(str(module_id))
        normalized[str(module_id)] = {
            'status': status,
            'enabled': enabled,
            'availability': availability,
            'entry_notes': entry_notes,
            'governance': None if governance is None else governance.summary(),
        }

    grouped: dict[str, list[tuple[str, bool]]] = {}
    for module_id, detail in normalized.items():
        grouped.setdefault(str(detail['status']), []).append((module_id, bool(detail['enabled'])))

    lines = ['# Module Status', '']
    for status in sorted(grouped):
        lines.append(f'## {status}')
        for module_id, enabled in sorted(grouped[status], key=lambda item: item[0]):
            detail = normalized[module_id]
            availability = str(detail.get('availability', '') or '')
            state_label = availability if availability else ('enabled' if enabled else 'disabled_by_profile')
            lines.append(f"- `{module_id}` ({state_label})")
            governance = detail.get('governance') if isinstance(detail, Mapping) else None
            if status == ModuleStatus.EXPERIMENTAL.value and isinstance(governance, Mapping):
                owner = str(governance.get('owner', '') or '')
                if owner:
                    lines.append(f"  - owner: `{owner}`")
                stable_ui_surface = str(governance.get('stable_ui_surface', '') or '')
                if stable_ui_surface:
                    lines.append(f"  - stable_ui_surface: `{stable_ui_surface}`")
                exit_criteria = tuple(str(item) for item in governance.get('exit_criteria', ()) or ())
                if exit_criteria:
                    lines.append(f"  - exit_criteria: `{list(exit_criteria)}`")
                required_quality_gates = tuple(str(item) for item in governance.get('required_quality_gates', ()) or ())
                if required_quality_gates:
                    lines.append(f"  - required_quality_gates: `{list(required_quality_gates)}`")
                promotion_blockers = tuple(str(item) for item in governance.get('promotion_blockers', ()) or ())
                if promotion_blockers:
                    lines.append(f"  - promotion_blockers: `{list(promotion_blockers)}`")
                missing_quality_gates = tuple(str(item) for item in governance.get('missing_quality_gates', ()) or ())
                if missing_quality_gates:
                    lines.append(f"  - missing_quality_gates: `{list(missing_quality_gates)}`")
                failed_quality_gates = tuple(str(item) for item in governance.get('failed_quality_gates', ()) or ())
                if failed_quality_gates:
                    lines.append(f"  - failed_quality_gates: `{list(failed_quality_gates)}`")
                lines.append(f"  - promotion_ready: `{bool(governance.get('promotion_ready', False))}`")
                notes = list(tuple(str(item) for item in governance.get('notes', ()) or ()))
                notes.extend(str(item) for item in detail.get('entry_notes', ()) or ())
                if notes:
                    lines.append(f"  - notes: `{list(dict.fromkeys(notes))}`")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'



def render_capability_matrix_markdown(descriptors: object | None = None) -> str:
    """Render deterministic capability-matrix markdown from the shared runtime contract.

    Args:
        descriptors: Either a full ``CapabilityMatrix`` instance or an explicit mapping
            containing capability sections.

    Returns:
        str: Deterministic markdown used by docs and regression checks.
    """
    if descriptors is None:
        sections = {'scene_features': [item for item in SCENE_CAPABILITIES]}
    elif isinstance(descriptors, CapabilityMatrix):
        sections = descriptors.as_dict()
    elif isinstance(descriptors, Mapping):
        sections = dict(descriptors)
    else:
        raise TypeError(f'unsupported capability-matrix payload: {type(descriptors)!r}')

    ordered_sections = (
        'solvers',
        'planners',
        'importers',
        'render_features',
        'export_features',
        'scene_features',
        'collision_features',
        'plugin_features',
    )
    lines = ['# Capability Matrix', '']
    for section_name in ordered_sections:
        section_items = list(sections.get(section_name, []) or [])
        if not section_items:
            continue
        lines.append(f'## {section_name}')
        for item in section_items:
            key = str(item.get('key', ''))
            status = str(item.get('status', 'unknown'))
            owner_module = str(item.get('owner_module', ''))
            lines.append(f'- `{key}` [{status}]')
            lines.append(f'  - owner: `{owner_module}`')
            lines.append(f'  - enabled: `{bool(item.get("enabled", True))}`')
            metadata = dict(item.get('metadata', {}) or {})
            for meta_key in sorted(metadata):
                lines.append(f'  - {meta_key}: `{metadata[meta_key]}`')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'
