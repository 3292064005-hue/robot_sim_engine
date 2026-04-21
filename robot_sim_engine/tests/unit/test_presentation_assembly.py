from __future__ import annotations

from types import SimpleNamespace

from robot_sim.presentation import assembly as mod


class _StubController:
    def __init__(self, *_args, **_kwargs) -> None:
        self.runtime_facade = SimpleNamespace(app_config={'window': {'title': 'Robot Sim Engine'}}, metrics_service='metrics')
        self.robot_workflow = 'robot-workflow'
        self.motion_workflow = 'motion-workflow'
        self.export_workflow = 'export-workflow'


def test_build_presentation_assembly_returns_grouped_window_runtime(monkeypatch) -> None:
    monkeypatch.setattr(mod, 'MainController', _StubController)
    monkeypatch.setattr(mod, 'ThreadOrchestrator', lambda *args, **kwargs: SimpleNamespace(policy=kwargs.get('start_policy', 'cancel_and_replace')))
    monkeypatch.setattr(mod, 'PlaybackRenderScheduler', lambda *args, **kwargs: 'scheduler')
    monkeypatch.setattr(mod, 'RobotCoordinator', lambda *args, **kwargs: 'robot_coord')
    monkeypatch.setattr(mod, 'IKTaskCoordinator', lambda *args, **kwargs: 'ik_coord')
    monkeypatch.setattr(mod, 'TrajectoryTaskCoordinator', lambda *args, **kwargs: 'traj_coord')
    monkeypatch.setattr(mod, 'BenchmarkTaskCoordinator', lambda *args, **kwargs: 'bench_coord')
    monkeypatch.setattr(mod, 'PlaybackTaskCoordinator', lambda *args, **kwargs: 'playback_coord')
    monkeypatch.setattr(mod, 'ExportTaskCoordinator', lambda *args, **kwargs: 'export_coord')
    monkeypatch.setattr(mod, 'SceneCoordinator', lambda *args, **kwargs: 'scene_coord')
    monkeypatch.setattr(mod, 'StatusCoordinator', lambda *args, **kwargs: 'status_coord')

    assembly = mod.build_presentation_assembly('.', container=object(), window_parent=None)

    assert assembly.window_runtime.runtime_services.runtime_facade.app_config['window']['title'] == 'Robot Sim Engine'
    assert assembly.window_runtime.workflow_services.robot_workflow == 'robot-workflow'
    assert assembly.window_runtime.task_orchestration.threader.policy == 'cancel_and_replace'
    assert assembly.window_runtime.task_orchestration.playback_threader.policy == 'queue_latest'
    assert assembly.window_runtime.task_orchestration.status_coordinator == 'status_coord'


def test_build_presentation_assembly_requires_container() -> None:
    try:
        mod.build_presentation_assembly('.', container=None, window_parent=None)
    except ValueError as exc:
        assert 'explicit application container' in str(exc)
    else:
        raise AssertionError('ValueError expected when container is missing')
