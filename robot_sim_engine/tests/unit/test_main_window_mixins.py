from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from robot_sim.domain.enums import TaskState
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.session_state import SessionState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.presentation.coordinators import (
    BenchmarkTaskCoordinator,
    ExportTaskCoordinator,
    IKTaskCoordinator,
    PlaybackTaskCoordinator,
    RobotCoordinator,
    SceneCoordinator,
    StatusCoordinator,
    TrajectoryTaskCoordinator,
)
from robot_sim.presentation.main_window_actions import MainWindowActionMixin
from robot_sim.presentation.main_window_tasks import MainWindowTaskMixin
from robot_sim.presentation.main_window_ui import MainWindowUIMixin
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.render_telemetry_state import build_render_telemetry_panel_state
from robot_sim.presentation.status_panel_state import build_render_runtime_panel_state


class DummySignal:
    def __init__(self):
        self.connected = []

    def connect(self, callback):
        self.connected.append(callback)


class ValueWidget:
    def __init__(self, value=None, checked=False, text=''):
        self._value = value
        self._checked = checked
        self._text = text
        self.clicked = DummySignal()
        self.valueChanged = DummySignal()
        self.toggled = DummySignal()

    def value(self):
        return self._value

    def isChecked(self):
        return self._checked

    def currentText(self):
        return self._text


class DummySummary:
    def __init__(self):
        self.text = ''

    def setText(self, text):
        self.text = text


class DummyStatusPanel:
    def __init__(self):
        self.summary = DummySummary()
        self.metrics = {}
        self.messages = []
        self.render_runtime = None

    def set_metrics(self, **kwargs):
        self.metrics.update(kwargs)

    def set_render_runtime(self, panel_state):
        self.render_runtime = panel_state
        self.metrics.update(panel_state.metric_payload)

    def append(self, message):
        self.messages.append(message)


class DummyDiagnosticsPanel:
    def __init__(self):
        self.values = None
        self.render_telemetry = None

    def set_values(self, **kwargs):
        self.values = kwargs

    def set_render_telemetry(self, panel_state):
        self.render_telemetry = panel_state


class DummyBenchmarkPanel:
    def __init__(self):
        self.summary = DummySummary()
        self.log = SimpleNamespace(clear=lambda: None)
        self.run_btn = ValueWidget()
        self.export_btn = ValueWidget()
        self.running = None
        self.report = None

    def set_running(self, running):
        self.running = running

    def set_report(self, report):
        self.report = report


class DummySolverPanel:
    def __init__(self):
        self.mode_combo = ValueWidget(text='dls')
        self.max_iters = ValueWidget(value=50)
        self.step_scale = ValueWidget(value=0.5)
        self.damping = ValueWidget(value=0.1)
        self.enable_nullspace = ValueWidget(checked=True)
        self.position_only = ValueWidget(checked=False)
        self.pos_tol = ValueWidget(value=1e-3)
        self.ori_tol = ValueWidget(value=1e-3)
        self.max_step_norm = ValueWidget(value=0.2)
        self.auto_fallback = ValueWidget(checked=True)
        self.reachability_precheck = ValueWidget(checked=True)
        self.retry_count = ValueWidget(value=2)
        self.joint_limit_weight = ValueWidget(value=0.2)
        self.manipulability_weight = ValueWidget(value=0.1)
        self.orientation_weight = ValueWidget(value=1.0)
        self.adaptive_damping = ValueWidget(checked=True)
        self.weighted_ls = ValueWidget(checked=False)
        self.run_fk_btn = ValueWidget()
        self.run_ik_btn = ValueWidget()
        self.cancel_btn = ValueWidget()
        self.plan_btn = ValueWidget()
        self.traj_duration = ValueWidget(value=3.0)
        self.traj_dt = ValueWidget(value=0.1)
        self.traj_mode = ValueWidget(text='joint_space')
        self.running = None

    def set_running(self, running):
        self.running = running

    def apply_defaults(self, *_args, **_kwargs):
        return None

    def apply_trajectory_defaults(self, *_args, **_kwargs):
        return None


class DummyPlaybackPanel:
    def __init__(self):
        self.play_btn = ValueWidget()
        self.pause_btn = ValueWidget()
        self.stop_btn = ValueWidget()
        self.step_btn = ValueWidget()
        self.slider = ValueWidget(value=0)
        self.speed = ValueWidget(value=1.0)
        self.loop = ValueWidget(checked=False)
        self.export_btn = ValueWidget()
        self.session_btn = ValueWidget()
        self.package_btn = ValueWidget()
        self.running = None
        self.frame = None
        self.total = None

    def set_running(self, running):
        self.running = running

    def set_total_frames(self, total):
        self.total = total

    def set_frame(self, frame, total):
        self.frame = (frame, total)


class DummyRobotPanel:
    def __init__(self):
        self.load_button = ValueWidget()
        self.save_button = ValueWidget()
        self.spec = None

    def selected_robot_name(self):
        return 'planar_2dof'

    def edited_home_q(self):
        return [0.1, 0.2]

    def edited_rows(self):
        return []

    def set_robot_spec(self, spec):
        self.spec = spec


class DummyTargetPanel:
    def __init__(self):
        self.fill_current_btn = ValueWidget()
        self.orientation_mode = ValueWidget(text='rvec')
        self.pose = None

    def values6(self):
        return [1, 2, 3, 0, 0, 0]

    def set_from_pose(self, pose):
        self.pose = pose


class DummySceneToolbar:
    def __init__(self):
        self.fit_requested = DummySignal()
        self.clear_path_requested = DummySignal()
        self.screenshot_requested = DummySignal()
        self.add_obstacle_requested = DummySignal()
        self.clear_obstacles_requested = DummySignal()
        self.target_axes_toggled = DummySignal()
        self.trajectory_toggled = DummySignal()


class DummySceneWidget:
    def __init__(self):
        self.fit_called = False
        self.trajectory_cleared = False
        self.target_axes_visible = None
        self.trajectory_visible = None
        self.screenshot_service = SimpleNamespace(runtime_state=lambda _widget: SimpleNamespace(capability='screenshot', status='degraded', backend='snapshot_renderer', reason='snapshot_renderer_fallback', error_code='', message='fallback', metadata={}))

    def fit_camera(self):
        self.fit_called = True

    def clear_trajectory(self):
        self.trajectory_cleared = True

    def set_target_axes_visible(self, visible):
        self.target_axes_visible = visible

    def scene_snapshot(self):
        return {
            'title': 'Robot Sim Engine',
            'robot_points': [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            'trajectory_points': None,
            'playback_marker': None,
            'target_pose': None,
            'target_axes_visible': True,
            'trajectory_visible': True,
        }

    def set_trajectory_visible(self, visible):
        self.trajectory_visible = visible

    def capture_screenshot(self, _path):
        return 'capture.png'

    def scene_runtime_state(self):
        return SimpleNamespace(capability='scene_3d', status='degraded', backend='pyvistaqt', reason='backend_initialization_failed', error_code='render_initialization_failed', message='init failed', metadata={})

    def screenshot_runtime_state(self):
        return SimpleNamespace(capability='screenshot', status='degraded', backend='snapshot_renderer', reason='snapshot_renderer_fallback', error_code='', message='fallback', metadata={})


class DummySceneController:
    def __init__(self):
        self.reset_called = False
        self.fk_updates = []
        self.playback_updates = []
        self.trajectory_points = None
        self.cleared = False
        self.scene_updates = []

    def reset_path(self):
        self.reset_called = True

    def update_fk_projection(self, *args, **kwargs):
        self.fk_updates.append((args, kwargs))

    def update_playback_projection(self, *args, **kwargs):
        self.playback_updates.append((args, kwargs))

    def set_trajectory_from_fk_samples(self, points):
        self.trajectory_points = np.asarray(points)

    def clear_transient_visuals(self):
        self.cleared = True

    def update_planning_scene_projection(self, scene):
        self.scene_updates.append(scene)


class DummyPlotsManager:
    def __init__(self):
        self.actions = []

    def clear(self, name):
        self.actions.append(('clear', name))

    def set_curve(self, panel, name, x, y):
        self.actions.append(('curve', panel, name, len(x), len(y)))

    def set_cursor(self, panel, value):
        self.actions.append(('cursor', panel, value))

    def runtime_state(self):
        return SimpleNamespace(capability='plots', status='available', backend='pyqtgraph', reason='plot_widgets_ready', error_code='', message='plots ready', metadata={})


class DummyThreader:
    def __init__(self):
        self.cancelled = False
        self.stopped = False
        self.started = None
        self.task_state_changed = DummySignal()

    def cancel(self):
        self.cancelled = True

    def stop(self, wait=False):
        self.stopped = True
        self.wait = wait

    def start(self, **kwargs):
        self.started = kwargs
        return SimpleNamespace(task_id='task-1', task_kind=kwargs.get('task_kind', 'unknown'))


class DummyPlaybackService:
    def build_state(self, *_args, **_kwargs):
        return PlaybackState(is_playing=False, frame_idx=0, total_frames=2, speed_multiplier=1.0, loop_enabled=False)


class DummyMetricsService:
    def summarize_ik(self, _result):
        return {
            'iterations': 3,
            'final_pos_err': 1e-4,
            'final_ori_err': 2e-4,
            'final_cond': 10.0,
            'final_manipulability': 0.2,
            'final_dq_norm': 0.05,
            'effective_mode': 'dls',
            'final_damping': 0.1,
            'stop_reason': 'converged',
            'elapsed_ms': 5.0,
        }

    def summarize_trajectory(self, _traj):
        return {'mode': 'joint_space', 'num_samples': 2, 'duration': 1.0, 'feasible': True, 'path_length': 1.0, 'jerk_proxy': 0.0}

    def summarize_benchmark(self, report):
        return {'num_cases': report.num_cases, 'success_rate': report.success_rate, 'p95_elapsed_ms': 1.0, 'mean_restarts_used': 0.0}


@dataclass
class DummyErrorPresentation:
    title: str = 'Err'
    user_message: str = 'boom'
    log_payload: dict[str, object] = None


class DummyTaskErrorMapper:
    def map_exception(self, _exc):
        return DummyErrorPresentation(log_payload={})


class DummyController:
    def __init__(self):
        self.state_store = StateStore(SessionState())
        self.state_store.patch(playback=PlaybackState(is_playing=False, frame_idx=0, total_frames=0, speed_multiplier=1.0, loop_enabled=False))
        self.state_store.patch(robot_spec=SimpleNamespace(label='Planar'), q_current=np.array([0.0, 0.0]))
        self.metrics_service = DummyMetricsService()
        self.playback_service = DummyPlaybackService()
        self.task_error_mapper = DummyTaskErrorMapper()
        self.project_root = '.'
        self.app_config = {'window': {'title': 't', 'width': 100, 'height': 100, 'splitter_sizes': [1, 1, 1], 'vertical_splitter_sizes': [1, 1]}}
        self.ik_uc = object()
        self.traj_uc = object()
        self.benchmark_uc = object()
        self.fk_calls = []
        self.playback_options = []

    @property
    def state(self):
        return self.state_store.state

    def robot_entries(self):
        return ['planar_2dof']

    def solver_defaults(self):
        return {}

    def trajectory_defaults(self):
        return {}

    def load_robot(self, _name):
        pose = SimpleNamespace(p=np.array([1.0, 2.0, 3.0]))
        fk = SimpleNamespace(ee_pose=pose, joint_positions=np.zeros((2, 3)))
        self.state_store.patch(robot_spec=SimpleNamespace(label='Planar'), fk_result=fk)
        return fk

    def save_current_robot(self, **_kwargs):
        return 'robot.yaml'

    def run_fk(self, q=None):
        self.fk_calls.append(q)
        pose = SimpleNamespace(p=np.array([1.0, 2.0, 3.0]))
        fk = SimpleNamespace(ee_pose=pose, joint_positions=np.zeros((2, 3)))
        self.state_store.patch(fk_result=fk)
        return fk

    def build_ik_request(self, values, **kwargs):
        return SimpleNamespace(target=values, config=SimpleNamespace(mode=SimpleNamespace(value='dls')), q0=np.array([0.0, 0.0]))

    def apply_ik_result(self, _req, result):
        self.state_store.patch(ik_result=result, fk_result=self.run_fk(q=result.q_sol))

    def build_trajectory_request(self, **kwargs):
        return SimpleNamespace(**kwargs)

    def apply_trajectory(self, traj):
        self.state_store.patch(trajectory=traj, playback=PlaybackState(is_playing=False, frame_idx=0, total_frames=traj.t.shape[0], speed_multiplier=1.0, loop_enabled=False))

    def sample_ee_positions(self, _q):
        return np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    def build_benchmark_config(self, **kwargs):
        return kwargs

    def set_playback_options(self, **kwargs):
        self.playback_options.append(kwargs)
        pb = self.state.playback
        speed = kwargs.get('speed_multiplier', pb.speed_multiplier)
        loop = kwargs.get('loop_enabled', pb.loop_enabled)
        self.state_store.patch(playback=PlaybackState(is_playing=pb.is_playing, frame_idx=pb.frame_idx, total_frames=pb.total_frames, speed_multiplier=speed, loop_enabled=loop))

    def next_playback_frame(self):
        return SimpleNamespace(frame_idx=1, t=0.5, q=np.array([0.2, 0.1]), qd=np.array([0.0, 0.0]), qdd=np.array([0.0, 0.0]), joint_positions=np.zeros((2, 3)), ee_position=np.array([1, 0, 0]))

    def set_playback_frame(self, idx):
        return SimpleNamespace(frame_idx=idx, t=0.5, q=np.array([0.2, 0.1]), qd=np.array([0.0, 0.0]), qdd=np.array([0.0, 0.0]), joint_positions=np.zeros((2, 3)), ee_position=np.array([1, 0, 0]))

    def export_trajectory(self):
        return 'trajectory.csv'

    def export_trajectory_metrics(self, _name, _metrics):
        return 'trajectory_metrics.json'

    def export_session(self):
        return 'session.json'

    def export_package(self):
        return 'package.zip'

    def export_benchmark(self):
        return 'benchmark.json'

    def export_benchmark_cases_csv(self):
        return 'benchmark.csv'


class DummyWindow(MainWindowTaskMixin, MainWindowActionMixin, MainWindowUIMixin):
    def __init__(self):
        self.controller = DummyController()
        self.metrics_service = self.controller.metrics_service
        self.runtime_facade = self.controller
        self.robot_facade = SimpleNamespace(
            robot_entries=self.controller.robot_entries,
            load_robot=self.controller.load_robot,
            save_current_robot=self.controller.save_current_robot,
        )
        self.solver_facade = SimpleNamespace(
            ik_use_case=self.controller.ik_uc,
            build_ik_request=self.controller.build_ik_request,
            apply_ik_result=self.controller.apply_ik_result,
            solver_defaults=self.controller.solver_defaults,
        )
        self.trajectory_facade = SimpleNamespace(
            trajectory_use_case=self.controller.traj_uc,
            build_trajectory_request=self.controller.build_trajectory_request,
            apply_trajectory=self.controller.apply_trajectory,
            trajectory_defaults=self.controller.trajectory_defaults,
        )
        self.playback_facade = SimpleNamespace(state=self.controller.state, set_playback_options=self.controller.set_playback_options, next_playback_frame=self.controller.next_playback_frame, set_playback_frame=self.controller.set_playback_frame, ensure_playback_ready=lambda strict=True: None)
        self.benchmark_facade = SimpleNamespace(benchmark_use_case=self.controller.benchmark_uc, build_benchmark_config=self.controller.build_benchmark_config)
        self.export_facade = SimpleNamespace(export_trajectory=self.controller.export_trajectory, export_trajectory_metrics=self.controller.export_trajectory_metrics, export_session=self.controller.export_session, export_package=self.controller.export_package, export_benchmark=self.controller.export_benchmark, export_benchmark_cases_csv=self.controller.export_benchmark_cases_csv)
        self.threader = DummyThreader()
        self.playback_threader = DummyThreader()
        self.window_cfg = self.controller.app_config['window']
        self.robot_panel = DummyRobotPanel()
        self.target_panel = DummyTargetPanel()
        self.solver_panel = DummySolverPanel()
        self.playback_panel = DummyPlaybackPanel()
        self.scene_toolbar = DummySceneToolbar()
        self.scene_widget = DummySceneWidget()
        self.scene_controller = DummySceneController()
        self.status_panel = DummyStatusPanel()
        self.diagnostics_panel = DummyDiagnosticsPanel()
        self.benchmark_panel = DummyBenchmarkPanel()
        self.plots_manager = DummyPlotsManager()
        self.robot_coordinator = RobotCoordinator(self, robot=self.robot_facade)
        self.ik_task_coordinator = IKTaskCoordinator(self, solver=self.solver_facade, threader=self.threader)
        self.trajectory_task_coordinator = TrajectoryTaskCoordinator(self, trajectory=self.trajectory_facade, threader=self.threader)
        self.benchmark_task_coordinator = BenchmarkTaskCoordinator(self, runtime=self.runtime_facade, benchmark=self.benchmark_facade, threader=self.threader)
        self.playback_task_coordinator = PlaybackTaskCoordinator(self, runtime=self.runtime_facade, playback=self.playback_facade, playback_threader=self.playback_threader)
        self.export_task_coordinator = ExportTaskCoordinator(self, runtime=self.runtime_facade, export=self.export_facade, threader=self.threader, metrics_service=self.metrics_service)
        self.scene_coordinator = SceneCoordinator(self, runtime=self.runtime_facade, threader=self.threader)
        self.status_coordinator = StatusCoordinator(self, runtime=self.runtime_facade)

    def setCentralWidget(self, widget):
        self.central = widget

    def _pop_dummy_ik_request(self):
        request = self._ik_pending_request
        self._ik_pending_request = None
        return request

    def _pop_dummy_traj_request(self):
        request = self._traj_pending_request
        self._traj_pending_request = None
        return request

    def _playback_worker_factory(self, traj):
        return SimpleNamespace(traj=traj)

    def read_scene_obstacle_request(self):
        return {'object_id': 'obstacle', 'center': np.array([0.3, 0.0, 0.2]), 'size': np.array([0.2, 0.2, 0.2])}

    def project_scene_obstacles_updated(self, scene):
        self.scene_controller.update_planning_scene_projection(scene)
        self.status_panel.append('scene updated')

    def build_scene_capture_request(self, path):
        return {'path': path, 'snapshot': self.scene_widget.scene_snapshot()}


def test_ui_mixin_helper_methods_and_signal_wiring(monkeypatch):
    from robot_sim.presentation import main_window_ui as ui_mod

    class DummyPanel:
        def __init__(self, *args, **kwargs):
            self.load_button = ValueWidget()
            self.save_button = ValueWidget()
            self.fill_current_btn = ValueWidget()
            self.orientation_mode = ValueWidget(text='rvec')
            self.run_fk_btn = ValueWidget()
            self.run_ik_btn = ValueWidget()
            self.cancel_btn = ValueWidget()
            self.plan_btn = ValueWidget()
            self.play_btn = ValueWidget()
            self.pause_btn = ValueWidget()
            self.stop_btn = ValueWidget()
            self.step_btn = ValueWidget()
            self.slider = ValueWidget()
            self.speed = ValueWidget(value=1.0)
            self.loop = ValueWidget()
            self.export_btn = ValueWidget()
            self.session_btn = ValueWidget()
            self.package_btn = ValueWidget()
            self.fit_requested = DummySignal()
            self.clear_path_requested = DummySignal()
            self.screenshot_requested = DummySignal()
            self.add_obstacle_requested = DummySignal()
            self.clear_obstacles_requested = DummySignal()
            self.target_axes_toggled = DummySignal()
            self.trajectory_toggled = DummySignal()
            self.run_btn = ValueWidget()
            self.summary = DummySummary()
            self.log = SimpleNamespace(clear=lambda: None)

        def apply_defaults(self, *_a, **_k):
            return None

        def apply_trajectory_defaults(self, *_a, **_k):
            return None

        def set_running(self, *_a, **_k):
            return None

        def values6(self):
            return [1, 2, 3, 0, 0, 0]

        def edited_home_q(self):
            return [0.1, 0.2]

        def edited_rows(self):
            return []

        def selected_robot_name(self):
            return 'planar_2dof'

        def set_robot_spec(self, *_a, **_k):
            return None

        def set_from_pose(self, *_a, **_k):
            return None

        def set_total_frames(self, *_a, **_k):
            return None

        def set_frame(self, *_a, **_k):
            return None

        def set_metrics(self, **_kwargs):
            return None

        def append(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(ui_mod, 'RobotConfigPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'TargetPosePanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'SolverPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'PlaybackPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'BenchmarkPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'DiagnosticsPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'StatusPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'SceneToolbar', DummyPanel)
    monkeypatch.setattr(ui_mod, 'Scene3DWidget', DummySceneWidget)
    monkeypatch.setattr(ui_mod, 'SceneController', lambda widget: DummySceneController())
    monkeypatch.setattr(ui_mod, 'PlotsPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'PlotsManager', lambda *_args, **_kwargs: DummyPlotsManager())

    window = DummyWindow()
    window._build_ui()
    window._wire_signals()
    window._wire_task_signals()
    assert hasattr(window, 'central')
    assert window.threader.task_state_changed.connected
    assert window.robot_panel.load_button.clicked.connected


def test_ui_mixin_status_helpers_cover_busy_and_metrics():
    window = DummyWindow()
    assert window._playback_status_text() == '无轨迹'
    window.controller.state_store.patch(playback=PlaybackState(is_playing=True, frame_idx=0, total_frames=2, speed_multiplier=2.0, loop_enabled=False))
    assert '播放中' in window._playback_status_text()
    kwargs = window._build_solver_kwargs()
    assert kwargs['mode'] == 'dls'
    window._set_busy(True, 'ik')
    assert window.controller.state.is_busy is True
    window._set_playback_running(True)
    assert window.playback_panel.running is True
    window._update_diagnostics_from_trajectory({'mode': 'joint', 'feasible': True, 'feasibility_reasons': '', 'path_length': 1.2, 'jerk_proxy': 0.0})
    window._update_diagnostics_from_benchmark({'success_rate': 1.0, 'p95_elapsed_ms': 3.0, 'mean_restarts_used': 0.0})
    window._sync_status_after_snapshot()
    assert window.diagnostics_panel.values is not None


def test_action_mixin_robot_and_export_paths():
    window = DummyWindow()
    window.on_load_robot()
    window.on_save_robot()
    window.on_fill_current_pose()
    window.on_run_fk()
    window.on_fit_scene()
    window.on_clear_scene_path()
    window.on_capture_scene()
    window.on_add_scene_obstacle()
    window.on_clear_scene_obstacles()
    window.on_export_trajectory()
    window.on_export_session()
    window.on_export_package()
    window.on_export_benchmark()
    assert window.scene_controller.reset_called is True
    assert window.scene_widget.fit_called is True
    assert window.scene_controller.cleared is True
    assert window.scene_controller.scene_updates
    assert window.status_panel.messages


def test_task_mixin_covers_ik_trajectory_benchmark_and_worker_terminal_paths():
    window = DummyWindow()
    window.on_run_ik()
    assert window.threader.started['task_kind'] == 'ik'
    window.on_cancel_ik()
    assert window.threader.cancelled is True
    log = SimpleNamespace(attempt_idx=0, iter_idx=0, pos_err_norm=1e-3, ori_err_norm=2e-3, cond_number=10.0, manipulability=0.1, dq_norm=0.2, effective_mode='dls', damping_lambda=0.1, elapsed_ms=1.0)
    window.on_ik_progress(log)
    result = SimpleNamespace(success=True, q_sol=np.array([0.3, 0.4]), message='ok', logs=[log])
    window.on_ik_finished(result)
    window.on_plan()
    assert window.threader.started['task_kind'] == 'trajectory'
    traj = SimpleNamespace(t=np.array([0.0, 1.0]), q=np.array([[0.0, 0.0], [1.0, 1.0]]), qd=np.zeros((2,2)), qdd=np.zeros((2,2)), ee_positions=np.array([[0,0,0],[1,0,0]]))
    window.on_trajectory_finished(traj)
    window.on_run_benchmark()
    report = SimpleNamespace(num_cases=2, success_rate=1.0, cases=[{'name': 'a', 'success': True, 'stop_reason': 'ok', 'final_pos_err': 0.0, 'final_ori_err': 0.0}])
    window.on_benchmark_finished(report)
    snap = TaskSnapshot(task_id='x', task_kind='ik', task_state=TaskState.RUNNING)
    window._on_task_state_changed(snap)
    window.on_worker_failed('boom')
    window.on_worker_cancelled()
    assert window.controller.state.active_task_snapshot is snap


def test_action_and_playback_mixins_cover_playback_paths():
    window = DummyWindow()
    traj = SimpleNamespace(t=np.array([0.0, 1.0]), q=np.array([[0.0, 0.0], [1.0, 1.0]]), qd=np.zeros((2,2)), qdd=np.zeros((2,2)))
    window.controller.state_store.patch(trajectory=traj, playback=PlaybackState(is_playing=False, frame_idx=0, total_frames=2, speed_multiplier=1.0, loop_enabled=False))
    window.on_play()
    assert window.playback_threader.started['task_kind'] == 'playback'
    window.on_pause()
    assert window.playback_threader.cancelled is True
    window.on_stop_playback()
    assert window.playback_threader.stopped is True
    window.on_step()
    window.on_seek_frame(1)
    window.on_playback_speed_changed(1.5)
    window.on_playback_loop_changed(True)
    frame = SimpleNamespace(frame_idx=1, t=0.5, q=np.array([0.2, 0.1]), qd=np.array([0.0, 0.0]), qdd=np.array([0.0, 0.0]), joint_positions=np.zeros((2, 3)), ee_position=np.array([1, 0, 0]))
    window.on_playback_progress(frame)
    window.on_playback_finished(PlaybackState(is_playing=True, frame_idx=1, total_frames=2, speed_multiplier=1.0, loop_enabled=False))
    window.on_playback_cancelled()
    window.on_playback_failed('oops')
    assert window.playback_panel.frame is not None
    assert window.controller.playback_options



def test_render_runtime_state_is_projected_into_shared_state_and_status_metrics():
    window = DummyWindow()
    window.project_render_runtime_state(window._collect_render_runtime_state())
    render_runtime = window.runtime_facade.state.render_runtime
    assert render_runtime.scene_3d.status == 'degraded'
    assert render_runtime.plots.status == 'available'
    assert render_runtime.screenshot.backend == 'snapshot_renderer'
    assert 'scene_3d' in window.status_panel.metrics
    assert 'plots' in window.status_panel.metrics
    assert 'screenshot' in window.status_panel.metrics


def test_state_store_selector_subscription_suppresses_duplicate_render_emits():
    store = StateStore(SessionState())
    seen = []
    unsubscribe = store.subscribe_render_runtime(lambda runtime: seen.append(runtime), emit_current=True)
    store.patch_render_capability('scene_3d', {'status': 'degraded', 'backend': 'pyvistaqt'})
    store.patch_render_capability('scene_3d', {'status': 'degraded', 'backend': 'pyvistaqt'})
    unsubscribe()
    assert len(seen) == 2
    assert seen[-1].scene_3d.status == 'degraded'


def test_render_runtime_panel_projection_reports_formal_alert_summary():
    panel_state = build_render_runtime_panel_state({
        'scene_3d': {'status': 'unsupported', 'backend': 'pyvistaqt', 'reason': 'backend_dependency_missing'},
        'plots': {'status': 'degraded', 'backend': 'pyqtgraph', 'reason': 'operation_failed'},
        'screenshot': {'status': 'available', 'backend': 'snapshot_renderer'},
    })
    assert panel_state.overall_severity == 'critical'
    assert '1 个不可用' in panel_state.summary_text
    assert '1 个降级' in panel_state.summary_text


def test_status_panel_projection_subscription_tracks_shared_runtime_state():
    window = DummyWindow()
    window._ensure_status_panel_projection_subscription()
    window.controller.state_store.patch_render_capability('plots', {'status': 'unsupported', 'backend': 'pyqtgraph', 'reason': 'backend_dependency_missing'})
    assert window.status_panel.render_runtime is not None
    assert window.status_panel.render_runtime.overall_severity == 'critical'
    assert 'plots' in window.status_panel.metrics['plots'] or window.status_panel.metrics['plots'].startswith('不可用')


def test_render_runtime_projection_records_structured_telemetry_events():
    window = DummyWindow()
    window.project_render_runtime_state(window._collect_render_runtime_state(), source='ui_runtime_scan')
    telemetry = tuple(window.runtime_facade.state.render_telemetry)
    spans = tuple(window.runtime_facade.state.render_operation_spans)
    counters = tuple(window.runtime_facade.state.render_sampling_counters)
    backend_perf = tuple(window.runtime_facade.state.render_backend_performance)
    assert len(telemetry) >= 1
    assert telemetry[-1].source == 'ui_runtime_scan'
    assert telemetry[-1].capability in {'scene_3d', 'screenshot'}
    assert len(spans) >= 3
    assert all(span.operation == 'runtime_probe' for span in spans[-3:])
    assert len(counters) >= 3
    assert any(counter.counter_name == 'probe_count' for counter in counters)
    assert len(backend_perf) >= 1
    assert window.diagnostics_panel.render_telemetry is not None
    assert window.diagnostics_panel.render_telemetry.event_count == len(telemetry)
    assert window.diagnostics_panel.render_telemetry.span_count == len(spans)
    assert window.diagnostics_panel.render_telemetry.counter_count == len(counters)


def test_render_telemetry_panel_projection_formats_recent_event_log():
    panel_state = build_render_telemetry_panel_state(
        [
            {
                'sequence': 1,
                'capability': 'scene_3d',
                'event_kind': 'degraded',
                'severity': 'warning',
                'status': 'degraded',
                'previous_status': 'available',
                'backend': 'pyvistaqt',
                'reason': 'backend_initialization_failed',
                'source': 'ui_runtime_scan',
                'message': 'scene backend degraded',
            },
            {
                'sequence': 2,
                'capability': 'screenshot',
                'event_kind': 'unsupported',
                'severity': 'critical',
                'status': 'unsupported',
                'previous_status': 'degraded',
                'backend': 'none',
                'reason': 'capture_backend_missing',
                'error_code': 'unsupported_capture_backend',
                'source': 'worker_failure_projection',
                'message': 'capture backend missing',
            },
        ],
        operation_spans=[
            {
                'sequence': 1,
                'capability': 'screenshot',
                'operation': 'capture_from_snapshot',
                'backend': 'snapshot_renderer',
                'status': 'succeeded',
                'duration_ms': 11.5,
                'sample_count': 9,
                'source': 'scene_capture_worker',
                'message': 'capture completed',
            },
        ],
        sampling_counters=[
            {
                'sequence': 1,
                'capability': 'screenshot',
                'counter_name': 'drawable_samples',
                'backend': 'snapshot_renderer',
                'value': 9,
                'unit': 'samples',
                'source': 'scene_capture_worker',
            },
        ],
        backend_performance=[
            {
                'key': 'screenshot:snapshot_renderer',
                'capability': 'screenshot',
                'backend': 'snapshot_renderer',
                'total_spans': 1,
                'succeeded_spans': 1,
                'average_duration_ms': 11.5,
                'max_duration_ms': 11.5,
                'last_duration_ms': 11.5,
                'last_operation': 'capture_from_snapshot',
                'last_status': 'succeeded',
                'span_sample_total': 9,
                'sampling_totals': {'drawable_samples': 9.0},
                'sampling_maxima': {'drawable_samples': 9.0},
                'sampling_units': {'drawable_samples': 'samples'},
                'latency_buckets': {'le_16ms': 1},
                'duration_percentiles_ms': {'p50': 11.5, 'p95': 11.5},
                'rolling_duration_percentiles_ms': {'p50': 11.5},
                'rolling_window_seconds': 60.0,
                'rolling_observed_seconds': 1.0,
                'rolling_span_count': 1,
                'rolling_counter_count': 1,
                'rolling_span_rate_per_sec': 1.0,
                'rolling_counter_rate_per_sec': 1.0,
                'rolling_sample_throughput_per_sec': 9.0,
                'rolling_counter_throughput': {'drawable_samples': 9.0},
                'rolling_counter_units': {'drawable_samples': 'samples'},
                'live_counters': {'drawable_samples': 9.0},
                'live_counter_units': {'drawable_samples': 'samples'},
            },
        ],
    )
    assert panel_state.event_count == 2
    assert panel_state.latest_severity == 'critical'
    assert '#2' in panel_state.latest_summary
    assert panel_state.span_count == 1
    assert 'capture_from_snapshot' in panel_state.latest_span_summary
    assert panel_state.counter_count == 1
    assert 'drawable_samples' in panel_state.latest_counter_summary
    assert panel_state.backend_count == 1
    assert 'snapshot_renderer' in panel_state.backend_summary
    assert 'le_16ms' in panel_state.backend_latency_summary
    assert 'p50=11.50ms' in panel_state.backend_percentile_summary
    assert 'span_rate=' in panel_state.backend_rolling_summary
    assert 'drawable_samples=9' in panel_state.backend_live_counter_summary
    assert panel_state.timeline_entries
    assert 'Diagnostics timeline' in panel_state.timeline_summary
    assert '[EVENT]' in panel_state.timeline_log_text
    assert '[SPAN]' in panel_state.timeline_log_text
    assert '[COUNTER]' in panel_state.timeline_log_text
    assert '截图能力' in panel_state.recent_log_text
    assert 'worker_failure_projection' in panel_state.recent_log_text
