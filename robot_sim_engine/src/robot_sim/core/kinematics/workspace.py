from __future__ import annotations
import numpy as np
from robot_sim.model.robot_spec import RobotSpec

def rough_reach_radius(spec: RobotSpec) -> float:
    return float(sum(abs(row.a) + abs(row.d) for row in spec.dh_rows) + np.linalg.norm(spec.tool_T[:3, 3]))
