from __future__ import annotations

import numpy as np

from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.metrics.condition_number import condition_number
from robot_sim.core.metrics.manipulability import manipulability
from robot_sim.domain.enums import JointType, ReferenceFrame
from robot_sim.domain.types import FloatArray
from robot_sim.model.fk_result import FKResult
from robot_sim.model.jacobian_result import JacobianResult
from robot_sim.model.robot_spec import RobotSpec


class JacobianSolver:
    def __init__(self) -> None:
        self._fk = ForwardKinematicsSolver()

    def _geometric_world(self, spec: RobotSpec, q: FloatArray, fk_result: FKResult) -> np.ndarray:
        articulated = spec.articulated_model
        articulated.require_serial_tree_execution()
        p_n = np.asarray(fk_result.ee_pose.p, dtype=float)
        J = np.zeros((6, articulated.dof), dtype=float)
        for i, (joint, (axis, origin)) in enumerate(zip(articulated.joint_models, articulated.world_joint_axes_origins(q))):
            z = np.asarray(axis, dtype=float)
            p = np.asarray(origin, dtype=float)
            if joint.joint_type is JointType.REVOLUTE:
                J[:3, i] = np.cross(z, p_n - p)
                J[3:, i] = z
            else:
                J[:3, i] = z
                J[3:, i] = 0.0
        return J

    def geometric(self, spec: RobotSpec, q: FloatArray, fk: FKResult | None = None, *, reference_frame: ReferenceFrame = ReferenceFrame.WORLD) -> JacobianResult:
        fk_result = fk if fk is not None else self._fk.solve(spec, q)
        J_world = self._geometric_world(spec, q, fk_result)
        if reference_frame is ReferenceFrame.LOCAL:
            R = np.asarray(fk_result.ee_pose.R, dtype=float)
            adj = np.block([[R.T, np.zeros((3, 3), dtype=float)], [np.zeros((3, 3), dtype=float), R.T]])
            J = adj @ J_world
        elif reference_frame in {ReferenceFrame.WORLD, ReferenceFrame.BASE}:
            J = J_world
        else:
            raise ValueError(f'unsupported Jacobian reference frame: {reference_frame}')
        return JacobianResult(J=J, condition_number=condition_number(J), manipulability=manipulability(J), reference_frame=reference_frame)

    def finite_difference(self, spec: RobotSpec, q: FloatArray, *, eps: float = 1.0e-7, reference_frame: ReferenceFrame = ReferenceFrame.WORLD) -> JacobianResult:
        articulated = spec.articulated_model
        articulated.require_serial_tree_execution()
        q = np.asarray(q, dtype=float)
        fk = self._fk.solve(spec, q)
        base_pos = np.asarray(fk.ee_pose.p, dtype=float)
        base_rot = np.asarray(fk.ee_pose.R, dtype=float)
        J = np.zeros((6, articulated.dof), dtype=float)
        for i in range(articulated.dof):
            q_plus = q.copy()
            q_plus[i] += eps
            fk_plus = self._fk.solve(spec, q_plus)
            p_plus = np.asarray(fk_plus.ee_pose.p, dtype=float)
            R_plus = np.asarray(fk_plus.ee_pose.R, dtype=float)
            J[:3, i] = (p_plus - base_pos) / eps
            dR = R_plus @ base_rot.T
            rotvec = np.array([
                dR[2, 1] - dR[1, 2],
                dR[0, 2] - dR[2, 0],
                dR[1, 0] - dR[0, 1],
            ], dtype=float) * 0.5 / max(eps, 1.0e-12)
            J[3:, i] = rotvec
        if reference_frame is ReferenceFrame.LOCAL:
            R = np.asarray(fk.ee_pose.R, dtype=float)
            adj = np.block([[R.T, np.zeros((3, 3), dtype=float)], [np.zeros((3, 3), dtype=float), R.T]])
            J = adj @ J
        return JacobianResult(J=J, condition_number=condition_number(J), manipulability=manipulability(J), reference_frame=reference_frame)
