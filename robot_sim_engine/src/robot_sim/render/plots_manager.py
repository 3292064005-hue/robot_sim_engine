from __future__ import annotations
try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover
    pg = None


class PlotsManager:  # pragma: no cover - GUI shell
    def __init__(self, plot_widgets: dict[str, object] | None = None):
        self.plot_widgets = plot_widgets or {}
        self.curves: dict[tuple[str, str], object] = {}
        self.cursors: dict[str, object] = {}
        self._configure_widgets()

    def _configure_widgets(self) -> None:
        if pg is None:
            return
        for key, widget in self.plot_widgets.items():
            try:
                widget.showGrid(x=True, y=True, alpha=0.2)
                widget.setClipToView(True)
                widget.getPlotItem().setMenuEnabled(False)
            except Exception:
                pass

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
        except Exception:
            pass

    def ensure_curve(self, plot_key: str, curve_name: str):
        if pg is None:
            return None
        key = (plot_key, curve_name)
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return None
        if key not in self.curves:
            self.curves[key] = widget.plot(name=curve_name)
        return self.curves[key]

    def set_curve(self, plot_key: str, curve_name: str, x, y):
        curve = self.ensure_curve(plot_key, curve_name)
        if curve is not None:
            curve.setData(x=x, y=y, skipFiniteCheck=True)

    def set_cursor(self, plot_key: str, x_value: float) -> None:
        if pg is None:
            return
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return
        cursor = self.cursors.get(plot_key)
        if cursor is None:
            cursor = pg.InfiniteLine(angle=90, movable=False)
            widget.addItem(cursor)
            self.cursors[plot_key] = cursor
        cursor.setValue(float(x_value))
