from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowUIContract


def _append_placeholder(container: Any, widget: Any) -> None:
    if hasattr(container, 'widgets') and isinstance(getattr(container, 'widgets'), list):
        container.widgets.append(widget)
    elif hasattr(container, 'children') and isinstance(getattr(container, 'children'), list):
        container.children.append(widget)


def _safe_add_widget(container: Any, widget: Any) -> None:
    try:
        container.addWidget(widget)
    except TypeError:
        _append_placeholder(container, widget)


def _safe_add_tab(container: Any, widget: Any, label: str) -> None:
    try:
        container.addTab(widget, label)
    except TypeError:
        if hasattr(container, 'tabs') and isinstance(getattr(container, 'tabs'), list):
            container.tabs.append((widget, label))


@dataclass(frozen=True)
class MainWindowLeftColumnBuilder:
    """Builder for the robot/solver feature column on the main window."""

    QWidget_cls: Any
    QVBoxLayout_cls: Any
    RobotConfigPanel_cls: Any
    TargetPosePanel_cls: Any
    SolverPanel_cls: Any

    def build(self, window: 'MainWindowUIContract'):
        left = self.QWidget_cls()
        left_layout = self.QVBoxLayout_cls(left)
        robot_ops = window._robot_ops()
        solver_ops = window._solver_ops()
        trajectory_ops = window._trajectory_ops()
        importer_entries = robot_ops.importer_entries() if hasattr(robot_ops, 'importer_entries') else ()
        window.robot_panel = self.RobotConfigPanel_cls(robot_ops.robot_entries(), importer_entries=importer_entries)
        window.target_panel = self.TargetPosePanel_cls()
        window.solver_panel = self.SolverPanel_cls()
        window.solver_panel.apply_defaults(solver_ops.solver_defaults())
        window.solver_panel.apply_trajectory_defaults(trajectory_ops.trajectory_defaults())
        _safe_add_widget(left_layout, window.robot_panel)
        _safe_add_widget(left_layout, window.target_panel)
        _safe_add_widget(left_layout, window.solver_panel)
        return left


@dataclass(frozen=True)
class MainWindowCenterColumnBuilder:
    """Builder for the scene/playback feature column on the main window."""

    QWidget_cls: Any
    QVBoxLayout_cls: Any
    Scene3DWidget_cls: Any
    SceneToolbar_cls: Any
    SceneController_cls: Any
    PlaybackPanel_cls: Any

    def build(self, window: 'MainWindowUIContract'):
        center = self.QWidget_cls()
        center_layout = self.QVBoxLayout_cls(center)
        window.scene_widget = self.Scene3DWidget_cls()
        window.scene_toolbar = self.SceneToolbar_cls()
        window.scene_controller = self.SceneController_cls(window.scene_widget)
        window.playback_panel = self.PlaybackPanel_cls()
        _safe_add_widget(center_layout, window.scene_toolbar)
        _safe_add_widget(center_layout, window.scene_widget)
        _safe_add_widget(center_layout, window.playback_panel)
        return center


@dataclass(frozen=True)
class MainWindowRightColumnBuilder:
    """Builder for the status/diagnostics/benchmark feature tabs."""

    StatusPanel_cls: Any
    DiagnosticsPanel_cls: Any
    BenchmarkPanel_cls: Any
    QTabWidget_cls: Any

    def build(self, window: 'MainWindowUIContract'):
        window.status_panel = self.StatusPanel_cls()
        window.diagnostics_panel = self.DiagnosticsPanel_cls()
        window.benchmark_panel = self.BenchmarkPanel_cls()
        window.right_tabs = self.QTabWidget_cls()
        _safe_add_tab(window.right_tabs, window.status_panel, '状态')
        _safe_add_tab(window.right_tabs, window.diagnostics_panel, '诊断')
        _safe_add_tab(window.right_tabs, window.benchmark_panel, 'Benchmark')
        return window.right_tabs


def _window_cfg(window: 'MainWindowUIContract') -> dict[str, object]:
    runtime_services = getattr(window, 'runtime_services', None)
    if runtime_services is not None and hasattr(runtime_services, 'window_cfg'):
        return dict(getattr(runtime_services, 'window_cfg') or {})
    return dict(getattr(window, 'window_cfg', {}) or {})

@dataclass(frozen=True)
class MainWindowLayoutBuilder:
    """Feature-oriented main-window layout builder.

    The builder composes the left/center/right feature columns and the plots strip while
    keeping the main window shell focused on orchestration instead of widget creation.
    """

    QWidget_cls: Any
    QVBoxLayout_cls: Any
    QSplitter_cls: Any
    Qt_namespace: Any
    PlotsPanel_cls: Any
    PlotsManager_cls: Any
    left_builder: MainWindowLeftColumnBuilder
    center_builder: MainWindowCenterColumnBuilder
    right_builder: MainWindowRightColumnBuilder

    def build(self, window: 'MainWindowUIContract') -> None:
        central = self.QWidget_cls()
        window.setCentralWidget(central)
        root_layout = self.QVBoxLayout_cls(central)

        top_split = self.QSplitter_cls(self.Qt_namespace.Horizontal)
        _safe_add_widget(top_split, self.left_builder.build(window))
        _safe_add_widget(top_split, self.center_builder.build(window))
        _safe_add_widget(top_split, self.right_builder.build(window))
        top_split.setSizes([int(v) for v in _window_cfg(window).get('splitter_sizes', [420, 820, 360])])

        window.plots_panel = self.PlotsPanel_cls()
        window.plots_manager = self.PlotsManager_cls(getattr(window.plots_panel, 'plot_widgets', None))

        v_split = self.QSplitter_cls(self.Qt_namespace.Vertical)
        _safe_add_widget(v_split, top_split)
        _safe_add_widget(v_split, window.plots_panel)
        v_split.setSizes([int(v) for v in _window_cfg(window).get('vertical_splitter_sizes', [700, 260])])
        _safe_add_widget(root_layout, v_split)


class MainWindowSignalBinder:
    """Centralized signal wiring for the feature-built main window shell."""

    def wire(self, window: 'MainWindowUIContract') -> None:
        window.robot_panel.load_button.clicked.connect(window.on_load_robot)
        if hasattr(window.robot_panel, 'import_button'):
            window.robot_panel.import_button.clicked.connect(window.on_import_robot)
        window.robot_panel.save_button.clicked.connect(window.on_save_robot)
        window.target_panel.fill_current_btn.clicked.connect(window.on_fill_current_pose)
        window.solver_panel.run_fk_btn.clicked.connect(window.on_run_fk)
        window.solver_panel.run_ik_btn.clicked.connect(window.on_run_ik)
        window.solver_panel.cancel_btn.clicked.connect(window.on_cancel_ik)
        window.solver_panel.plan_btn.clicked.connect(window.on_plan)
        window.playback_panel.play_btn.clicked.connect(window.on_play)
        window.playback_panel.pause_btn.clicked.connect(window.on_pause)
        window.playback_panel.stop_btn.clicked.connect(window.on_stop_playback)
        window.playback_panel.step_btn.clicked.connect(window.on_step)
        window.playback_panel.slider.valueChanged.connect(window.on_seek_frame)
        window.playback_panel.speed.valueChanged.connect(window.on_playback_speed_changed)
        window.playback_panel.loop.toggled.connect(window.on_playback_loop_changed)
        window.playback_panel.export_btn.clicked.connect(window.on_export_trajectory_bundle)
        window.playback_panel.session_btn.clicked.connect(window.on_export_session)
        window.playback_panel.package_btn.clicked.connect(window.on_export_package)
        window.scene_toolbar.fit_requested.connect(window.on_fit_scene)
        window.scene_toolbar.clear_path_requested.connect(window.on_clear_scene_path)
        window.scene_toolbar.screenshot_requested.connect(window.on_capture_scene)
        window.scene_toolbar.add_obstacle_requested.connect(window.on_add_scene_obstacle)
        window.scene_toolbar.clear_obstacles_requested.connect(window.on_clear_scene_obstacles)
        window.scene_toolbar.target_axes_toggled.connect(window.scene_widget.set_target_axes_visible)
        window.scene_toolbar.trajectory_toggled.connect(window.scene_widget.set_trajectory_visible)
        window.benchmark_panel.run_btn.clicked.connect(window.on_run_benchmark)
        window.benchmark_panel.export_btn.clicked.connect(window.on_export_benchmark)
