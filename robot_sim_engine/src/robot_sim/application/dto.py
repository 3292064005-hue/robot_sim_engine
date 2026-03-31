from __future__ import annotations
from dataclasses import dataclass
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.domain.types import FloatArray

@dataclass(frozen=True)
class FKRequest:
    spec: RobotSpec
    q: FloatArray

@dataclass(frozen=True)
class IKRequest:
    spec: RobotSpec
    target: Pose
    q0: FloatArray
    config: IKConfig

@dataclass(frozen=True)
class TrajectoryRequest:
    q_start: FloatArray
    q_goal: FloatArray
    duration: float
    dt: float
