from __future__ import annotations

from robot_sim.app.container import build_container


def test_container_reuses_one_shared_ik_use_case(project_root):
    container = build_container(project_root)

    assert container.ik_uc is container.benchmark_uc._service._ik_uc
    assert container.planner_registry.get('cartesian_sampled')._uc._ik_uc is container.ik_uc
    assert container.planner_registry.get('waypoint_graph')._planner._cartesian_planner._ik_uc is container.ik_uc
