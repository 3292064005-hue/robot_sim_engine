from __future__ import annotations

import numpy as np

from robot_sim.domain.enums import ReferenceFrame
from robot_sim.model.pose import Pose
from robot_sim.model.transform import Transform


def test_pose_transform_roundtrip_preserves_frame():
    pose = Pose.from_quaternion(np.array([1.0, 2.0, 3.0], dtype=float), np.array([1.0, 0.0, 0.0, 0.0], dtype=float), frame=ReferenceFrame.TOOL)
    transform = Transform.from_pose(pose)
    reconstructed = transform.to_pose()
    assert reconstructed.frame is ReferenceFrame.TOOL
    assert np.allclose(reconstructed.p, pose.p)
    assert np.allclose(reconstructed.R, pose.R)


def test_pose_relative_and_inverse_are_consistent():
    a = Pose(p=np.array([1.0, 0.0, 0.0], dtype=float), R=np.eye(3, dtype=float))
    b = Pose(p=np.array([2.0, 0.0, 0.0], dtype=float), R=np.eye(3, dtype=float))
    rel = b.relative_to(a)
    assert np.allclose(rel.p, np.array([1.0, 0.0, 0.0], dtype=float))
    identity = a.compose(a.inverse())
    assert np.allclose(identity.to_matrix(), np.eye(4, dtype=float))
