from __future__ import annotations
from dataclasses import dataclass
from robot_sim.domain.types import FloatArray

@dataclass(frozen=True)
class JacobianResult:
    J: FloatArray
    condition_number: float
    manipulability: float
