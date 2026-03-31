from __future__ import annotations
from time import perf_counter
from typing import Callable
import numpy as np

from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.ik_result import IKIterationLog, IKResult
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.kinematics.jacobian_solver import JacobianSolver
from robot_sim.core.math.linalg import clip_norm, damped_least_squares
from robot_sim.core.math.so3 import rotation_error
from robot_sim.core.ik.validators import clip_to_joint_limits
from robot_sim.core.ik.nullspace import (
    can_use_nullspace,
    nullspace_projector,
    secondary_objective_gradient,
)
from robot_sim.core.ik.convergence import has_converged
from robot_sim.domain.enums import IKSolverMode
from robot_sim.domain.types import FloatArray


class IterativeIKSolverBase:
    def __init__(self) -> None:
        self._fk = ForwardKinematicsSolver()
        self._jac = JacobianSolver()

    def _inverse(self, J: FloatArray, config: IKConfig) -> FloatArray:
        raise NotImplementedError

    def solve(
        self,
        spec: RobotSpec,
        target: Pose,
        q0: FloatArray,
        config: IKConfig,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[IKIterationLog], None] | None = None,
    ) -> IKResult:
        q = q0.astype(float).copy()
        logs: list[IKIterationLog] = []
        cancelled = cancel_flag or (lambda: False)
        t0 = perf_counter()

        for k in range(config.max_iters):
            if cancelled():
                return IKResult(False, q, tuple(logs), "cancelled")

            fk = self._fk.solve(spec, q)
            jac = self._jac.geometric(spec, q, fk=fk)

            pos_err = target.p - fk.ee_pose.p
            ori_err = rotation_error(target.R, fk.ee_pose.R)
            pos_norm = float(np.linalg.norm(pos_err))
            ori_norm = float(np.linalg.norm(ori_err))

            if config.position_only:
                err = pos_err
                J_task = jac.J[:3, :]
                ori_for_convergence = 0.0
            else:
                err = np.concatenate([pos_err, config.orientation_weight * ori_err])
                J_task = np.vstack([jac.J[:3, :], config.orientation_weight * jac.J[3:, :]])
                ori_for_convergence = ori_norm

            effective_mode = config.mode.value
            if (
                config.fallback_to_dls_when_singular
                and config.mode is IKSolverMode.PINV
                and jac.condition_number >= config.singularity_cond_threshold
            ):
                J_inv = damped_least_squares(J_task, config.damping_lambda)
                effective_mode = IKSolverMode.DLS.value
            else:
                J_inv = self._inverse(J_task, config)

            dq = J_inv @ err

            task_dim = J_task.shape[0]
            if config.enable_nullspace and can_use_nullspace(J_task.shape[1], task_dim):
                grad = secondary_objective_gradient(
                    spec,
                    q,
                    joint_limit_weight=config.joint_limit_weight,
                    manipulability_weight=config.manipulability_weight,
                )
                dq += nullspace_projector(J_inv, J_task) @ grad

            dq = clip_norm(dq, max_norm=config.max_step_norm)
            q_next = clip_to_joint_limits(spec, q + config.step_scale * dq)

            log = IKIterationLog(
                iter_idx=k,
                pos_err_norm=pos_norm,
                ori_err_norm=ori_norm,
                cond_number=jac.condition_number,
                manipulability=jac.manipulability,
                dq_norm=float(np.linalg.norm(dq)),
                elapsed_ms=(perf_counter() - t0) * 1000.0,
                effective_mode=effective_mode,
            )
            logs.append(log)
            if progress_cb is not None:
                progress_cb(log)

            if has_converged(pos_norm, ori_for_convergence, config.pos_tol, config.ori_tol):
                return IKResult(True, q, tuple(logs), "converged")

            q = q_next

        return IKResult(False, q, tuple(logs), "max iterations exceeded")
