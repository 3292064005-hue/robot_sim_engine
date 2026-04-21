from __future__ import annotations

from robot_sim.app.container import build_container


def test_scene_capabilities_expose_stable_toolbar_surface_editor_contract_and_reserved_plugin_surfaces(project_root):
    container = build_container(project_root)
    matrix = container.capability_matrix_service.build_matrix(
        solver_registry=container.solver_registry,
        planner_registry=container.planner_registry,
        importer_registry=container.importer_registry,
    )
    scene = {descriptor.key: descriptor for descriptor in matrix.scene_features}
    collision = {descriptor.key: descriptor for descriptor in matrix.collision_features}

    assert scene['planning_scene'].status.value == 'stable'
    assert scene['planning_scene'].metadata['ui_surface'] == 'stable_scene_toolbar'
    assert scene['planning_scene'].metadata['edit_surface'] == 'stable_scene_editor'
    assert scene['planning_scene'].metadata['declared_backends'] == ['aabb', 'capsule']
    assert scene['planning_scene'].metadata['active_backends'] == ['aabb', 'capsule']
    assert scene['planning_scene'].metadata['stable_surface_version'] == 'v3'
    assert scene['planning_scene'].metadata['scene_geometry_contract_version'] == 'v1'
    assert scene['planning_scene'].metadata['scene_validation_capability_matrix_version'] == 'v1'
    assert scene['planning_scene'].metadata['validation_backend_capabilities'][0]['backend_id'] == 'aabb'
    assert scene['scene_backend_plugin_surface'].metadata['plugin_kind'] == 'scene_backend'
    assert scene['scene_backend_plugin_surface'].metadata['enabled_plugin_ids'] == ['planning_scene_backend']
    assert collision['collision_backend_plugin_surface'].metadata['plugin_kind'] == 'collision_backend'
    assert collision['collision_backend_plugin_surface'].metadata['enabled_plugin_ids'] == ['aabb_collision_backend']
    assert collision['collision_backend_aabb'].status.value == 'internal'
