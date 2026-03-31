from __future__ import annotations
from robot_sim.core.ik._iterative_solver import IterativeIKSolverBase
from robot_sim.core.math.linalg import pseudo_inverse_svd
from robot_sim.model.solver_config import IKConfig
from robot_sim.domain.types import FloatArray

class PseudoInverseIKSolver(IterativeIKSolverBase):
    def _inverse(self, J: FloatArray, config: IKConfig) -> FloatArray:
        return pseudo_inverse_svd(J)
