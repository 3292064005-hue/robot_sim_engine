from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from robot_sim.domain.enums import JointType
from robot_sim.domain.types import FloatArray


@dataclass(frozen=True)
class RobotJointLimit:
    """Joint limit bundle used by structured robot models."""

    lower: float
    upper: float
    velocity: float | None = None
    effort: float | None = None


@dataclass(frozen=True)
class RobotLinkSpec:
    """Structured link description parsed from source models such as URDF."""

    name: str
    parent_joint: str | None = None
    inertial_mass: float | None = None
    inertial_origin: FloatArray | None = None
    has_visual: bool = False
    has_collision: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.inertial_origin is not None:
            origin = np.asarray(self.inertial_origin, dtype=float).reshape(-1)
            if origin.shape != (3,):
                raise ValueError(f'inertial_origin must be length 3, got {origin.shape}')
            if not np.isfinite(origin).all():
                raise ValueError('inertial_origin contains non-finite values')
            object.__setattr__(self, 'inertial_origin', origin.copy())


@dataclass(frozen=True)
class RobotJointSpec:
    """Structured joint description parsed from source models such as URDF."""

    name: str
    parent_link: str
    child_link: str
    joint_type: JointType
    axis: FloatArray = field(default_factory=lambda: np.array([0.0, 0.0, 1.0], dtype=float))
    limit: RobotJointLimit | None = None
    origin_translation: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=float))
    origin_rpy: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=float))
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        axis = np.asarray(self.axis, dtype=float).reshape(-1)
        translation = np.asarray(self.origin_translation, dtype=float).reshape(-1)
        rpy = np.asarray(self.origin_rpy, dtype=float).reshape(-1)
        if axis.shape != (3,):
            raise ValueError(f'joint axis must be length 3, got {axis.shape}')
        if translation.shape != (3,):
            raise ValueError(f'joint origin_translation must be length 3, got {translation.shape}')
        if rpy.shape != (3,):
            raise ValueError(f'joint origin_rpy must be length 3, got {rpy.shape}')
        if not np.isfinite(axis).all() or not np.isfinite(translation).all() or not np.isfinite(rpy).all():
            raise ValueError('joint structured fields contain non-finite values')
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1.0e-12:
            axis = np.array([0.0, 0.0, 1.0], dtype=float)
        else:
            axis = axis / axis_norm
        object.__setattr__(self, 'axis', axis.copy())
        object.__setattr__(self, 'origin_translation', translation.copy())
        object.__setattr__(self, 'origin_rpy', rpy.copy())
