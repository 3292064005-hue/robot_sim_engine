from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / 'src' / 'robot_sim'


def test_domain_layer_does_not_import_application_or_infra_layers():
    for path in (SRC_ROOT / 'domain').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'robot_sim.application' not in text, f'domain->application import leak: {path.relative_to(PROJECT_ROOT)}'
        assert 'robot_sim.infra' not in text, f'domain->infra import leak: {path.relative_to(PROJECT_ROOT)}'


def test_application_layer_does_not_import_app_layer():
    for path in (SRC_ROOT / 'application').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'robot_sim.app.' not in text, f'application import leak: {path.relative_to(PROJECT_ROOT)}'


def test_model_layer_does_not_import_application_or_infra_layers():
    for path in (SRC_ROOT / 'model').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'robot_sim.application' not in text, f'model->application import leak: {path.relative_to(PROJECT_ROOT)}'
        assert 'robot_sim.infra' not in text, f'model->infra import leak: {path.relative_to(PROJECT_ROOT)}'


def test_stable_main_window_ui_does_not_mount_experimental_widgets():
    path = SRC_ROOT / 'presentation' / 'main_window_ui.py'
    text = path.read_text(encoding='utf-8')
    for marker in ('collision_panel', 'export_panel', 'scene_options_panel'):
        assert marker not in text


def test_main_window_builds_through_presentation_assembly():
    text = (SRC_ROOT / 'presentation' / 'main_window.py').read_text(encoding='utf-8')
    assert 'build_presentation_assembly(' in text
    assert 'MainController(' not in text
    assert 'ThreadOrchestrator(' not in text


def test_main_window_uses_grouped_runtime_bundles_instead_of_installing_peer_aliases():
    text = (SRC_ROOT / 'presentation' / 'main_window.py').read_text(encoding='utf-8')
    assert 'runtime_services' in text
    assert 'workflow_services' in text
    assert 'task_orchestration' in text
    assert '_install_window_runtime_aliases' not in text


def test_main_window_ui_consumes_workflow_services_as_primary_surface():
    text = (SRC_ROOT / 'presentation' / 'main_window_ui.py').read_text(encoding='utf-8')
    assert "getattr(self, 'robot_workflow', None)" in text
    assert "getattr(self, 'motion_workflow', None)" in text
    assert "getattr(self, 'export_workflow', None)" in text
    assert "getattr(self, 'robot_facade', None)" not in text
    assert "getattr(self, 'solver_facade', None)" not in text
    assert "getattr(self, 'trajectory_facade', None)" not in text
    assert "getattr(self, 'playback_facade', None)" not in text
    assert "getattr(self, 'benchmark_facade', None)" not in text
    assert "getattr(self, 'export_facade', None)" not in text


def test_presentation_assembly_requires_explicit_workflow_services_without_facade_fallback():
    text = (SRC_ROOT / 'presentation' / 'assembly.py').read_text(encoding='utf-8')
    assert 'controller.robot_workflow' in text
    assert 'controller.motion_workflow' in text
    assert 'controller.export_workflow' in text
    assert "getattr(controller, 'robot_workflow'" not in text
    assert "getattr(controller, 'motion_workflow'" not in text
    assert "getattr(controller, 'export_workflow'" not in text


def test_main_controller_builds_collaborators_through_support_module():
    text = (SRC_ROOT / 'presentation' / 'main_controller.py').read_text(encoding='utf-8')
    assert 'build_presentation_collaborators' in text
    assert 'install_main_controller_collaborators' in text
    assert 'class _PresentationControllerCollaborators' not in text


def test_collision_validator_keeps_planning_scene_as_canonical_validation_surface():
    text = (SRC_ROOT / 'application' / 'validators' / 'collision_validator.py').read_text(encoding='utf-8')
    assert 'legacy_obstacle_adapter' in text
    assert 'collision_input' in text
