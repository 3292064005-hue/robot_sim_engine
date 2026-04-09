from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.core.math.so3 import is_rotation_matrix, orthonormalize_rotation
from robot_sim.domain.enums import ReferenceFrame
from robot_sim.domain.types import FloatArray

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.model.pose import Pose


@dataclass(frozen=True)
class Transform:
    """Rigid-body transform expressed as a 4x4 homogeneous matrix.

    Attributes:
        matrix: Homogeneous transform matrix from the owning ``frame`` to the
            represented pose.
        frame: Semantic reference frame describing the matrix interpretation.

    Boundary behavior:
        The constructor accepts any finite 4x4 matrix. Callers that require a
        guaranteed rigid transform should use :meth:`validated` or
        :meth:`from_rt`.
    """

    matrix: FloatArray
    frame: ReferenceFrame = ReferenceFrame.BASE

    def __post_init__(self) -> None:
        M = np.asarray(self.matrix, dtype=float)
        if M.shape != (4, 4):
            raise ValueError(f'transform matrix must be 4x4, got {M.shape}')
        if not np.isfinite(M).all():
            raise ValueError('transform matrix contains non-finite values')
        object.__setattr__(self, 'matrix', M.copy())

    @property
    def rotation(self) -> FloatArray:
        """Return the 3x3 rotation block."""
        return np.asarray(self.matrix[:3, :3], dtype=float).copy()

    @property
    def translation(self) -> FloatArray:
        """Return the translation vector."""
        return np.asarray(self.matrix[:3, 3], dtype=float).copy()

    @staticmethod
    def identity(*, frame: ReferenceFrame = ReferenceFrame.BASE) -> 'Transform':
        """Build an identity transform for ``frame``."""
        return Transform(np.eye(4, dtype=float), frame=frame)

    @staticmethod
    def from_rt(
        rotation: FloatArray,
        translation: FloatArray,
        *,
        frame: ReferenceFrame = ReferenceFrame.BASE,
        validate_rotation: bool = True,
    ) -> 'Transform':
        """Build a transform from rotation and translation parts.

        Args:
            rotation: Candidate 3x3 rotation matrix.
            translation: Candidate 3-vector translation.
            frame: Semantic reference frame.
            validate_rotation: Whether to project non-orthonormal rotations onto
                ``SO(3)``.

        Returns:
            Transform: Rigid transform composed from the supplied parts.

        Raises:
            ValueError: If the inputs have invalid shapes or contain non-finite
                values.
        """
        R = np.asarray(rotation, dtype=float)
        p = np.asarray(translation, dtype=float).reshape(-1)
        if R.shape != (3, 3):
            raise ValueError(f'rotation must be 3x3, got {R.shape}')
        if p.shape != (3,):
            raise ValueError(f'translation must be a length-3 vector, got {p.shape}')
        if not np.isfinite(R).all() or not np.isfinite(p).all():
            raise ValueError('transform parts contain non-finite values')
        if validate_rotation and not is_rotation_matrix(R, atol=1.0e-6):
            R = orthonormalize_rotation(R)
        T = np.eye(4, dtype=float)
        T[:3, :3] = R
        T[:3, 3] = p
        return Transform(T, frame=frame)

    @staticmethod
    def from_pose(pose: Pose) -> 'Transform':
        """Convert a :class:`Pose` into a homogeneous transform."""
        return Transform.from_rt(pose.R, pose.p, frame=pose.frame)

    def validated(self, *, orthonormalize: bool = True) -> 'Transform':
        """Return a finite rigid transform with an optional ``SO(3)`` projection."""
        R = self.rotation
        if orthonormalize and not is_rotation_matrix(R, atol=1.0e-6):
            R = orthonormalize_rotation(R)
        return Transform.from_rt(R, self.translation, frame=self.frame, validate_rotation=False)

    def inverse(self) -> 'Transform':
        """Return the inverse rigid transform.

        Raises:
            ValueError: If the stored rotation block is singular / invalid.
        """
        rigid = self.validated()
        R = rigid.rotation
        p = rigid.translation
        T_inv = np.eye(4, dtype=float)
        T_inv[:3, :3] = R.T
        T_inv[:3, 3] = -(R.T @ p)
        return Transform(T_inv, frame=self.frame)

    def compose(self, other: 'Transform') -> 'Transform':
        """Right-compose ``other`` onto this transform.

        Args:
            other: Transform expressed in the same semantic chain.

        Returns:
            Transform: ``self * other``.
        """
        return Transform(np.asarray(self.matrix, dtype=float) @ np.asarray(other.matrix, dtype=float), frame=self.frame)

    def to_pose(self) -> Pose:
        """Project the transform into a :class:`Pose` object."""
        from robot_sim.model.pose import Pose

        return Pose.from_matrix(self.matrix, frame=self.frame)
