from __future__ import annotations

import logging
from collections.abc import Iterable

from robot_sim.domain.errors import PlotBackendUnavailableError, RenderOperationError
from robot_sim.model.render_runtime import RenderCapabilityState

try:
    import pyqtgraph as pg
except ImportError:  # pragma: no cover
    pg = None

logger = logging.getLogger(__name__)


class PlotsManager:  # pragma: no cover - GUI shell
    """Thin adapter around the plotting backend used by the presentation layer.

    The manager tolerates missing optional plotting dependencies, but it no longer swallows
    arbitrary runtime errors. Backend setup and projection failures are narrowed to the set of
    exceptions that the GUI shell can reasonably degrade around.
    """

    def __init__(self, plot_widgets: dict[str, object] | None = None):
        self.plot_widgets = plot_widgets or {}
        self.curves: dict[tuple[str, str], object] = {}
        self.cursors: dict[str, object] = {}
        if pg is None:
            self._runtime_state = RenderCapabilityState(capability='plots', status='unsupported', backend='pyqtgraph', reason='backend_dependency_missing', error_code=PlotBackendUnavailableError.default_error_code, message='Plot backend dependency is unavailable.')
        elif not self.plot_widgets:
            self._runtime_state = RenderCapabilityState(capability='plots', status='degraded', backend='pyqtgraph', reason='no_plot_widgets_configured', message='Plot backend is installed but no plot widgets were configured.')
        else:
            self._runtime_state = RenderCapabilityState.available_state('plots', backend='pyqtgraph', reason='plot_widgets_ready', message='Plot backend is active.')
        self._configure_widgets()

    def _configure_widgets(self) -> None:
        if pg is None:
            return
        for key, widget in self.plot_widgets.items():
            try:
                widget.showGrid(x=True, y=True, alpha=0.2)
                widget.setClipToView(True)
                widget.getPlotItem().setMenuEnabled(False)
                widget.setDownsampling(auto=True, mode='peak')
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logger.warning('failed to configure plot widget %s: %s', key, exc)

    def clear(self, plot_key: str) -> None:
        if pg is None:
            return
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return
        widget.clear()
        self.curves = {k: v for k, v in self.curves.items() if k[0] != plot_key}
        self.cursors.pop(plot_key, None)
        try:
            widget.addLegend()
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logger.warning('failed to add legend for plot %s: %s', plot_key, exc)

    def ensure_curve(self, plot_key: str, curve_name: str):
        if pg is None:
            return None
        key = (plot_key, curve_name)
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return None
        if key not in self.curves:
            curve = widget.plot(name=curve_name)
            try:
                curve.setClipToView(True)
                curve.setDownsampling(auto=True, method='peak')
                curve.setSkipFiniteCheck(True)
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logger.debug('curve performance opts unavailable for %s/%s: %s', plot_key, curve_name, exc)
            self.curves[key] = curve
        return self.curves[key]

    def require_backend(self) -> None:
        """Raise a structured error when the optional plotting backend is unavailable.

        Returns:
            None: The method only validates backend availability.

        Raises:
            PlotBackendUnavailableError: If ``pyqtgraph`` is not installed in the active runtime.
        """
        if pg is None:
            raise PlotBackendUnavailableError('plot backend is unavailable')

    def set_curve(self, plot_key: str, curve_name: str, x, y):
        """Set or replace a single named curve.

        Args:
            plot_key: Target plot identifier.
            curve_name: Stable curve name within the plot.
            x: X-axis sample array.
            y: Y-axis sample array.

        Returns:
            None: Updates the configured plot widget in place.

        Raises:
            RenderOperationError: If the backend rejects the provided data payload.
        """
        curve = self.ensure_curve(plot_key, curve_name)
        if curve is None:
            return
        try:
            curve.setData(x=x, y=y, skipFiniteCheck=True)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            raise RenderOperationError(
                'failed to update plot curve',
                metadata={'plot_key': plot_key, 'curve_name': curve_name, 'exception_type': exc.__class__.__name__},
            ) from exc

    def set_curves_batch(self, plot_key: str, curves: Iterable[tuple[str, object, object]], *, clear_first: bool = False) -> None:
        """Set multiple curves on the same plot in one call.

        Args:
            plot_key: Target plot identifier.
            curves: Iterable of ``(curve_name, x, y)`` tuples.
            clear_first: Whether to clear the plot before populating curves.

        Returns:
            None: Updates in-memory curve handles and plot widgets.

        Raises:
            RenderOperationError: Propagates any per-curve backend projection failure.
        """
        if clear_first:
            self.clear(plot_key)
        for curve_name, x, y in curves:
            self.set_curve(plot_key, curve_name, x, y)

    def set_cursor(self, plot_key: str, x_value: float) -> None:
        """Move or create a vertical cursor line on the requested plot.

        Args:
            plot_key: Target plot identifier.
            x_value: X-axis cursor location.

        Returns:
            None: Mutates cursor overlays for the selected plot.

        Raises:
            RenderOperationError: If the plotting backend rejects cursor creation or update.
        """
        if pg is None:
            return
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return
        cursor = self.cursors.get(plot_key)
        try:
            if cursor is None:
                cursor = pg.InfiniteLine(angle=90, movable=False)
                widget.addItem(cursor)
                self.cursors[plot_key] = cursor
            cursor.setValue(float(x_value))
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            raise RenderOperationError(
                'failed to project plot cursor',
                metadata={'plot_key': plot_key, 'exception_type': exc.__class__.__name__},
            ) from exc

    def runtime_state(self) -> RenderCapabilityState:
        """Return the structured runtime status for plot rendering."""
        return self._runtime_state

    def set_cursors_batch(self, cursor_updates: Iterable[tuple[str, float]]) -> None:
        """Update multiple plot cursors in one call.

        Args:
            cursor_updates: Iterable of ``(plot_key, x_value)`` cursor updates.

        Returns:
            None: Updates cursor overlays on the configured plots.

        Raises:
            RenderOperationError: Propagates any per-plot cursor projection failure.
        """
        for plot_key, x_value in cursor_updates:
            self.set_cursor(plot_key, x_value)
