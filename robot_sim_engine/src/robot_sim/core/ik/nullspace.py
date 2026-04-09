from __future__ import annotations
import numpy as np
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.domain.types import FloatArray
from robot_sim.core.kinematics.jacobian_solver import JacobianSolver


def joint_limit_gradient(spec: RobotSpec, q: FloatArray) -> FloatArray:
<<<<<<< HEAD
    articulated = spec.articulated_model
    articulated.require_serial_tree_execution()
    grad = np.zeros_like(q, dtype=float)
    for i, joint in enumerate(articulated.joint_models):
        q_mid = 0.5 * (joint.limit.lower + joint.limit.upper)
        half_range = max(1.0e-9, 0.5 * (joint.limit.upper - joint.limit.lower))
=======
    grad = np.zeros_like(q, dtype=float)
    for i, row in enumerate(spec.dh_rows):
        q_mid = 0.5 * (row.q_min + row.q_max)
        half_range = max(1.0e-9, 0.5 * (row.q_max - row.q_min))
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        grad[i] = -2.0 * (q[i] - q_mid) / (half_range ** 2)
    return grad


def manipulability_gradient(spec: RobotSpec, q: FloatArray, eps: float = 1.0e-5) -> FloatArray:
    jac_solver = JacobianSolver()
    base = jac_solver.geometric(spec, q).manipulability
    grad = np.zeros_like(q, dtype=float)
    for i in range(q.size):
        dq = np.zeros_like(q, dtype=float)
        dq[i] = eps
        plus = jac_solver.geometric(spec, q + dq).manipulability
        minus = jac_solver.geometric(spec, q - dq).manipulability
        if np.isfinite(plus) and np.isfinite(minus):
            grad[i] = (plus - minus) / (2.0 * eps)
        elif np.isfinite(plus):
            grad[i] = (plus - base) / eps
        elif np.isfinite(minus):
            grad[i] = (base - minus) / eps
    return grad


<<<<<<< HEAD
def secondary_objective_gradient(spec: RobotSpec, q: FloatArray, joint_limit_weight: float, manipulability_weight: float) -> FloatArray:
=======
def secondary_objective_gradient(
    spec: RobotSpec,
    q: FloatArray,
    joint_limit_weight: float,
    manipulability_weight: float,
) -> FloatArray:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    grad = np.zeros_like(q, dtype=float)
    if joint_limit_weight > 0.0:
        grad += joint_limit_weight * joint_limit_gradient(spec, q)
    if manipulability_weight > 0.0:
        grad += manipulability_weight * manipulability_gradient(spec, q)
    return grad


def can_use_nullspace(jacobian_cols: int, task_dim: int) -> bool:
    return jacobian_cols > task_dim


def nullspace_projector(J_pinv: FloatArray, J: FloatArray) -> FloatArray:
    n = J.shape[1]
    return np.eye(n, dtype=float) - J_pinv @ J
