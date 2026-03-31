from __future__ import annotations
import numpy as np


class SceneController:  # pragma: no cover - GUI shell
    def __init__(self, widget) -> None:
        self.widget = widget
        self._ee_path: list[np.ndarray] = []

    def reset_path(self) -> None:
        self._ee_path.clear()

    def update_fk(self, fk_result, target_pose=None, *, append_path: bool = False) -> None:
        self.widget.set_robot_lines(fk_result.joint_positions)
        if target_pose is not None:
            self.widget.set_target_pose(target_pose)
        ee = np.asarray(fk_result.ee_pose.p, dtype=float)
        self.widget.set_playback_marker(ee)
        if append_path:
            self._ee_path.append(ee)
            if len(self._ee_path) >= 2:
                self.widget.set_trajectory(np.vstack(self._ee_path))

    def set_trajectory_from_fk_samples(self, points: np.ndarray) -> None:
        self._ee_path = [np.asarray(p, dtype=float).copy() for p in np.asarray(points, dtype=float)]
        self.widget.set_trajectory(np.asarray(points, dtype=float))
