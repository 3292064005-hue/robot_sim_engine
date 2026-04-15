from __future__ import annotations

from typing import Mapping


def backend_validation_precision(backend_id: str) -> str:
    """Return the stable validation-precision label for a collision backend.

    Args:
        backend_id: Resolved collision backend identifier.

    Returns:
        str: Stable precision label projected into diagnostics, export, and UI summaries.

    Raises:
        None: Unknown backends degrade to an approximate label instead of failing.
    """
    normalized = str(backend_id or 'aabb').strip().lower() or 'aabb'
    if normalized == 'aabb':
        return 'approximate_aabb'
    if normalized == 'capsule':
        return 'approximate_capsule'
    return f'approximate_{normalized}'



def summarize_record_validation_surface(
    *,
    validation_geometry_source: str,
    validation_geometry: Mapping[str, object] | None,
    attached: bool,
) -> dict[str, object]:
    """Describe how one scene record participates in validation.

    Args:
        validation_geometry_source: Canonical validation geometry source label.
        validation_geometry: Validation geometry payload projected for the record.
        attached: Whether the record represents an attached object.

    Returns:
        dict[str, object]: Stable record-level validation capability summary.

    Raises:
        None: Missing payloads degrade to declaration-only semantics.
    """
    source = str(validation_geometry_source or '').strip().lower()
    geometry_kind = str(dict(validation_geometry or {}).get('kind', '') or '').strip().lower()
    participates = bool(source)
    if not participates:
        return {
            'validation_participation': 'declaration_only',
            'validation_precision': 'none',
            'capability_tier': 'editable_only',
            'attached': bool(attached),
        }
    precision = 'approximate'
    if geometry_kind == 'aabb' or 'aabb' in source:
        precision = 'approximate_aabb'
    elif 'capsule' in source:
        precision = 'approximate_capsule'
    return {
        'validation_participation': 'validation_effective',
        'validation_precision': precision,
        'capability_tier': 'editable_and_validation_effective',
        'attached': bool(attached),
    }



def summarize_scene_validation_surface(
    *,
    collision_backend: str,
    scene_fidelity: str,
    scene_authority: str,
    scene_geometry_contract: str,
    attached_object_count: int = 0,
    adapter_applied: bool = False,
    source: str = 'planning_scene',
) -> dict[str, object]:
    """Return the stable validation-surface summary for a planning scene.

    Args:
        collision_backend: Resolved collision backend identifier.
        scene_fidelity: Stable scene fidelity label.
        scene_authority: Stable scene authority label.
        scene_geometry_contract: Geometry authority contract label.
        attached_object_count: Number of attached objects in the scene.
        adapter_applied: Whether the scene originated from the legacy obstacle adapter.
        source: Canonical scene-source label.

    Returns:
        dict[str, object]: Stable validation-surface summary.

    Raises:
        None: Pure projection helper.
    """
    backend = str(collision_backend or 'aabb').strip().lower() or 'aabb'
    normalized_source = str(source or 'planning_scene').strip().lower() or 'planning_scene'
    normalized_authority = str(scene_authority or 'planning_scene').strip().lower() or 'planning_scene'
    normalized_geometry_contract = str(scene_geometry_contract or 'declaration_validation_render').strip().lower() or 'declaration_validation_render'
    normalized_fidelity = str(scene_fidelity or 'generated').strip().lower() or 'generated'
    validation_effective = (
        normalized_source != 'none'
        and normalized_authority != 'none'
        and normalized_fidelity != 'none'
    )
    precision = backend_validation_precision(backend) if validation_effective else 'none'
    mode = f'{backend}_planning_scene' if validation_effective else 'none'
    attached_validation = 'approximate' if validation_effective and int(attached_object_count) > 0 else 'none'
    return {
        'scene_source': normalized_source,
        'scene_validation_effective': bool(validation_effective),
        'scene_validation_mode': mode,
        'scene_validation_precision': precision,
        'scene_authority': normalized_authority,
        'scene_geometry_contract': normalized_geometry_contract if validation_effective else 'none',
        'scene_fidelity': normalized_fidelity,
        'attached_object_validation': attached_validation,
        'adapter_applied': bool(adapter_applied),
    }
