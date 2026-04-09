<<<<<<< HEAD
from __future__ import annotations

from types import SimpleNamespace

import pytest

from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent
from robot_sim.domain.errors import CancelledTaskError, ExportRobotError
from robot_sim.model.pose import Pose
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.coordinators.scene_coordinator import SceneCoordinator
from robot_sim.presentation.state_store import StateStore


class DummyThreader:
    def __init__(self):
        self.started = []

    def start(self, **kwargs):
        self.started.append(kwargs)
        return SimpleNamespace(task_id='shot-1', task_kind=kwargs.get('task_kind', 'unknown'))




class DummyRuntimeFacade:
    def __init__(self, state_store: StateStore):
        self.export_root = '.'
        self.state_store = state_store

    @property
    def state(self):
        return self.state_store.state
=======
from types import SimpleNamespace

from robot_sim.presentation.coordinators.scene_coordinator import SceneCoordinator
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


class DummyWindow:
    def __init__(self):
        self.scene_widget = SimpleNamespace(
            fit_called=False,
            trajectory_cleared=False,
            fit_camera=self._fit,
            clear_trajectory=self._clear,
<<<<<<< HEAD
            scene_snapshot=lambda: {
                'title': 'Robot Sim Engine',
                'robot_points': [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
                'trajectory_points': None,
                'playback_marker': None,
                'target_pose': None,
                'target_axes_visible': True,
                'trajectory_visible': True,
            },
        )
        self.scene_controller = SimpleNamespace(cleared=False, clear_transient_visuals=self._clear_visuals)
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        state_store = StateStore(SessionState(target_pose=Pose(p=[0.4, 0.0, 0.3], R=[[1,0,0],[0,1,0],[0,0,1]])))
        self.runtime_facade = DummyRuntimeFacade(state_store)
        self.threader = DummyThreader()
        self.project_task_started = lambda task_kind, message: self.status_panel.append(f'{task_kind}:{message}')
        self.project_task_registered = lambda task_id, task_kind: self.status_panel.append(f'registered:{task_kind}:{task_id}')
        self.project_scene_fit = lambda: (self.scene_widget.fit_camera(), self.status_panel.append('3D 视图已适配到当前场景'))
        self.project_scene_path_cleared = lambda: (self.scene_controller.clear_transient_visuals(), self.scene_widget.clear_trajectory(), self.status_panel.append('末端轨迹显示已清空'))
        self.build_scene_capture_request = lambda path: {'path': path, 'snapshot': self.scene_widget.scene_snapshot()}
        self.project_scene_capture = lambda result: self.status_panel.append(f'场景截图已导出：{result}')
        self.read_scene_obstacle_request = lambda: {'object_id': 'box', 'center': [0.4, 0.0, 0.3], 'size': [0.2, 0.2, 0.2]}
        self.project_scene_obstacles_updated = lambda scene: self.status_panel.append(f'scene:{scene.revision}:{len(scene.obstacles)}')
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))
        self.on_worker_failed = lambda failure: self._projected.append(('failed', str(getattr(failure, 'message', failure))))
        self.on_worker_cancelled = lambda: self._projected.append(('cancelled', 'cancelled'))
=======
            capture_screenshot=lambda path: 'capture.png',
        )
        self.scene_controller = SimpleNamespace(cleared=False, clear_transient_visuals=self._clear_visuals)
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        self.runtime_facade = SimpleNamespace(export_root='.')
        self.project_scene_fit = lambda: (self.scene_widget.fit_camera(), self.status_panel.append('3D 视图已适配到当前场景'))
        self.project_scene_path_cleared = lambda: (self.scene_controller.clear_transient_visuals(), self.scene_widget.clear_trajectory(), self.status_panel.append('末端轨迹显示已清空'))
        self.capture_scene_screenshot = lambda path: self.scene_widget.capture_screenshot(path)
        self.project_scene_capture = lambda result: self.status_panel.append(f'场景截图已导出：{result}')
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    def _fit(self):
        self.scene_widget.fit_called = True

    def _clear(self):
        self.scene_widget.trajectory_cleared = True

    def _clear_visuals(self):
        self.scene_controller.cleared = True


<<<<<<< HEAD
class FakeScreenshotService:
    def __init__(self, *, failure: Exception | None = None):
        self.failure = failure

    def snapshot_sampling_counters(self, snapshot, *, backend: str, source: str):
        return (
            {
                'capability': 'screenshot',
                'counter_name': 'drawable_samples',
                'backend': backend,
                'value': len(snapshot.get('robot_points', [])),
                'unit': 'samples',
                'source': source,
            },
        )

    def snapshot_sample_count(self, snapshot):
        return len(snapshot.get('robot_points', []))

    def capture_from_snapshot(self, _snapshot, path, **_kwargs):
        if self.failure is not None:
            raise self.failure
        return str(path)



def test_scene_coordinator_handles_fit_clear_and_background_capture():
    window = DummyWindow()
    coord = SceneCoordinator(
        window,
        runtime=window.runtime_facade,
        threader=window.threader,
        screenshot_service=FakeScreenshotService(),
    )
    coord.fit()
    coord.clear_path()
    coord.capture()

    assert window.scene_widget.fit_called is True
    assert window.scene_widget.trajectory_cleared is True
    assert window.scene_controller.cleared is True
    assert [item['task_kind'] for item in window.threader.started] == ['screenshot']

    payload = window.threader.started[0]['worker']._invoke_with_control()
    window.threader.started[0]['on_finished'](payload)

    assert window.status_panel.messages[:4] == [
        '3D 视图已适配到当前场景',
        '末端轨迹显示已清空',
        'screenshot:场景截图任务已启动',
        'registered:screenshot:shot-1',
    ]
    assert window.status_panel.messages[-1] == f"场景截图已导出：{payload['path']}"
    snap = window.runtime_facade.state_store.snapshot()
    assert len(snap.render_operation_spans) == 1
    assert snap.render_operation_spans[0].operation == 'capture_from_snapshot'
    assert snap.render_operation_spans[0].status == 'succeeded'
    assert len(snap.render_sampling_counters) >= 1
    perf = snap.render_backend_performance[0]
    assert any(count >= 1 for count in perf.latency_buckets.values())
    assert perf.live_counters['drawable_samples'] >= 2.0



def test_scene_coordinator_routes_failed_capture_through_failed_event_path():
    window = DummyWindow()
    coord = SceneCoordinator(
        window,
        runtime=window.runtime_facade,
        threader=window.threader,
        screenshot_service=FakeScreenshotService(failure=OSError('disk full')),
    )
    coord.capture()

    with pytest.raises(ExportRobotError) as excinfo:
        window.threader.started[0]['worker']._invoke_with_control()

    error = excinfo.value
    event = WorkerFailedEvent(
        task_id='shot-1',
        task_kind='screenshot',
        message=str(error),
        error_code=error.error_code,
        exception_type=error.__class__.__name__,
        metadata=dict(error.metadata),
        severity='error',
    )
    window.threader.started[0]['on_failed_event'](event)

    snap = window.runtime_facade.state_store.snapshot()
    assert window._projected[-1][0] == 'failed'
    assert len(snap.render_operation_spans) == 1
    assert snap.render_operation_spans[0].status == 'failed'
    assert snap.render_operation_spans[0].error_code == error.error_code
    assert snap.render_sampling_counters[0].counter_name == 'drawable_samples'
    assert all('场景截图已导出' not in item for item in window.status_panel.messages)



def test_scene_coordinator_routes_cancelled_capture_through_cancelled_event_path():
    window = DummyWindow()
    coord = SceneCoordinator(
        window,
        runtime=window.runtime_facade,
        threader=window.threader,
        screenshot_service=FakeScreenshotService(failure=CancelledTaskError('scene capture cancelled')),
    )
    coord.capture()

    with pytest.raises(CancelledTaskError) as excinfo:
        window.threader.started[0]['worker']._invoke_with_control()

    error = excinfo.value
    event = WorkerCancelledEvent(
        task_id='shot-1',
        task_kind='screenshot',
        message=str(error),
        metadata=dict(error.metadata),
    )
    window.threader.started[0]['on_cancelled_event'](event)

    snap = window.runtime_facade.state_store.snapshot()
    assert window._projected[-1] == ('cancelled', 'cancelled')
    assert len(snap.render_operation_spans) == 1
    assert snap.render_operation_spans[0].status == 'cancelled'
    assert snap.render_sampling_counters[0].counter_name == 'drawable_samples'
    assert all('场景截图已导出' not in item for item in window.status_panel.messages)


def test_scene_coordinator_records_failed_telemetry_for_missing_capture_path():
    window = DummyWindow()
    window.build_scene_capture_request = lambda _path: {'snapshot': window.scene_widget.scene_snapshot()}
    coord = SceneCoordinator(
        window,
        runtime=window.runtime_facade,
        threader=window.threader,
        screenshot_service=FakeScreenshotService(),
    )
    coord.capture()

    with pytest.raises(ExportRobotError) as excinfo:
        window.threader.started[0]['worker']._invoke_with_control()

    error = excinfo.value
    event = WorkerFailedEvent(
        task_id='shot-1',
        task_kind='screenshot',
        message=str(error),
        error_code=error.error_code,
        exception_type=error.__class__.__name__,
        metadata=dict(error.metadata),
        severity='error',
    )
    window.threader.started[0]['on_failed_event'](event)

    snap = window.runtime_facade.state_store.snapshot()
    assert window._projected[-1][0] == 'failed'
    assert len(snap.render_operation_spans) == 1
    assert snap.render_operation_spans[0].status == 'failed'
    assert snap.render_operation_spans[0].error_code == error.error_code
    assert snap.render_operation_spans[0].message
    assert len(snap.render_sampling_counters) == 0



def test_scene_coordinator_records_failed_telemetry_for_invalid_snapshot_payload():
    window = DummyWindow()
    window.build_scene_capture_request = lambda path: {'path': path, 'snapshot': 123}
    coord = SceneCoordinator(
        window,
        runtime=window.runtime_facade,
        threader=window.threader,
        screenshot_service=FakeScreenshotService(),
    )
    coord.capture()

    with pytest.raises(ExportRobotError) as excinfo:
        window.threader.started[0]['worker']._invoke_with_control()

    error = excinfo.value
    event = WorkerFailedEvent(
        task_id='shot-1',
        task_kind='screenshot',
        message=str(error),
        error_code=error.error_code,
        exception_type=error.__class__.__name__,
        metadata=dict(error.metadata),
        severity='error',
    )
    window.threader.started[0]['on_failed_event'](event)

    snap = window.runtime_facade.state_store.snapshot()
    assert window._projected[-1][0] == 'failed'
    assert len(snap.render_operation_spans) == 1
    assert snap.render_operation_spans[0].status == 'failed'
    assert snap.render_operation_spans[0].error_code == error.error_code
    assert len(snap.render_sampling_counters) == 0


def test_scene_coordinator_adds_and_clears_runtime_obstacles():
    window = DummyWindow()
    coord = SceneCoordinator(window, runtime=window.runtime_facade, threader=window.threader, screenshot_service=FakeScreenshotService())

    coord.add_obstacle()
    scene = window.runtime_facade.state_store.state.planning_scene
    assert scene is not None
    assert scene.obstacle_ids == ('box',)
    assert window.runtime_facade.state_store.state.scene_summary['obstacle_count'] == 1

    coord.clear_obstacles()
    scene = window.runtime_facade.state_store.state.planning_scene
    assert scene is not None
    assert scene.obstacle_ids == ()
    assert window.runtime_facade.state_store.state.scene_summary['obstacle_count'] == 0


def test_scene_coordinator_accepts_legacy_capture_use_case_alias():
    window = DummyWindow()
    capture_uc = object()
    coord = SceneCoordinator(
        window,
        runtime=window.runtime_facade,
        threader=window.threader,
        screenshot_service=FakeScreenshotService(),
        capture_scene_uc=capture_uc,
    )
    assert coord.capture_scene_use_case is capture_uc


def test_scene_coordinator_rejects_conflicting_capture_use_case_aliases():
    window = DummyWindow()
    with pytest.raises(ValueError):
        SceneCoordinator(
            window,
            runtime=window.runtime_facade,
            threader=window.threader,
            screenshot_service=FakeScreenshotService(),
            capture_scene_use_case=object(),
            capture_scene_uc=object(),
        )
=======
def test_scene_coordinator_handles_fit_clear_and_capture():
    window = DummyWindow()
    coord = SceneCoordinator(window)
    coord.fit()
    coord.clear_path()
    coord.capture()
    assert window.scene_widget.fit_called is True
    assert window.scene_widget.trajectory_cleared is True
    assert window.scene_controller.cleared is True
    assert window.status_panel.messages == [
        '3D 视图已适配到当前场景',
        '末端轨迹显示已清空',
        '场景截图已导出：capture.png',
    ]
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
