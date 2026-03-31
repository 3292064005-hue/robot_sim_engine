from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.pose import Pose
from robot_sim.model.fk_result import FKResult
from robot_sim.model.ik_result import IKResult
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.playback_state import PlaybackState
from robot_sim.domain.types import FloatArray


@dataclass
class SessionState:
    robot_spec: Optional[RobotSpec] = None
    q_current: Optional[FloatArray] = None
    target_pose: Optional[Pose] = None
    fk_result: Optional[FKResult] = None
    ik_result: Optional[IKResult] = None
    trajectory: Optional[JointTrajectory] = None
    playback: PlaybackState = field(default_factory=PlaybackState)
    is_busy: bool = False
    busy_reason: str = ""
    last_error: str = ""
    last_warning: str = ""
