from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / 'src' / 'robot_sim'


def test_core_waypoint_planner_does_not_import_application_layer():
    path = SRC_ROOT / 'core' / 'trajectory' / 'waypoint_planner.py'
    text = path.read_text(encoding='utf-8')
    assert 'robot_sim.application' not in text


def test_domain_layer_does_not_import_application_layer():
    for path in (SRC_ROOT / 'domain').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'robot_sim.application' not in text, f'domain import leak: {path.relative_to(PROJECT_ROOT)}'


def test_application_layer_does_not_import_app_layer():
    for path in (SRC_ROOT / 'application').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'robot_sim.app.' not in text, f'application import leak: {path.relative_to(PROJECT_ROOT)}'


def test_stable_main_window_ui_does_not_mount_experimental_widgets():
    path = SRC_ROOT / 'presentation' / 'main_window_ui.py'
    text = path.read_text(encoding='utf-8')
    for marker in ('collision_panel', 'export_panel', 'scene_options_panel'):
        assert marker not in text


def test_gui_boundary_catches_are_centralized_in_main_window_ui():
    allowed = {
        SRC_ROOT / 'presentation' / 'main_window_ui.py',
        SRC_ROOT / 'presentation' / 'coordinators' / '_helpers.py',
    }
    guarded_paths = [
        SRC_ROOT / 'presentation' / 'main_window_actions.py',
        SRC_ROOT / 'presentation' / 'main_window_tasks.py',
        *(path for path in (SRC_ROOT / 'presentation' / 'coordinators').glob('*.py') if path.name != '_helpers.py'),
    ]
    for path in guarded_paths:
        text = path.read_text(encoding='utf-8')
        assert 'except Exception' not in text, f'presentation boundary catch should be centralized: {path.relative_to(PROJECT_ROOT)}'
    for path in allowed:
        text = path.read_text(encoding='utf-8')
        assert 'except Exception' in text, f'missing centralized presentation error boundary: {path.relative_to(PROJECT_ROOT)}'


def test_coordinators_only_touch_view_boundary_methods_for_widget_projection():
    forbidden_markers = (
        '.status_panel',
        '.playback_panel',
        '.benchmark_panel',
        '.scene_controller',
        '.scene_widget',
        '.target_panel',
        '.robot_panel',
        '._set_busy',
        '._set_playback_running',
    )
    for path in (SRC_ROOT / 'presentation' / 'coordinators').glob('*.py'):
        if path.name in {'__init__.py', '_helpers.py'}:
            continue
        text = path.read_text(encoding='utf-8')
        for marker in forbidden_markers:
            assert marker not in text, f'coordinator should project through view boundary ({marker}): {path.relative_to(PROJECT_ROOT)}'
<<<<<<< HEAD


def test_main_window_and_view_contracts_do_not_store_pending_task_requests():
    for path in (
        SRC_ROOT / 'presentation' / 'main_window.py',
        SRC_ROOT / 'presentation' / 'view_contracts.py',
    ):
        text = path.read_text(encoding='utf-8')
        assert '_pending_ik_request' not in text, f'pending IK request leaked into window contract: {path.relative_to(PROJECT_ROOT)}'
        assert '_pending_traj_request' not in text, f'pending trajectory request leaked into window contract: {path.relative_to(PROJECT_ROOT)}'



def test_main_window_legacy_impl_surface_is_removed():
    observed = set()
    for path in (
        SRC_ROOT / 'presentation' / 'main_window_actions.py',
        SRC_ROOT / 'presentation' / 'main_window_tasks.py',
    ):
        text = path.read_text(encoding='utf-8')
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('def _') and '_impl(' in line:
                observed.add(line.split('def ', 1)[1].split('(', 1)[0])
    assert observed == set()



def test_view_contracts_define_task_scoped_protocols():
    text = (SRC_ROOT / 'presentation' / 'view_contracts.py').read_text(encoding='utf-8')
    assert 'class IKTaskView' in text
    assert 'class TrajectoryTaskView' in text


def test_legacy_monolithic_main_window_protocol_is_removed():
    text = (SRC_ROOT / 'presentation' / 'view_contracts.py').read_text(encoding='utf-8')
    assert 'class MainWindowLike' not in text
    assert 'class MainWindowActionView' in text
    assert 'class MainWindowTaskView' in text
    assert 'class MainWindowUIContract' in text




def test_coordinator_constructors_no_longer_guess_dependencies_from_window():
    for path in (SRC_ROOT / 'presentation' / 'coordinators').glob('*coordinator.py'):
        text = path.read_text(encoding='utf-8')
        assert "getattr(window, 'runtime_facade'" not in text
        assert "getattr(window, 'robot_facade'" not in text
        assert "getattr(window, 'solver_facade'" not in text
        assert "getattr(window, 'trajectory_facade'" not in text
        assert "getattr(window, 'benchmark_facade'" not in text
        assert "getattr(window, 'export_facade'" not in text
        assert "getattr(window, 'playback_facade'" not in text
        assert "getattr(window, 'threader'" not in text
        assert "getattr(window, 'playback_threader'" not in text

def test_main_window_builds_through_presentation_assembly():
    text = (SRC_ROOT / 'presentation' / 'main_window.py').read_text(encoding='utf-8')
    assert 'build_presentation_assembly(' in text
    assert 'MainController(' not in text
    assert 'ThreadOrchestrator(' not in text


def test_main_window_uses_grouped_runtime_bundles_instead_of_installing_peer_aliases():
    text = (SRC_ROOT / 'presentation' / 'main_window.py').read_text(encoding='utf-8')
    assert 'runtime_services' in text
    assert 'workflow_facades' in text
    assert 'task_orchestration' in text
    assert '_install_window_runtime_aliases' not in text


def test_render_state_segment_delegates_to_render_telemetry_service():
    text = (SRC_ROOT / 'presentation' / 'state_segments.py').read_text(encoding='utf-8')
    assert 'RenderTelemetryService' in text
    assert 'telemetry_service' in text


def test_state_store_routes_subscriber_bookkeeping_through_registry_support():
    text = (SRC_ROOT / 'presentation' / 'state_store.py').read_text(encoding='utf-8')
    assert 'StateSubscriberRegistry' in text
    assert '_segment_subscribers' not in text


def test_main_controller_builds_collaborators_through_support_module():
    text = (SRC_ROOT / 'presentation' / 'main_controller.py').read_text(encoding='utf-8')
    assert 'build_presentation_collaborators' in text
    assert 'install_main_controller_collaborators' in text
    assert 'class _PresentationControllerCollaborators' not in text
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
