from __future__ import annotations

from types import SimpleNamespace

from robot_sim.application.services.collision_backend_runtime import (
    AABBCollisionBackendRuntime,
    install_collision_backend_runtime_plugins,
    resolve_collision_backend_runtime,
)
from robot_sim.application.services.scene_backend_runtime import (
    PlanningSceneBackendRuntime,
    install_scene_backend_runtime_plugins,
    resolve_scene_backend_runtime,
)


class _CollisionPlugin(AABBCollisionBackendRuntime):
    def __init__(self) -> None:
        object.__setattr__(self, 'backend_id', 'custom_aabb')
        object.__setattr__(self, 'display_name', 'Custom AABB')
        object.__setattr__(self, 'plugin_surface', 'collision_backend')
        object.__setattr__(self, 'backend_contract_version', 'v1')
        object.__setattr__(self, 'validation_fidelity', 'approximate_aabb')


class _ScenePlugin(PlanningSceneBackendRuntime):
    def __init__(self) -> None:
        object.__setattr__(self, 'backend_id', 'custom_scene')
        object.__setattr__(self, 'display_name', 'Custom Scene Backend')
        object.__setattr__(self, 'plugin_surface', 'scene_backend')
        object.__setattr__(self, 'scene_geometry_contract_version', 'v1')
        object.__setattr__(self, 'scene_validation_capability_matrix_version', 'v1')



def test_runtime_plugin_installation_registers_scene_and_collision_backends() -> None:
    collision_registration = SimpleNamespace(plugin_id='custom_collision_plugin', instance=_CollisionPlugin())
    scene_registration = SimpleNamespace(plugin_id='custom_scene_plugin', instance=_ScenePlugin())

    install_collision_backend_runtime_plugins((collision_registration,))
    install_scene_backend_runtime_plugins((scene_registration,))

    assert resolve_collision_backend_runtime('custom_aabb').backend_id == 'custom_aabb'
    assert resolve_scene_backend_runtime('custom_scene').backend_id == 'custom_scene'
    