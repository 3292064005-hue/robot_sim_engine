from __future__ import annotations

from dataclasses import dataclass

import numpy as np

<<<<<<< HEAD
from robot_sim.core.math.so3 import is_rotation_matrix, orthonormalize_rotation
from robot_sim.core.rotation.quaternion import from_matrix as quaternion_from_matrix
from robot_sim.core.rotation.quaternion import to_matrix as quaternion_to_matrix
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from robot_sim.domain.enums import ReferenceFrame
from robot_sim.domain.types import FloatArray


@dataclass(frozen=True)
class Pose:
<<<<<<< HEAD
    """Rigid pose represented by translation and rotation components.

    Attributes:
        p: Translation vector of shape ``(3,)``.
        R: Rotation matrix of shape ``(3, 3)``.
        frame: Semantic reference frame of the pose.

    Boundary behavior:
        The dataclass keeps the legacy ``p`` / ``R`` surface used across the V7
        runtime while adding explicit validation and composition helpers. Invalid
        rotations can be projected onto ``SO(3)`` through :meth:`validated`.
    """

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    p: FloatArray
    R: FloatArray
    frame: ReferenceFrame = ReferenceFrame.BASE

<<<<<<< HEAD
    def __post_init__(self) -> None:
        p = np.asarray(self.p, dtype=float).reshape(-1)
        R = np.asarray(self.R, dtype=float)
        if p.shape != (3,):
            raise ValueError(f'pose translation must be length 3, got {p.shape}')
        if R.shape != (3, 3):
            raise ValueError(f'pose rotation must be 3x3, got {R.shape}')
        if not np.isfinite(p).all() or not np.isfinite(R).all():
            raise ValueError('pose contains non-finite values')
        object.__setattr__(self, 'p', p.copy())
        object.__setattr__(self, 'R', R.copy())

    @staticmethod
    def from_matrix(T: FloatArray, *, frame: ReferenceFrame = ReferenceFrame.BASE) -> 'Pose':
        """Build a pose from a homogeneous transform matrix.

        Args:
            T: Candidate 4x4 homogeneous transform.
            frame: Semantic reference frame associated with the matrix.

        Returns:
            Pose: Pose projection of ``T``.

        Raises:
            ValueError: If ``T`` is not a finite 4x4 matrix.
        """
        M = np.asarray(T, dtype=float)
        if M.shape != (4, 4):
            raise ValueError(f'pose matrix must be 4x4, got {M.shape}')
        if not np.isfinite(M).all():
            raise ValueError('pose matrix contains non-finite values')
        return Pose(p=M[:3, 3].copy(), R=M[:3, :3].copy(), frame=frame)

    @staticmethod
    def from_quaternion(
        p: FloatArray,
        q_wxyz: FloatArray,
        *,
        frame: ReferenceFrame = ReferenceFrame.BASE,
    ) -> 'Pose':
        """Build a pose from translation and a quaternion in ``[w, x, y, z]`` order."""
        return Pose(p=np.asarray(p, dtype=float), R=quaternion_to_matrix(q_wxyz), frame=frame)

    def to_matrix(self) -> FloatArray:
        """Convert the pose to a homogeneous transform matrix."""
=======
    @staticmethod
    def from_matrix(T: FloatArray, *, frame: ReferenceFrame = ReferenceFrame.BASE) -> "Pose":
        return Pose(p=T[:3, 3].copy(), R=T[:3, :3].copy(), frame=frame)

    def to_matrix(self) -> FloatArray:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        T = np.eye(4, dtype=float)
        T[:3, :3] = self.R
        T[:3, 3] = self.p
        return T

<<<<<<< HEAD
    def as_quaternion(self) -> FloatArray:
        """Return the pose rotation as a normalized quaternion ``[w, x, y, z]``."""
        return quaternion_from_matrix(self.validated().R)

    def validated(self, *, orthonormalize: bool = True) -> 'Pose':
        """Return a finite pose with an optionally orthonormalized rotation.

        Args:
            orthonormalize: Whether to project non-orthonormal rotations onto
                ``SO(3)``.

        Returns:
            Pose: Validated pose.
        """
        R = np.asarray(self.R, dtype=float)
        if orthonormalize and not is_rotation_matrix(R, atol=1.0e-6):
            R = orthonormalize_rotation(R)
        return Pose(p=np.asarray(self.p, dtype=float), R=R, frame=self.frame)

    def with_frame(self, frame: ReferenceFrame) -> 'Pose':
        """Clone the pose under a different semantic reference frame."""
        return Pose(p=np.asarray(self.p, dtype=float).copy(), R=np.asarray(self.R, dtype=float).copy(), frame=frame)

    def compose(self, other: 'Pose') -> 'Pose':
        """Right-compose ``other`` after this pose.

        Args:
            other: Pose to apply after this pose.

        Returns:
            Pose: ``self * other`` expressed in ``self.frame``.
        """
        return Pose.from_matrix(self.to_matrix() @ other.to_matrix(), frame=self.frame)

    def inverse(self) -> 'Pose':
        """Return the inverse rigid pose."""
        rigid = self.validated()
        Rt = rigid.R.T
        return Pose(p=-(Rt @ rigid.p), R=Rt, frame=rigid.frame)

    def relative_to(self, reference: 'Pose') -> 'Pose':
        """Express this pose relative to ``reference``.

        Args:
            reference: Pose treated as the parent reference frame.

        Returns:
            Pose: Relative transform ``reference^-1 * self``.
        """
        return reference.inverse().compose(self)

    def orthonormalized(self) -> 'Pose':
        """Compatibility alias for :meth:`validated` with projection enabled."""
        return self.validated(orthonormalize=True)
=======
    def with_frame(self, frame: ReferenceFrame) -> "Pose":
        return Pose(p=np.asarray(self.p, dtype=float).copy(), R=np.asarray(self.R, dtype=float).copy(), frame=frame)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
