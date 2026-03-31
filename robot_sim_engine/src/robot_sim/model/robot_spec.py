from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from robot_sim.model.dh_row import DHRow
from robot_sim.domain.types import FloatArray

@dataclass(frozen=True)
class RobotSpec:
    name: str
    dh_rows: tuple[DHRow, ...]
    base_T: FloatArray
    tool_T: FloatArray
    home_q: FloatArray
    display_name: str | None = None
    description: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def dof(self) -> int:
        return len(self.dh_rows)

    @property
    def label(self) -> str:
        return self.display_name or self.name

    def q_mid(self) -> FloatArray:
        return np.array([(r.q_min + r.q_max) * 0.5 for r in self.dh_rows], dtype=float)
