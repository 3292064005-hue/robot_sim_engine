from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IKSeedPolicy(str, Enum):
    PROVIDED = 'provided'
    HOME = 'home'
    MID_LIMITS = 'mid_limits'
    MULTI_START = 'multi_start'


@dataclass(frozen=True)
class IKTaskMask:
    """Task-space mask controlling which target dimensions are enforced."""

    position: tuple[bool, bool, bool] = (True, True, True)
    orientation: tuple[bool, bool, bool] = (True, True, True)

    def __post_init__(self) -> None:
        if len(self.position) != 3 or len(self.orientation) != 3:
            raise ValueError('IKTaskMask position and orientation masks must each have length 3')

    @property
    def position_only(self) -> bool:
        return not any(self.orientation)


@dataclass(frozen=True)
class IKConstraintSummary:
    """Human-readable summary of the active IK contract.

    Attributes:
        target_frame: Frame in which the target pose is interpreted.
        position_only: Whether orientation is intentionally relaxed.
        orientation_weight: Effective orientation scaling applied by the solver.
        notes: Bounded diagnostic notes attached at request construction.
    """

    target_frame: str
    position_only: bool
    orientation_weight: float
    notes: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
