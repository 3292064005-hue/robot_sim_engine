from __future__ import annotations

from robot_sim.app.container import build_container
from robot_sim.presentation.main_controller import MainController


def test_main_controller_exposes_full_capability_matrix(project_root):
    container = build_container(project_root)
    controller = MainController(project_root, container=container)
    descriptors = {descriptor.key: descriptor for descriptor in controller.capability_descriptors()}
    matrix_sections = descriptors['capability_matrix'].metadata['sections']

    assert 'scene_features' in matrix_sections
    assert 'collision_features' in matrix_sections
    assert 'render_features' in matrix_sections
    assert 'export_features' in matrix_sections
    assert 'plugin_features' in matrix_sections
    assert controller.state.capability_matrix == matrix_sections
