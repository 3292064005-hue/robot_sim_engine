from __future__ import annotations
from dataclasses import dataclass
from robot_sim.domain.types import FloatArray
from robot_sim.model.pose import Pose

@dataclass(frozen=True)
class FKResult:
    T_list: tuple[FloatArray, ...]
    joint_positions: FloatArray
    ee_pose: Pose
