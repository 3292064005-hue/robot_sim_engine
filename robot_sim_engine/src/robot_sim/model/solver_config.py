from __future__ import annotations
from dataclasses import dataclass
from robot_sim.domain.enums import IKSolverMode


@dataclass(frozen=True)
class IKConfig:
    mode: IKSolverMode = IKSolverMode.DLS
    max_iters: int = 150
    pos_tol: float = 1.0e-4
    ori_tol: float = 1.0e-4
    damping_lambda: float = 0.05
    step_scale: float = 0.5
    enable_nullspace: bool = True
    joint_limit_weight: float = 0.03
    manipulability_weight: float = 0.0
    position_only: bool = False
    orientation_weight: float = 1.0
    max_step_norm: float = 0.35
    singularity_cond_threshold: float = 250.0
    fallback_to_dls_when_singular: bool = True
