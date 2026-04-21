from __future__ import annotations

import numpy as np

from robot_sim.core.kinematics.execution_adapter import resolve_execution_adapter
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec


def rough_reach_radius(spec: RobotSpec) -> float:
    adapter = resolve_execution_adapter(spec)
    adapter.require_active_path_execution()
    return float(adapter.rough_reach_radius())


def target_is_certainly_outside_workspace(spec: RobotSpec, target: Pose, *, margin: float = 1.05) -> bool:
    margin_value = float(margin)
    effective_margin = margin_value if margin_value >= 1.0 else 1.0 + max(margin_value, 0.0)
    radius = rough_reach_radius(spec) * effective_margin
    target_position = np.asarray(target.p, dtype=float).reshape(3)
    base_position = np.asarray(spec.articulated_model.base_T[:3, 3], dtype=float).reshape(3)
    return float(np.linalg.norm(target_position - base_position)) > radius
