from __future__ import annotations

import numpy as np

<<<<<<< HEAD
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec


def rough_reach_radius(spec: RobotSpec) -> float:
    articulated = spec.articulated_model
    articulated.require_serial_tree_execution()
    return float(articulated.rough_reach_radius())


def target_is_certainly_outside_workspace(spec: RobotSpec, target: Pose, *, margin: float = 1.05) -> bool:
    margin_value = float(margin)
    effective_margin = margin_value if margin_value >= 1.0 else 1.0 + max(margin_value, 0.0)
    radius = rough_reach_radius(spec) * effective_margin
    target_position = np.asarray(target.p, dtype=float).reshape(3)
    base_position = np.asarray(spec.articulated_model.base_T[:3, 3], dtype=float).reshape(3)
    return float(np.linalg.norm(target_position - base_position)) > radius
=======
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.pose import Pose


def base_position(spec: RobotSpec) -> np.ndarray:
    return np.asarray(spec.base_T[:3, 3], dtype=float)


def rough_reach_radius(spec: RobotSpec) -> float:
    return float(sum(abs(row.a) + abs(row.d) for row in spec.dh_rows) + np.linalg.norm(spec.tool_T[:3, 3]))


def target_is_certainly_outside_workspace(spec: RobotSpec, target: Pose, *, margin: float = 0.0) -> bool:
    radius = rough_reach_radius(spec)
    distance = float(np.linalg.norm(np.asarray(target.p, dtype=float) - base_position(spec)))
    return distance > radius + float(margin)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
