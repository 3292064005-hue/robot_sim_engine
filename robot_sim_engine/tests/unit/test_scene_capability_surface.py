from __future__ import annotations

from robot_sim.app.container import build_container


def test_scene_capabilities_expose_stable_toolbar_surface_and_editor_contract(project_root):
    container = build_container(project_root)
    matrix = container.capability_matrix_service.build_matrix(
        solver_registry=container.solver_registry,
        planner_registry=container.planner_registry,
        importer_registry=container.importer_registry,
    )
    scene = {descriptor.key: descriptor for descriptor in matrix.scene_features}

    assert scene['planning_scene'].status.value == 'stable'
    assert scene['planning_scene'].metadata['ui_surface'] == 'stable_scene_toolbar'
    assert scene['planning_scene'].metadata['edit_surface'] == 'stable_scene_editor'
    assert scene['planning_scene'].metadata['declared_backends'] == ['aabb', 'capsule']
    assert scene['planning_scene'].metadata['active_backends'] == ['aabb']
    assert scene['collision_backend_aabb'].status.value == 'internal'
