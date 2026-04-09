from __future__ import annotations

import math

import numpy as np

from robot_sim.domain.types import FloatArray
from robot_sim.model.transform import Transform


def rot_x(a: float) -> FloatArray:
    """Return an X-axis rotation matrix."""
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)


def rot_y(a: float) -> FloatArray:
    """Return a Y-axis rotation matrix."""
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)


def rot_z(a: float) -> FloatArray:
    """Return a Z-axis rotation matrix."""
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def make_transform(R: FloatArray, p: FloatArray) -> FloatArray:
    """Build a homogeneous transform matrix from rotation and translation.

    Args:
        R: Rotation matrix of shape ``(3, 3)``.
        p: Translation vector of shape ``(3,)``.

    Returns:
        FloatArray: 4x4 homogeneous transform.

    Raises:
        ValueError: If the input shapes are invalid or contain non-finite values.
    """
    return Transform.from_rt(R, p).matrix


def compose_transforms(*transforms: FloatArray) -> FloatArray:
    """Compose one or more homogeneous transforms in order."""
    result = Transform.identity()
    for item in transforms:
        result = result.compose(Transform(np.asarray(item, dtype=float)))
    return result.matrix


def invert_transform(T: FloatArray) -> FloatArray:
    """Return the inverse of a homogeneous rigid transform."""
    return Transform(np.asarray(T, dtype=float)).inverse().matrix


def translation(x: float, y: float, z: float) -> FloatArray:
    """Build a pure-translation homogeneous transform."""
    return Transform.from_rt(np.eye(3, dtype=float), np.array([x, y, z], dtype=float)).matrix
