from __future__ import annotations
from robot_sim.application.dto import IKRequest
from robot_sim.domain.enums import IKSolverMode
from robot_sim.core.ik.pseudo_inverse import PseudoInverseIKSolver
from robot_sim.core.ik.dls import DLSIKSolver


class RunIKUseCase:
    def __init__(self) -> None:
        self._solvers = {
            IKSolverMode.PINV: PseudoInverseIKSolver(),
            IKSolverMode.DLS: DLSIKSolver(),
        }

    def execute(self, req: IKRequest, cancel_flag=None, progress_cb=None):
        solver = self._solvers[req.config.mode]
        return solver.solve(
            req.spec,
            req.target,
            req.q0,
            req.config,
            cancel_flag=cancel_flag,
            progress_cb=progress_cb,
        )
