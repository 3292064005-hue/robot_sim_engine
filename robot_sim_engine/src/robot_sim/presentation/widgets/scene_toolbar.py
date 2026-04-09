from __future__ import annotations

from robot_sim.presentation.qt_runtime import QCheckBox, QHBoxLayout, QPushButton, Signal, QWidget, require_qt_runtime


class SceneToolbar(QWidget):  # pragma: no cover - GUI shell
    fit_requested = Signal()
    clear_path_requested = Signal()
    screenshot_requested = Signal()
    add_obstacle_requested = Signal()
    clear_obstacles_requested = Signal()
    target_axes_toggled = Signal(bool)
    trajectory_toggled = Signal(bool)

    def __init__(self, parent=None):
        require_qt_runtime('SceneToolbar')
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.fit_btn = QPushButton('适配视角')
        self.clear_path_btn = QPushButton('清空轨迹')
        self.screenshot_btn = QPushButton('截图')
        self.add_obstacle_btn = QPushButton('场景编辑')
        self.clear_obstacles_btn = QPushButton('清空场景')
        self.target_axes_chk = QCheckBox('目标坐标轴')
        self.trajectory_chk = QCheckBox('轨迹')
        self.target_axes_chk.setChecked(True)
        self.trajectory_chk.setChecked(True)
        for widget in [
            self.fit_btn,
            self.clear_path_btn,
            self.screenshot_btn,
            self.add_obstacle_btn,
            self.clear_obstacles_btn,
            self.target_axes_chk,
            self.trajectory_chk,
        ]:
            layout.addWidget(widget)
        layout.addStretch(1)
        self.fit_btn.clicked.connect(self.fit_requested.emit)
        self.clear_path_btn.clicked.connect(self.clear_path_requested.emit)
        self.screenshot_btn.clicked.connect(self.screenshot_requested.emit)
        self.add_obstacle_btn.clicked.connect(self.add_obstacle_requested.emit)
        self.clear_obstacles_btn.clicked.connect(self.clear_obstacles_requested.emit)
        self.target_axes_chk.toggled.connect(self.target_axes_toggled.emit)
        self.trajectory_chk.toggled.connect(self.trajectory_toggled.emit)
