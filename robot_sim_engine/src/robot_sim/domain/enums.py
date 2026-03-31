from __future__ import annotations
from enum import Enum

class JointType(str, Enum):
    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"

class IKSolverMode(str, Enum):
    PINV = "pinv"
    DLS = "dls"
