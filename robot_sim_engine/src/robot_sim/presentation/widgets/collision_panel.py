from __future__ import annotations
<<<<<<< HEAD

from robot_sim.presentation.experimental.widgets.collision_panel import CollisionPanel


__all__ = ['CollisionPanel']
=======
try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class CollisionPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QFormLayout, QLabel
        layout = QFormLayout(self)
        self.self_collision = QLabel('未知')
        self.environment_collision = QLabel('未知')
        layout.addRow('自碰撞预警', self.self_collision)
        layout.addRow('环境碰撞预警', self.environment_collision)

    def set_values(self, *, self_collision: str | None = None, environment_collision: str | None = None) -> None:
        if self_collision is not None:
            self.self_collision.setText(str(self_collision))
        if environment_collision is not None:
            self.environment_collision.setText(str(environment_collision))
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
