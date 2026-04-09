from __future__ import annotations

from robot_sim.presentation.render_telemetry_state import RenderTelemetryPanelState, build_render_telemetry_panel_state
from robot_sim.presentation.status_panel_state import StatusPanelProjection, build_status_panel_projection


class MainWindowProjectionBindings:
    """Encapsulate shared-state projection and subscription plumbing for the main window.

    The main window still owns widget construction, but subscription wiring and typed
    projection logic live here so render/runtime projections no longer bloat the UI shell.
    """

    def __init__(self, *, runtime, status_panel, diagnostics_panel) -> None:
        self._runtime = runtime
        self._status_panel = status_panel
        self._diagnostics_panel = diagnostics_panel

    def build_status_panel_projection(self) -> StatusPanelProjection:
        """Return the typed status-panel projection from the shared runtime state."""
        return build_status_panel_projection(self._runtime.state)

    def apply_status_panel_projection(self, projection: StatusPanelProjection) -> None:
        """Render a typed status-panel projection into concrete widgets."""
        self._status_panel.set_metrics(**projection.metric_payload)
        render_projector = getattr(self._status_panel, 'set_render_runtime', None)
        if callable(render_projector):
            render_projector(projection.render_runtime)

    def ensure_status_panel_projection_subscription(self, window) -> None:
        """Bind the status panel to the shared-state projection exactly once."""
        if getattr(window, '_status_panel_projection_unsubscribe', None) is not None:
            return
        window._status_panel_projection_unsubscribe = self._runtime.state_store.subscribe_selector(
            build_status_panel_projection,
            self.apply_status_panel_projection,
            emit_current=True,
        )

    def build_render_telemetry_projection(self) -> RenderTelemetryPanelState:
        """Return the typed diagnostics render-telemetry projection from shared state."""
        state = self._runtime.state
        return build_render_telemetry_panel_state(
            state.render_telemetry,
            operation_spans=state.render_operation_spans,
            sampling_counters=state.render_sampling_counters,
            backend_performance=state.render_backend_performance,
        )

    def apply_render_telemetry_projection(self, projection: RenderTelemetryPanelState) -> None:
        """Render a typed diagnostics telemetry projection into concrete widgets."""
        projector = getattr(self._diagnostics_panel, 'set_render_telemetry', None)
        if callable(projector):
            projector(projection)

    def ensure_render_telemetry_subscription(self, window) -> None:
        """Bind the diagnostics panel to the structured render telemetry stream exactly once."""
        if getattr(window, '_render_telemetry_unsubscribe', None) is not None:
            return
        window._render_telemetry_unsubscribe = self._runtime.state_store.subscribe_selector(
            lambda state: build_render_telemetry_panel_state(
                state.render_telemetry,
                operation_spans=state.render_operation_spans,
                sampling_counters=state.render_sampling_counters,
                backend_performance=state.render_backend_performance,
            ),
            self.apply_render_telemetry_projection,
            emit_current=True,
            segment='render',
            snapshot_strategy='identity',
        )
