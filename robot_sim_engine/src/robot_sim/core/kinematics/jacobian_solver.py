from __future__ import annotations
import numpy as np
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.fk_result import FKResult
from robot_sim.model.jacobian_result import JacobianResult
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.domain.enums import JointType
from robot_sim.core.metrics.condition_number import condition_number
from robot_sim.core.metrics.manipulability import manipulability
from robot_sim.domain.types import FloatArray

class JacobianSolver:
    def __init__(self) -> None:
        self._fk = ForwardKinematicsSolver()

    def geometric(self, spec: RobotSpec, q: FloatArray, fk: FKResult | None = None) -> JacobianResult:
        fk_result = fk if fk is not None else self._fk.solve(spec, q)
        p_n = fk_result.ee_pose.p
        n = spec.dof
        J = np.zeros((6, n), dtype=float)

        for i, row in enumerate(spec.dh_rows):
            T_prev = fk_result.T_list[i]
            z = T_prev[:3, 2]
            p = T_prev[:3, 3]
            if row.joint_type is JointType.REVOLUTE:
                J[:3, i] = np.cross(z, p_n - p)
                J[3:, i] = z
            else:
                J[:3, i] = z
                J[3:, i] = 0.0

        return JacobianResult(
            J=J,
            condition_number=condition_number(J),
            manipulability=manipulability(J),
        )
