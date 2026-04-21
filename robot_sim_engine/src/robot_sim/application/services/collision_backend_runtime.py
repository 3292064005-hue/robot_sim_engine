from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from robot_sim.core.collision.geometry import AABB
from robot_sim.model.scene_geometry_projection import SceneGeometryProjection, project_declaration_geometry, serialize_aabb


@dataclass(frozen=True)
class CollisionBackendRuntime:
    """Executable collision-backend runtime surface shared by plugins and services."""

    backend_id: str
    display_name: str
    plugin_surface: str = 'collision_backend'
    backend_contract_version: str = 'v1'
    validation_fidelity: str = 'approximate_aabb'

    def capabilities(self) -> dict[str, object]:
        return {
            'display_name': self.display_name,
            'plugin_surface': self.plugin_surface,
            'backend_contract_version': self.backend_contract_version,
            'validation_fidelity': self.validation_fidelity,
            'supported_operations': ['project_geometry', 'project_query_aabb', 'project_scene_object'],
        }

    def project_declaration_geometry(
        self,
        declaration_geometry: Mapping[str, object] | None,
        *,
        attached: bool = False,
        fallback_geometry: AABB | None = None,
    ) -> SceneGeometryProjection:
        return project_declaration_geometry(
            declaration_geometry,
            backend_id=self.backend_id,
            attached=attached,
            fallback_geometry=fallback_geometry,
        )

    def project_query_aabb(
        self,
        declaration_geometry: Mapping[str, object] | None,
        *,
        attached: bool = False,
        fallback_geometry: AABB | None = None,
    ) -> AABB:
        return self.project_declaration_geometry(
            declaration_geometry,
            attached=attached,
            fallback_geometry=fallback_geometry,
        ).query_aabb

    def project_scene_object(self, obj: object, *, attached: bool = False) -> dict[str, object]:
        projection = self.project_declaration_geometry(
            getattr(obj, 'metadata', {}).get('declaration_geometry')
            if isinstance(getattr(obj, 'metadata', None), Mapping)
            else None,
            attached=attached,
            fallback_geometry=getattr(obj, 'geometry', None),
        )
        payload = projection.summary()
        payload['query_geometry'] = serialize_aabb(projection.query_aabb)
        return payload


class AABBCollisionBackendRuntime(CollisionBackendRuntime):
    def __init__(self) -> None:
        super().__init__(
            backend_id='aabb',
            display_name='AABB collision backend',
            validation_fidelity='approximate_aabb',
        )


class CapsuleCollisionBackendRuntime(CollisionBackendRuntime):
    def __init__(self) -> None:
        super().__init__(
            backend_id='capsule',
            display_name='Capsule collision backend',
            validation_fidelity='primitive_passthrough_with_aabb_queries',
        )


_BUILTIN_COLLISION_BACKEND_RUNTIMES: dict[str, CollisionBackendRuntime] = {
    'aabb': AABBCollisionBackendRuntime(),
    'capsule': CapsuleCollisionBackendRuntime(),
}
_REGISTERED_COLLISION_BACKEND_RUNTIMES: dict[str, CollisionBackendRuntime] = dict(_BUILTIN_COLLISION_BACKEND_RUNTIMES)

def register_collision_backend_runtime(
    runtime: CollisionBackendRuntime,
    *,
    plugin_id: str | None = None
) -> CollisionBackendRuntime:
    """Register a collision-backend runtime exposed by a shipped or external plugin."""
    runtime_id = str(getattr(runtime, 'backend_id', '') or '').strip().lower()
    if not runtime_id:
        raise ValueError('collision backend runtime must expose a non-empty backend_id')
    _REGISTERED_COLLISION_BACKEND_RUNTIMES[runtime_id] = runtime
    return runtime


def install_collision_backend_runtime_plugins(registrations: tuple[object, ...]) -> tuple[str, ...]:
    """Install collision-backend runtime plugins into the executable runtime registry."""
    installed: list[str] = []
    for registration in tuple(registrations or ()):
        instance = getattr(registration, 'instance', None)
        if not isinstance(instance, CollisionBackendRuntime):
            continue
        register_collision_backend_runtime(
            instance,
            plugin_id=str(getattr(registration, 'plugin_id', '') or ''),
        )
        installed.append(str(getattr(registration, 'plugin_id', instance.backend_id) or instance.backend_id))
    return tuple(installed)


def default_collision_backend_runtime_registry() -> dict[str, CollisionBackendRuntime]:
    return dict(_REGISTERED_COLLISION_BACKEND_RUNTIMES)


def resolve_collision_backend_runtime(backend_id: str) -> CollisionBackendRuntime:
    normalized = str(backend_id or 'aabb').strip().lower() or 'aabb'
    return _REGISTERED_COLLISION_BACKEND_RUNTIMES.get(normalized, _BUILTIN_COLLISION_BACKEND_RUNTIMES['aabb'])


__all__ = [
    'AABBCollisionBackendRuntime',
    'CapsuleCollisionBackendRuntime',
    'CollisionBackendRuntime',
    'default_collision_backend_runtime_registry',
    'install_collision_backend_runtime_plugins',
    'register_collision_backend_runtime',
    'resolve_collision_backend_runtime',
]
