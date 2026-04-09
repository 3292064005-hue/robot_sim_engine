from __future__ import annotations

from pathlib import Path
import os

from robot_sim.app.container import AppContainer
from robot_sim.presentation.assembly import build_presentation_assembly
from robot_sim.presentation.legacy_aliases import MainWindowLegacyAliasMixin
from robot_sim.presentation.main_window_actions import MainWindowActionMixin
from robot_sim.presentation.main_window_tasks import MainWindowTaskMixin
from robot_sim.presentation.main_window_ui import MainWindowUIMixin
from robot_sim.presentation.runtime_bundles import RuntimeServiceBundle, TaskOrchestrationBundle, WorkflowFacadeBundle

try:
    from PySide6.QtWidgets import QApplication, QMainWindow
except Exception as exc:  # pragma: no cover
    raise RuntimeError('PySide6 is required to launch the GUI.') from exc


class MainWindow(QMainWindow, MainWindowLegacyAliasMixin, MainWindowTaskMixin, MainWindowActionMixin, MainWindowUIMixin):  # pragma: no cover - GUI shell
    """Top-level Qt window for the simulator UI.

    Canonical ownership now flows through grouped runtime bundles instead of mutating the
    window instance with dozens of peer attributes. Read-only properties keep the legacy
    façade/coordinator surface stable for mixins, tests, and limited compatibility shims.
    """

    @property
    def runtime_services(self) -> RuntimeServiceBundle:
        return self.window_runtime.runtime_services

    @property
    def workflow_facades(self) -> WorkflowFacadeBundle:
        return self.window_runtime.workflow_facades

    @property
    def task_orchestration(self) -> TaskOrchestrationBundle:
        return self.window_runtime.task_orchestration

    @property
    def runtime_facade(self):
        return self.runtime_services.runtime_facade

    @property
    def metrics_service(self):
        return self.runtime_services.metrics_service

    @property
    def window_cfg(self) -> dict[str, object]:
        return self.runtime_services.window_cfg

    @property
    def robot_facade(self):
        return self.workflow_facades.robot_facade

    @property
    def solver_facade(self):
        return self.workflow_facades.solver_facade

    @property
    def trajectory_facade(self):
        return self.workflow_facades.trajectory_facade

    @property
    def playback_facade(self):
        return self.workflow_facades.playback_facade

    @property
    def benchmark_facade(self):
        return self.workflow_facades.benchmark_facade

    @property
    def export_facade(self):
        return self.workflow_facades.export_facade

    @property
    def threader(self):
        return self.task_orchestration.threader

    @property
    def playback_threader(self):
        return self.task_orchestration.playback_threader

    @property
    def playback_render_scheduler(self):
        return self.task_orchestration.playback_render_scheduler

    @property
    def robot_coordinator(self):
        return self.task_orchestration.robot_coordinator

    @property
    def ik_task_coordinator(self):
        return self.task_orchestration.ik_task_coordinator

    @property
    def trajectory_task_coordinator(self):
        return self.task_orchestration.trajectory_task_coordinator

    @property
    def benchmark_task_coordinator(self):
        return self.task_orchestration.benchmark_task_coordinator

    @property
    def playback_task_coordinator(self):
        return self.task_orchestration.playback_task_coordinator

    @property
    def export_task_coordinator(self):
        return self.task_orchestration.export_task_coordinator

    @property
    def scene_coordinator(self):
        return self.task_orchestration.scene_coordinator

    @property
    def status_coordinator(self):
        return self.task_orchestration.status_coordinator

    def _should_auto_load_robot(self) -> bool:
        """Return whether the window should auto-load the default robot on startup.

        Returns:
            bool: ``True`` during normal GUI runs, ``False`` for explicit test/headless
            smoke environments where offscreen/minimal Qt backends are active.

        Boundary behavior:
            Offscreen/minimal platform plugins are treated as smoke-test environments so
            widget-construction checks do not block on startup robot loading. Operators can
            still load the default robot manually through the existing toolbar action.
        """
        if str(os.environ.get('ROBOT_SIM_SKIP_AUTO_LOAD', '') or '').strip() == '1':
            return False
        app = QApplication.instance()
        platform_name = ''
        if app is not None and hasattr(app, 'platformName'):
            platform_name = str(app.platformName() or '').strip().lower()
        if platform_name in {'offscreen', 'minimal'}:
            return False
        return True

    def __init__(self, project_root: str | Path, *, container: AppContainer) -> None:
        """Create the top-level simulator window.

        Args:
            project_root: Project root used to resolve runtime resources.
            container: Explicitly built dependency container.

        Returns:
            None: Initializes the Qt window from a pre-built presentation assembly.

        Raises:
            ValueError: If ``container`` is not provided.
        """
        super().__init__()
        if container is None:
            raise ValueError('MainWindow requires an explicit application container')
        assembly = build_presentation_assembly(project_root, container=container, window_parent=self)
        self.controller = assembly.controller
        self.window_runtime = assembly.window_runtime
        self.setWindowTitle(str(self.window_cfg.get('title', 'Robot Sim Engine')))

        self._build_ui()
        self._wire_signals()
        self._wire_task_signals()
        self.playback_render_scheduler.flushed.connect(self.project_playback_frame)

        self.resize(int(self.window_cfg.get('width', 1680)), int(self.window_cfg.get('height', 980)))
        if self.robot_facade.robot_entries() and self._should_auto_load_robot():
            self.on_load_robot()
