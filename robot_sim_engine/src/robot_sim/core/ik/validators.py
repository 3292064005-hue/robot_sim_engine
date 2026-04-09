from __future__ import annotations
import numpy as np
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.domain.types import FloatArray

<<<<<<< HEAD

def clip_to_joint_limits(spec: RobotSpec, q: FloatArray) -> FloatArray:
    articulated = spec.articulated_model
    articulated.require_serial_tree_execution()
    q_out = np.asarray(q, dtype=float).copy()
    return np.clip(q_out, articulated.joint_minima, articulated.joint_maxima)
=======
def clip_to_joint_limits(spec: RobotSpec, q: FloatArray) -> FloatArray:
    q_out = q.copy()
    for i, row in enumerate(spec.dh_rows):
        q_out[i] = np.clip(q_out[i], row.q_min, row.q_max)
    return q_out
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
