from __future__ import annotations
<<<<<<< HEAD

from robot_sim.presentation.qt_runtime import QLabel, QTabWidget, QVBoxLayout, QWidget, require_qt_runtime
=======
try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


class PlotsPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
<<<<<<< HEAD
        require_qt_runtime('PlotsPanel')
        super().__init__(parent)
=======
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QLabel, QTabWidget
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        layout = QVBoxLayout(self)
        self.plot_widgets = {}
        try:
            import pyqtgraph as pg
            self.tabs = QTabWidget()
            for key, title in [
                ("joint_position", "关节角"),
                ("joint_velocity", "关节速度"),
                ("joint_acceleration", "关节加速度"),
                ("ik_error", "IK 误差"),
                ("condition", "条件数/可操作度"),
            ]:
                w = pg.PlotWidget()
                w.addLegend()
                self.plot_widgets[key] = w
                self.tabs.addTab(w, title)
            layout.addWidget(self.tabs)
        except ImportError:
            self.tabs = None
            layout.addWidget(QLabel("pyqtgraph 未安装，当前为占位曲线区。"))
