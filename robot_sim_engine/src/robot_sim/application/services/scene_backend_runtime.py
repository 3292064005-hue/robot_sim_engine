from __future__ import annotations

from collections.abc import Mapping

from robot_sim.application.services.collision_backend_runtime import resolve_collision_backend_runtime
from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.scene import PlanningScene, SceneObject
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.model.scene_geometry_authority import SceneGeometryAuthority
from robot_sim.model.scene_graph_authority import SceneGraphAuthority
from robot_sim.model.scene_geometry_projection import normalize_declaration_geometry


class PlanningSceneBackendRuntime:
    """Executable planning-scene backend used by the stable scene runtime and plugin surface."""

    backend_id = 'planning_scene_backend'

    def capabilities(self) -> dict[str, object]:
        return {
            'display_name': 'Planning-scene backend',
            'plugin_surface': 'scene_backend',
            'scene_geometry_contract_version': 'v1',
            'scene_validation_capability_matrix_version': 'v1',
            'supported_operations': ['bootstrap_scene', 'build_scene_object', 'refresh_scene_authority'],
        }

    def bootstrap_scene(
        self,
        *,
        scene_summary: Mapping[str, object] | None,
        authority: str,
        edit_surface: str,
    ) -> PlanningScene:
        summary = dict(scene_summary or {})
        normalized_backend, normalized_metadata = default_collision_backend_registry().normalize_backend(
            str(summary.get('collision_backend', 'aabb') or 'aabb'),
            metadata={
                'scene_authority': str(authority),
                'edit_surface': str(edit_surface),
                'scene_fidelity': str(summary.get('scene_fidelity', summary.get('geometry_source', 'generated')) or 'generated'),
                'stable_surface_version': str(summary.get('stable_surface_version', 'v3') or 'v3'),
                'scene_geometry_contract_version': 'v1',
                'scene_validation_capability_matrix_version': 'v1',
                'scene_backend_runtime': self.backend_id,
                'declaration_geometry_source': str(summary.get('declaration_geometry_source', summary.get('geometry_source', 'generated')) or summary.get('geometry_source', 'generated')),
                'validation_geometry_source': str(summary.get('validation_geometry_source', f"{summary.get('collision_backend', 'aabb')}_planning_scene") or f"{summary.get('collision_backend', 'aabb')}_planning_scene"),
                'render_geometry_source': str(summary.get('render_geometry_source', summary.get('geometry_source', 'generated')) or summary.get('geometry_source', 'generated')),
                'scene_geometry_contract': 'declaration_validation_render',
            },
        )
        acm = AllowedCollisionMatrix()
        for pair in summary.get('allowed_collision_pairs', ()) or ():
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                acm = acm.allow(str(pair[0]), str(pair[1]))
        scene = PlanningScene(
            revision=int(summary.get('revision', 0) or 0),
            collision_backend=normalized_backend,
            geometry_source=str(summary.get('geometry_source', 'generated') or 'generated'),
            allowed_collision_matrix=acm,
            metadata=normalized_metadata,
        )
        authority_model = SceneGeometryAuthority.from_summary(
            summary,
            authority=str((summary.get('geometry_authority') or {}).get('authority', authority) if isinstance(summary.get('geometry_authority'), Mapping) else authority),
            authority_kind=str((summary.get('geometry_authority') or {}).get('authority_kind', 'planning_scene') if isinstance(summary.get('geometry_authority'), Mapping) else 'planning_scene'),
            declaration_geometry_source=str(summary.get('declaration_geometry_source', summary.get('geometry_source', 'generated')) or summary.get('geometry_source', 'generated')),
            validation_geometry_source=str(summary.get('validation_geometry_source', f"{summary.get('collision_backend', 'aabb')}_planning_scene") or f"{summary.get('collision_backend', 'aabb')}_planning_scene"),
            render_geometry_source=str(summary.get('render_geometry_source', summary.get('geometry_source', 'generated')) or summary.get('geometry_source', 'generated')),
            supported_scene_shapes=('box', 'cylinder', 'sphere'),
            collision_backend=normalized_backend,
            scene_fidelity=str(summary.get('scene_fidelity', summary.get('geometry_source', 'generated')) or 'generated'),
        )
        seeded = scene.with_geometry_authority(authority_model)
        return seeded.with_scene_graph_authority(SceneGraphAuthority.from_scene(seeded, previous=seeded.scene_graph_authority))

    def build_scene_object(
        self,
        *,
        object_id: str,
        declaration_geometry: Mapping[str, object],
        metadata: Mapping[str, object] | None,
        collision_backend: str,
        attached: bool,
    ) -> SceneObject:
        normalized_declaration = normalize_declaration_geometry(declaration_geometry)
        runtime = resolve_collision_backend_runtime(collision_backend)
        projection = runtime.project_declaration_geometry(normalized_declaration, attached=attached)
        merged_metadata = {
            **dict(metadata or {}),
            'declaration_geometry': dict(projection.declaration_geometry),
            'validation_geometry': dict(projection.validation_geometry),
            'render_geometry': dict(projection.render_geometry),
            'validation_query_geometry': projection.summary()['query_geometry'],
            'validation_backend': str(projection.validation_backend),
            'validation_adapter_kind': str(projection.adapter_kind),
            'declaration_geometry_source': str(dict(metadata or {}).get('declaration_geometry_source', 'stable_scene_editor') or 'stable_scene_editor'),
            'validation_geometry_source': str(projection.validation_geometry_source),
            'render_geometry_source': str(dict(metadata or {}).get('render_geometry_source', 'stable_scene_editor') or 'stable_scene_editor'),
            'scene_backend_runtime': self.backend_id,
            'collision_backend_runtime': str(runtime.backend_id),
            'collision_backend_runtime_label': str(runtime.display_name),
                    }
        return SceneObject(object_id=str(object_id), geometry=projection.query_aabb, metadata=merged_metadata)

    def refresh_scene_authority(self, scene: PlanningScene) -> PlanningScene:
        refreshed = SceneGeometryAuthority.from_scene(scene)
        scene = scene.with_metadata_patch(**refreshed.metadata_patch())
        scene = scene.with_geometry_authority(refreshed)
        return scene.with_scene_graph_authority(SceneGraphAuthority.from_scene(scene, previous=scene.scene_graph_authority))


_REGISTERED_SCENE_BACKEND_RUNTIMES: dict[str, PlanningSceneBackendRuntime] = {
    'planning_scene_backend': PlanningSceneBackendRuntime(),
}

def register_scene_backend_runtime(
    runtime: PlanningSceneBackendRuntime,
    *,
    plugin_id: str | None = None
) -> PlanningSceneBackendRuntime:
    runtime_id = str(getattr(runtime, 'backend_id', '') or 'planning_scene_backend').strip().lower() or 'planning_scene_backend'
    _REGISTERED_SCENE_BACKEND_RUNTIMES[runtime_id] = runtime
    return runtime


def install_scene_backend_runtime_plugins(registrations: tuple[object, ...]) -> tuple[str, ...]:
    installed: list[str] = []
    for registration in tuple(registrations or ()):
        instance = getattr(registration, 'instance', None)
        if not isinstance(instance, PlanningSceneBackendRuntime):
            continue
        register_scene_backend_runtime(
            instance,
            plugin_id=str(getattr(registration, 'plugin_id', '') or ''),
        )
        installed.append(str(getattr(registration, 'plugin_id', instance.backend_id) or instance.backend_id))
    return tuple(installed)


def resolve_scene_backend_runtime(backend_id: str = 'planning_scene_backend') -> PlanningSceneBackendRuntime:
    normalized = str(backend_id or 'planning_scene_backend').strip().lower() or 'planning_scene_backend'
    return _REGISTERED_SCENE_BACKEND_RUNTIMES.get(normalized, _REGISTERED_SCENE_BACKEND_RUNTIMES['planning_scene_backend'])


def default_scene_backend_runtime() -> PlanningSceneBackendRuntime:
    return resolve_scene_backend_runtime('planning_scene_backend')


__all__ = [
    'PlanningSceneBackendRuntime',
    'default_scene_backend_runtime',
    'install_scene_backend_runtime_plugins',
    'register_scene_backend_runtime',
    'resolve_scene_backend_runtime',
]
