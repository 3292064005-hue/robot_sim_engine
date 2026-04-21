from __future__ import annotations

from robot_sim.app.container import build_container


def test_default_container_registers_shipped_stable_plugins_as_compatibility_aliases(project_root):
    container = build_container(project_root)

    assert 'shipped_lm_solver' not in container.solver_registry.ids()
    assert 'shipped_joint_space_planner' not in container.planner_registry.ids()
    assert 'shipped_yaml_importer' not in container.importer_registry.ids()
    assert container.solver_registry.resolve_id('shipped_lm_solver') == 'lm'
    assert container.planner_registry.resolve_id('shipped_joint_space_planner') == 'joint_trapezoidal'
    assert container.importer_registry.resolve_id('shipped_yaml_importer') == 'yaml'
    matrix = container.capability_matrix_service.build_matrix(
        solver_registry=container.solver_registry,
        planner_registry=container.planner_registry,
        importer_registry=container.importer_registry,
    ).as_dict()
    plugin_ids = {item['metadata'].get('plugin_id') for item in matrix['plugin_features'] if item['key'].startswith('plugin_')}
    assert 'planning_scene_backend' in plugin_ids
    assert 'aabb_collision_backend' in plugin_ids
