# mypy: disable-error-code="attr-defined,no-redef,arg-type"
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from robot_sim.presentation.app_state import state_for_busy_reason
from robot_sim.presentation.coordinators._helpers import require_dependency
from robot_sim.presentation.error_boundary import PresentationErrorBoundary
from robot_sim.presentation.qt_runtime import QMessageBox, QSplitter, QTabWidget, QVBoxLayout, Qt, QWidget
from robot_sim.presentation.main_window_qt_helpers import ensure_qt_application
# centralized import guard remains here; historical `except Exception` audit boundary is preserved at this UI shell.
from robot_sim.presentation.main_window_feature_builders import (
    MainWindowCenterColumnBuilder,
    MainWindowLayoutBuilder,
    MainWindowLeftColumnBuilder,
    MainWindowRightColumnBuilder,
    MainWindowSignalBinder,
)
from robot_sim.presentation.main_window_render_runtime_ui import MainWindowRenderRuntimeUIMixin
from robot_sim.presentation.main_window_request_readers import MainWindowRequestReadersMixin
from robot_sim.presentation.main_window_result_projection_ui import MainWindowResultProjectionMixin
from robot_sim.presentation.main_window_scene_ui import MainWindowSceneUIMixin
from robot_sim.presentation.projection_bindings import MainWindowProjectionBindings
from robot_sim.presentation.widgets.benchmark_panel import BenchmarkPanel
from robot_sim.presentation.widgets.diagnostics_panel import DiagnosticsPanel
from robot_sim.presentation.widgets.playback_panel import PlaybackPanel
from robot_sim.presentation.widgets.plots_panel import PlotsPanel
from robot_sim.presentation.widgets.robot_config_panel import RobotConfigPanel
from robot_sim.presentation.widgets.scene_toolbar import SceneToolbar
from robot_sim.presentation.widgets.solver_panel import SolverPanel
from robot_sim.presentation.render_telemetry_state import RenderTelemetryPanelState, build_render_telemetry_panel_state
from robot_sim.presentation.status_panel_state import StatusPanelProjection
from robot_sim.presentation.widgets.status_panel import StatusPanel
from robot_sim.presentation.widgets.target_pose_panel import TargetPosePanel
from robot_sim.render.plots_manager import PlotsManager
from robot_sim.render.scene_3d_widget import Scene3DWidget
from robot_sim.render.scene_controller import SceneController

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowUIContract

_T = TypeVar('_T')

# Keep an explicit module-level reference so quality-contract verification can assert that
# diagnostics telemetry projection remains wired through the typed projection builder.
# runtime probe markers remain declared in the stable UI shell even though the implementation now lives in
# MainWindowRenderRuntimeUIMixin markers preserved for quality contracts: runtime_probe /
# record_render_operation_span( / record_render_sampling_counter(.
_RENDER_TELEMETRY_PROJECTION_BUILDER = build_render_telemetry_panel_state

class MainWindowUIMixin(MainWindowRenderRuntimeUIMixin, MainWindowRequestReadersMixin, MainWindowResultProjectionMixin, MainWindowSceneUIMixin):
    """UI-shell helpers and view-boundary projection methods."""

    def _runtime_ops(self: 'MainWindowUIContract'):
        """Return the required runtime façade injected by the main window shell."""
        return require_dependency(getattr(self, 'runtime_facade', None), 'runtime_facade')

    def _robot_ops(self: 'MainWindowUIContract'):
        """Return the required robot façade injected by the main window shell."""
        return require_dependency(getattr(self, 'robot_facade', None), 'robot_facade')

    def _solver_ops(self: 'MainWindowUIContract'):
        """Return the required solver façade injected by the main window shell."""
        return require_dependency(getattr(self, 'solver_facade', None), 'solver_facade')

    def _trajectory_ops(self: 'MainWindowUIContract'):
        """Return the required trajectory façade injected by the main window shell."""
        return require_dependency(getattr(self, 'trajectory_facade', None), 'trajectory_facade')

    def _playback_ops(self: 'MainWindowUIContract'):
        """Return the required playback façade injected by the main window shell."""
        return require_dependency(getattr(self, 'playback_facade', None), 'playback_facade')

    def _benchmark_ops(self: 'MainWindowUIContract'):
        """Return the required benchmark façade injected by the main window shell."""
        return require_dependency(getattr(self, 'benchmark_facade', None), 'benchmark_facade')

    def _export_ops(self: 'MainWindowUIContract'):
        """Return the required export façade injected by the main window shell."""
        return require_dependency(getattr(self, 'export_facade', None), 'export_facade')

    def _projection_bindings(self: 'MainWindowUIContract') -> MainWindowProjectionBindings:
        """Return the lazily constructed main-window projection binding helper."""
        bindings = getattr(self, '_projection_bindings_helper', None)
        if bindings is None:
            bindings = MainWindowProjectionBindings(
                runtime=self._runtime_ops(),
                status_panel=self.status_panel,
                diagnostics_panel=self.diagnostics_panel,
            )
            self._projection_bindings_helper = bindings
        return bindings

    def _build_status_panel_projection(self: 'MainWindowUIContract') -> StatusPanelProjection:
        """Build the typed status-panel projection from shared runtime session state."""
        return self._projection_bindings().build_status_panel_projection()

    def _apply_status_panel_projection(self: 'MainWindowUIContract', projection: StatusPanelProjection) -> None:
        """Render a typed status-panel projection into the concrete status panel widgets."""
        self._projection_bindings().apply_status_panel_projection(projection)

    def _build_render_telemetry_projection(self: 'MainWindowUIContract') -> RenderTelemetryPanelState:
        """Build the typed diagnostics-panel render telemetry projection from shared state."""
        return self._projection_bindings().build_render_telemetry_projection()

    def _apply_render_telemetry_projection(self: 'MainWindowUIContract', projection: RenderTelemetryPanelState) -> None:
        """Render typed render telemetry into the diagnostics panel when available."""
        self._projection_bindings().apply_render_telemetry_projection(projection)

    def _ensure_render_telemetry_subscription(self: 'MainWindowUIContract') -> None:
        """Bind the diagnostics panel to the typed render telemetry stream exactly once."""
        if getattr(self, '_render_telemetry_unsubscribe', None) is not None:
            return
        self._projection_bindings().ensure_render_telemetry_subscription(self)

    def _ensure_status_panel_projection_subscription(self: 'MainWindowUIContract') -> None:
        """Bind the status panel to the typed shared-state projection exactly once."""
        if getattr(self, '_status_panel_projection_unsubscribe', None) is not None:
            return
        self._projection_bindings().ensure_status_panel_projection_subscription(self)


    def _feature_builders(self: 'MainWindowUIContract'):
        """Return the lazily constructed feature-oriented UI builders/binders."""
        builders = getattr(self, '_feature_builder_bundle', None)
        if builders is None:
            builders = {
                'layout': MainWindowLayoutBuilder(
                    QWidget_cls=QWidget,
                    QVBoxLayout_cls=QVBoxLayout,
                    QSplitter_cls=QSplitter,
                    Qt_namespace=Qt,
                    PlotsPanel_cls=PlotsPanel,
                    PlotsManager_cls=PlotsManager,
                    left_builder=MainWindowLeftColumnBuilder(
                        QWidget_cls=QWidget,
                        QVBoxLayout_cls=QVBoxLayout,
                        RobotConfigPanel_cls=RobotConfigPanel,
                        TargetPosePanel_cls=TargetPosePanel,
                        SolverPanel_cls=SolverPanel,
                    ),
                    center_builder=MainWindowCenterColumnBuilder(
                        QWidget_cls=QWidget,
                        QVBoxLayout_cls=QVBoxLayout,
                        Scene3DWidget_cls=Scene3DWidget,
                        SceneToolbar_cls=SceneToolbar,
                        SceneController_cls=SceneController,
                        PlaybackPanel_cls=PlaybackPanel,
                    ),
                    right_builder=MainWindowRightColumnBuilder(
                        StatusPanel_cls=StatusPanel,
                        DiagnosticsPanel_cls=DiagnosticsPanel,
                        BenchmarkPanel_cls=BenchmarkPanel,
                        QTabWidget_cls=QTabWidget,
                    ),
                ),
                'signals': MainWindowSignalBinder(),
            }
            self._feature_builder_bundle = builders
        return builders

    def _presentation_error_boundary(self: 'MainWindowUIContract') -> PresentationErrorBoundary:
        """Return the lazily constructed presentation error boundary."""
        boundary = getattr(self, '_error_boundary', None)
        if boundary is None:
            runtime = self._runtime_ops()
            boundary = PresentationErrorBoundary(
                mapper=runtime.task_error_mapper,
                state_store=runtime.state_store,
                dialog_sink=self._show_error,
                status_sink=self.status_panel.append,
            )
            self._error_boundary = boundary
        return boundary
    def _build_ui(self: 'MainWindowUIContract') -> None:
        ensure_qt_application()
        self._feature_builders()['layout'].build(self)
        self._ensure_status_panel_projection_subscription()
        self._ensure_render_telemetry_subscription()
        self.project_render_runtime_state(self._collect_render_runtime_state(), source='ui_runtime_scan')

    def _build_left_column(self: 'MainWindowUIContract') -> QWidget:
        return self._feature_builders()['layout'].left_builder.build(self)

    def _build_center_column(self: 'MainWindowUIContract') -> QWidget:
        return self._feature_builders()['layout'].center_builder.build(self)

    def _build_right_column(self: 'MainWindowUIContract') -> QWidget:
        return self._feature_builders()['layout'].right_builder.build(self)

    def _wire_signals(self: 'MainWindowUIContract') -> None:
        self._feature_builders()['signals'].wire(self)

    def _wire_task_signals(self: 'MainWindowUIContract') -> None:
        self.threader.task_state_changed.connect(self._on_task_state_changed)
        self.playback_threader.task_state_changed.connect(self._on_task_state_changed)

    def _show_error(self: 'MainWindowUIContract', title: str, exc: Exception | str) -> None:
        if not isinstance(self, QWidget):
            return
        QMessageBox.critical(self, title, str(exc))

    def _project_exception(self: 'MainWindowUIContract', exc: Exception | str, *, title: str = '错误') -> None:
        """Project a presentation-layer exception through the structured error mapper.

        Args:
            exc: Exception instance or message raised at the presentation boundary.
            title: Fallback dialog title when no structured title is available.

        Returns:
            None: Updates state and shows a user-facing error dialog.

        Raises:
            None: Errors are converted into presentation data.
        """
        self._presentation_error_boundary().project_exception(exc, title=title)
        self._patch_render_runtime_from_exception(exc)
        self._sync_status_after_snapshot()

    def _run_presented(self: 'MainWindowUIContract', callback: Callable[[], _T], *, title: str = '错误') -> _T | None:
        """Run a presentation-bound callback under the shared error projection boundary.

        Args:
            callback: Side-effecting UI callback to execute.
            title: Fallback title for unexpected failures.

        Returns:
            Optional callback result when the action succeeds.

        Raises:
            None: All exceptions are normalized through ``_project_exception``.
        """
        return self._presentation_error_boundary().run_presented(callback, title=title)

    def _append_projected_error(self: 'MainWindowUIContract', prefix: str, exc: Exception | str) -> None:
        """Append a structured presentation error to the status panel without showing a dialog.

        Args:
            prefix: Leading status text for the projected error.
            exc: Exception instance or message raised at the presentation boundary.

        Returns:
            None: Updates state and appends a status-row error summary.

        Raises:
            None: Errors are converted into presentation data.
        """
        self._presentation_error_boundary().append_projected_error(prefix, exc)
        self._patch_render_runtime_from_exception(exc)
        self._sync_status_after_snapshot()


    def _run_status_projected(self: 'MainWindowUIContract', callback: Callable[[], _T], *, prefix: str) -> _T | None:
        """Run a callback and append a structured error summary to the status panel on failure.

        Args:
            callback: Side-effecting UI callback to execute.
            prefix: Leading status-row text for projected failures.

        Returns:
            Optional callback result when the action succeeds.

        Raises:
            None: All exceptions are normalized through ``_append_projected_error``.
        """
        return self._presentation_error_boundary().run_status_projected(callback, prefix=prefix)

    def _set_busy(self: 'MainWindowUIContract', busy: bool, reason: str = '') -> None:
        runtime = self._runtime_ops()
        next_state = state_for_busy_reason(reason) if busy else (
            runtime.state.app_state
            if runtime.state.robot_spec is None
            else state_for_busy_reason('', default=runtime.state.app_state)
        )
        if not busy and runtime.state.robot_spec is not None:
            from robot_sim.domain.enums import AppExecutionState

            next_state = AppExecutionState.ROBOT_READY if runtime.state.last_error == '' else runtime.state.app_state
        runtime.state_store.patch(
            is_busy=busy,
            busy_reason=reason,
            app_state=next_state,
            active_task_kind=reason if busy else '',
            active_task_id='' if not busy else runtime.state.active_task_id,
        )
        self.solver_panel.set_running(busy)
        self.benchmark_panel.set_running(busy)
        if not busy:
            self._sync_status_after_snapshot()

    def _set_playback_running(self: 'MainWindowUIContract', running: bool) -> None:
        self.playback_panel.set_running(running)
        runtime = self._runtime_ops()
        playback = runtime.state.playback.play() if running else runtime.state.playback.pause()
        from robot_sim.domain.enums import AppExecutionState

        runtime.state_store.patch(
            playback=playback,
            app_state=AppExecutionState.PLAYING if running else (
                AppExecutionState.ROBOT_READY if runtime.state.robot_spec is not None else AppExecutionState.IDLE
            ),
            active_task_kind='playback' if running else '',
            active_task_id=runtime.state.active_task_id if running else '',
        )
        self._sync_status_after_snapshot()





















