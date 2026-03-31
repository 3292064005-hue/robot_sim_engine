from __future__ import annotations
import numpy as np
from robot_sim.render.actor_manager import ActorManager

try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class Scene3DWidget(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plotter = None
        self.actor_manager = ActorManager()
        self._trajectory_points: np.ndarray | None = None
        try:
            from PySide6.QtWidgets import QVBoxLayout, QLabel
            layout = QVBoxLayout(self)
            try:
                from pyvistaqt import QtInteractor
                self.plotter = QtInteractor(self)
                layout.addWidget(self.plotter.interactor)
                self.plotter.set_background("white")
                self.plotter.add_axes()
                self.plotter.add_text("Robot Sim Engine", font_size=10)
            except Exception as exc:
                label = QLabel(
                    "3D 视图依赖未安装或初始化失败，当前为占位视图。\n"
                    "请在项目目录执行: pip install -e .[gui]\n"
                    f"详细信息: {exc.__class__.__name__}: {exc}"
                )
                label.setWordWrap(True)
                layout.addWidget(label)
        except Exception:
            self.plotter = None

    def _update_mesh(self, name: str, mesh, **kwargs) -> None:
        if self.plotter is None:
            return
        actor = self.actor_manager.get(name)
        if actor is None:
            actor = self.plotter.add_mesh(mesh, **kwargs)
            self.actor_manager.set(name, actor)
        else:
            mapper = actor.GetMapper()
            if mapper is not None:
                mapper.SetInputData(mesh)

    def set_robot_lines(self, points: np.ndarray) -> None:
        if self.plotter is None:
            return
        if len(points) < 2:
            return
        import pyvista as pv
        poly = pv.lines_from_points(points)
        cloud = pv.PolyData(points)
        self._update_mesh("robot_lines", poly, line_width=5)
        self._update_mesh("robot_joints", cloud, point_size=12, render_points_as_spheres=True)
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()

    def set_target_pose(self, pose) -> None:
        if self.plotter is None:
            return
        import pyvista as pv
        marker = pv.PolyData(np.asarray([pose.p], dtype=float))
        self._update_mesh("target_point", marker, point_size=18, render_points_as_spheres=True)
        self.plotter.render()

    def set_trajectory(self, points: np.ndarray) -> None:
        if self.plotter is None or points is None or len(points) < 2:
            return
        import pyvista as pv
        self._trajectory_points = np.asarray(points, dtype=float).copy()
        poly = pv.lines_from_points(self._trajectory_points)
        self._update_mesh("trajectory", poly, line_width=3)
        self.plotter.render()

    def set_playback_marker(self, point: np.ndarray) -> None:
        if self.plotter is None:
            return
        import pyvista as pv
        marker = pv.PolyData(np.asarray([point], dtype=float))
        self._update_mesh("playback_marker", marker, point_size=15, render_points_as_spheres=True)
        self.plotter.render()
