from __future__ import annotations
from dataclasses import dataclass
from robot_sim.domain.types import FloatArray


@dataclass(frozen=True)
class IKIterationLog:
    iter_idx: int
    pos_err_norm: float
    ori_err_norm: float
    cond_number: float
    manipulability: float
    dq_norm: float = 0.0
    elapsed_ms: float = 0.0
    effective_mode: str = ""


@dataclass(frozen=True)
class IKResult:
    success: bool
    q_sol: FloatArray
    logs: tuple[IKIterationLog, ...]
    message: str
