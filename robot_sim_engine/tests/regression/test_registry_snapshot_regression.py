from robot_sim.app.container import build_container


def test_container_registry_snapshot_contains_canonical_ids(tmp_path):
    container = build_container(tmp_path)
    assert set(container.solver_registry.ids()) == {'pinv', 'dls', 'lm', 'analytic_6r'}
    assert set(container.planner_registry.ids()) == {'joint_trapezoidal', 'joint_quintic', 'cartesian_sampled', 'waypoint_graph'}
    assert set(container.importer_registry.ids()) == {'yaml', 'urdf_model', 'urdf_skeleton'}
    assert container.solver_registry.resolve_id('shipped_lm_solver') == 'lm'
    assert container.planner_registry.resolve_id('shipped_joint_space_planner') == 'joint_trapezoidal'
    assert container.importer_registry.resolve_id('shipped_yaml_importer') == 'yaml'
