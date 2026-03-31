from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from robot_sim.domain.types import FloatArray

@dataclass(frozen=True)
class Pose:
    p: FloatArray
    R: FloatArray

    @staticmethod
    def from_matrix(T: FloatArray) -> "Pose":
        return Pose(p=T[:3, 3].copy(), R=T[:3, :3].copy())

    def to_matrix(self) -> FloatArray:
        T = np.eye(4, dtype=float)
        T[:3, :3] = self.R
        T[:3, 3] = self.p
        return T
