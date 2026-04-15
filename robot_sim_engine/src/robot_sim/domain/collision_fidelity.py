from __future__ import annotations

from dataclasses import dataclass

from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import CollisionLevel


@dataclass(frozen=True)
class CollisionFidelityDescriptor:
    collision_level: str
    precision: str
    stable_surface: bool
    promotion_state: str
    summary: str


_COLLISION_FIDELITY_DESCRIPTORS: dict[str, CollisionFidelityDescriptor] = {
    CollisionLevel.NONE.value: CollisionFidelityDescriptor(CollisionLevel.NONE.value, 'none', False, 'disabled', 'collision checking disabled'),
    CollisionLevel.AABB.value: CollisionFidelityDescriptor(CollisionLevel.AABB.value, 'broad_phase', True, 'stable', 'AABB broad-phase validation'),
    CollisionLevel.CAPSULE.value: CollisionFidelityDescriptor(CollisionLevel.CAPSULE.value, 'capsule_narrow_phase', False, 'profile_gated', 'capsule narrow-phase validation'),
    CollisionLevel.MESH.value: CollisionFidelityDescriptor(CollisionLevel.MESH.value, 'mesh_exact', False, 'not_implemented', 'mesh-level validation'),
}


def collision_fidelity_descriptor(collision_level: str | CollisionLevel | None) -> CollisionFidelityDescriptor:
    normalized = getattr(collision_level, 'value', collision_level)
    normalized = str(normalized or CollisionLevel.NONE.value).strip().lower() or CollisionLevel.NONE.value
    return _COLLISION_FIDELITY_DESCRIPTORS.get(normalized, _COLLISION_FIDELITY_DESCRIPTORS[CollisionLevel.NONE.value])


def summarize_collision_fidelity(*, collision_level: str | CollisionLevel | None, collision_backend: str, scene_fidelity: str, experimental_backends_enabled: bool | None = None) -> dict[str, object]:
    descriptor = collision_fidelity_descriptor(collision_level)
    registry = default_collision_backend_registry()
    backend_id = str(collision_backend or registry.default_backend).strip().lower() or registry.default_backend
    backend_descriptor = next((item for item in registry.descriptors() if item.backend_id == backend_id), None)
    experimental_enabled = bool(experimental_backends_enabled) if experimental_backends_enabled is not None else True
    availability = 'unknown'
    backend_status = 'unknown'
    backend_family = ''
    supported_levels: list[str] = []
    if backend_descriptor is not None:
        availability = backend_descriptor.availability(experimental_enabled=experimental_enabled)
        backend_status = backend_descriptor.status.value
        backend_family = str(backend_descriptor.metadata.get('family', '') or '')
        supported_levels = [str(item) for item in backend_descriptor.metadata.get('supported_collision_levels', ())]
    return {
        'collision_level': descriptor.collision_level,
        'collision_backend': backend_id,
        'precision': descriptor.precision,
        'stable_surface': descriptor.stable_surface,
        'promotion_state': descriptor.promotion_state,
        'summary': descriptor.summary,
        'backend_status': backend_status,
        'backend_availability': availability,
        'backend_family': backend_family,
        'supported_collision_levels': supported_levels,
        'scene_fidelity': str(scene_fidelity or ''),
    }



def validation_backend_capability_matrix(*, experimental_enabled: bool) -> list[dict[str, object]]:
    """Return the versioned validation-backend capability matrix for scene diagnostics.

    Args:
        experimental_enabled: Whether experimental collision backends are currently active.

    Returns:
        list[dict[str, object]]: Deterministic capability rows ordered by backend identifier.

    Raises:
        None: The matrix is derived from the in-process backend registry.
    """
    registry = default_collision_backend_registry()
    rows: list[dict[str, object]] = []
    for descriptor in registry.descriptors():
        supported_levels = tuple(str(item) for item in descriptor.metadata.get('supported_collision_levels', ()) or ())
        fidelity_rows = [
            summarize_collision_fidelity(
                collision_level=level,
                collision_backend=descriptor.backend_id,
                scene_fidelity='planning_scene',
                experimental_backends_enabled=experimental_enabled,
            )
            for level in supported_levels
        ]
        rows.append({
            'backend_id': descriptor.backend_id,
            'family': str(descriptor.metadata.get('family', '') or ''),
            'status': descriptor.status.value,
            'availability': descriptor.availability(experimental_enabled=experimental_enabled),
            'is_default': bool(descriptor.backend_id == registry.default_backend),
            'is_experimental': bool(descriptor.is_experimental),
            'supported_collision_levels': list(supported_levels),
            'fidelity_rows': fidelity_rows,
        })
    rows.sort(key=lambda item: (0 if item['is_default'] else 1, str(item['backend_id'])))
    return rows
