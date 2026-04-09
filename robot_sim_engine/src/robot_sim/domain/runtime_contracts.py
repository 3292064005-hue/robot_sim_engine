from __future__ import annotations

from collections.abc import Mapping

from robot_sim.domain.capabilities import CapabilityDescriptor
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import ModuleStatus
from robot_sim.domain.module_governance import governance_for_module


MODULE_STATUSES: dict[str, str] = {
    'core.collision.scene': ModuleStatus.STABLE.value,
    'presentation.widgets.collision_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.widgets.export_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.widgets.scene_options_panel': ModuleStatus.EXPERIMENTAL.value,
    'render.picking': ModuleStatus.EXPERIMENTAL.value,
    'render.plot_sync': ModuleStatus.EXPERIMENTAL.value,
    'presentation.experimental.widgets.collision_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.experimental.widgets.export_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.experimental.widgets.scene_options_panel': ModuleStatus.EXPERIMENTAL.value,
    'render.experimental.picking': ModuleStatus.EXPERIMENTAL.value,
    'render.experimental.plot_sync': ModuleStatus.EXPERIMENTAL.value,
    'application.importers.urdf_model_importer': ModuleStatus.STABLE.value,
    'application.importers.urdf_skeleton_importer': ModuleStatus.STABLE.value,
    'core.collision.capsule_backend': ModuleStatus.EXPERIMENTAL.value,
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
            'stable_surface_version': 'v2',
            'supported_scene_shapes': ['box', 'cylinder', 'sphere'],
            'declared_backends': list(_collision_registry.declared_backend_ids()),
            'active_backends': list(_collision_registry.active_backend_ids(experimental_enabled=False)),
            'fallback_backend': _collision_registry.default_backend,
            'experimental_backends': [
                descriptor.backend_id for descriptor in _collision_registry.descriptors() if descriptor.is_experimental
            ],
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
        else:
            status = str(payload)
            enabled = True
        governance = governance_for_module(str(module_id))
        normalized[str(module_id)] = {
            'status': status,
            'enabled': enabled,
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
            lines.append(f"- `{module_id}` ({'enabled' if enabled else 'disabled_by_profile'})")
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
                notes = tuple(str(item) for item in governance.get('notes', ()) or ())
                if notes:
                    lines.append(f"  - notes: `{list(notes)}`")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'



def render_capability_matrix_markdown(descriptors: tuple[CapabilityDescriptor, ...] | None = None) -> str:
    """Render deterministic scene-capability markdown from the shared runtime contract."""
    lines = ['# Capability Matrix', '', '## scene_features']
    for descriptor in descriptors or SCENE_CAPABILITIES:
        lines.append(f'- `{descriptor.key}` [{descriptor.status.value}]')
        lines.append(f'  - owner: `{descriptor.owner_module}`')
        if descriptor.metadata:
            for key in sorted(descriptor.metadata):
                lines.append(f'  - {key}: `{descriptor.metadata[key]}`')
    lines.append('')
    return '\n'.join(lines)
