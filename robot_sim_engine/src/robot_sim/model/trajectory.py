from __future__ import annotations
from dataclasses import dataclass
from robot_sim.domain.types import FloatArray

@dataclass(frozen=True)
class JointTrajectory:
    t: FloatArray
    q: FloatArray
    qd: FloatArray
    qdd: FloatArray
