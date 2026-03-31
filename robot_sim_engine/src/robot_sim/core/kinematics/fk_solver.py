from __future__ import annotations
import numpy as np
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.fk_result import FKResult
from robot_sim.model.pose import Pose
from robot_sim.core.kinematics.dh import dh_transform
from robot_sim.domain.types import FloatArray

class ForwardKinematicsSolver:
    def solve(self, spec: RobotSpec, q: FloatArray) -> FKResult:
        T = spec.base_T.copy()
        T_list = [T.copy()]
        joint_positions = [T[:3, 3].copy()]

        for row, q_i in zip(spec.dh_rows, q):
            T = T @ dh_transform(row, float(q_i))
            T_list.append(T.copy())
            joint_positions.append(T[:3, 3].copy())

        T = T @ spec.tool_T
        pose = Pose.from_matrix(T)
        return FKResult(
            T_list=tuple(T_list),
            joint_positions=np.array(joint_positions, dtype=float),
            ee_pose=pose,
        )
