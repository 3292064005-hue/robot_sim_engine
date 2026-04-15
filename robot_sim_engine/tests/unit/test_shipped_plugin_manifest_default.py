from __future__ import annotations

from robot_sim.app.container import build_container


def test_default_container_registers_shipped_stable_plugins(project_root):
    container = build_container(project_root)

    assert 'stable_demo_lm' in container.solver_registry.ids()
    assert 'stable_demo_joint_planner' in container.planner_registry.ids()
    assert 'stable_demo_yaml_importer' in container.importer_registry.ids()
    matrix = container.capability_matrix_service.build_matrix(
        solver_registry=container.solver_registry,
        planner_registry=container.planner_registry,
        importer_registry=container.importer_registry,
    ).as_dict()
    plugin_ids = {item['metadata'].get('plugin_id') for item in matrix['plugin_features'] if item['key'].startswith('plugin_')}
    assert 'stable_demo_scene_backend_contract' in plugin_ids
    assert 'stable_demo_collision_backend_contract' in plugin_ids
