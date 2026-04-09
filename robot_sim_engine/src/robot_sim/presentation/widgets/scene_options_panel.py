from __future__ import annotations

<<<<<<< HEAD
from robot_sim.presentation.experimental.widgets.scene_options_panel import SceneOptionsPanel


__all__ = ['SceneOptionsPanel']
=======
try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object


class SceneOptionsPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QCheckBox, QFormLayout, QPushButton

        layout = QFormLayout(self)
        self.show_target = QCheckBox()
        self.show_target.setChecked(True)
        self.show_trajectory = QCheckBox()
        self.show_trajectory.setChecked(True)
        self.capture_btn = QPushButton("截图")
        layout.addRow("显示目标", self.show_target)
        layout.addRow("显示轨迹", self.show_trajectory)
        layout.addRow(self.capture_btn)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
