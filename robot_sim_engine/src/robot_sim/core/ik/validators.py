from __future__ import annotations
import numpy as np
from robot_sim.core.kinematics.execution_adapter import resolve_execution_adapter
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.domain.types import FloatArray


def clip_to_joint_limits(spec: RobotSpec, q: FloatArray) -> FloatArray:
    adapter = resolve_execution_adapter(spec)
    adapter.require_active_path_execution()
    q_out = np.asarray(q, dtype=float).copy()
    return np.clip(q_out, adapter.joint_minima, adapter.joint_maxima)
