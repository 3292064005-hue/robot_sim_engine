from __future__ import annotations

import numpy as np

<<<<<<< HEAD
=======
from robot_sim.core.kinematics.dh import dh_transform
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from robot_sim.domain.enums import ReferenceFrame
from robot_sim.domain.types import FloatArray
from robot_sim.model.fk_result import FKResult
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec


class ForwardKinematicsSolver:
    def solve(self, spec: RobotSpec, q: FloatArray) -> FKResult:
<<<<<<< HEAD
        articulated = spec.articulated_model
        articulated.require_serial_tree_execution()
        q_arr = np.asarray(q, dtype=float).reshape(-1)
        frames = articulated.forward_transforms(q_arr)
        joint_pairs = articulated.world_joint_axes_origins(q_arr)
        joint_positions = [np.asarray(frame[:3, 3], dtype=float).copy() for frame in frames]
        joint_axes = [np.asarray(axis, dtype=float).copy() for axis, _origin in joint_pairs]
        joint_origins = [np.asarray(origin, dtype=float).copy() for _axis, origin in joint_pairs]
        if joint_axes:
            joint_axes.insert(0, np.asarray(frames[0][:3, 2], dtype=float).copy())
            joint_origins.insert(0, np.asarray(frames[0][:3, 3], dtype=float).copy())
        else:
            joint_axes = [np.asarray(frames[0][:3, 2], dtype=float).copy()]
            joint_origins = [np.asarray(frames[0][:3, 3], dtype=float).copy()]
        T_ee = np.asarray(frames[-1], dtype=float)
        pose = Pose.from_matrix(T_ee, frame=ReferenceFrame.BASE)
        return FKResult(
            T_list=tuple(np.asarray(frame, dtype=float).copy() for frame in frames),
=======
        T = np.asarray(spec.base_T, dtype=float).copy()
        T_list = [T.copy()]
        joint_positions = [T[:3, 3].copy()]
        joint_origins = [T[:3, 3].copy()]
        joint_axes = [T[:3, 2].copy()]

        for row, q_i in zip(spec.dh_rows, q):
            T = T @ dh_transform(row, float(q_i))
            T_list.append(T.copy())
            joint_positions.append(T[:3, 3].copy())
            joint_origins.append(T[:3, 3].copy())
            joint_axes.append(T[:3, 2].copy())

        T_ee = T @ np.asarray(spec.tool_T, dtype=float)
        pose = Pose.from_matrix(T_ee, frame=ReferenceFrame.BASE)
        return FKResult(
            T_list=tuple(T_list),
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            joint_positions=np.asarray(joint_positions, dtype=float),
            ee_pose=pose,
            joint_axes=np.asarray(joint_axes, dtype=float),
            joint_origins=np.asarray(joint_origins, dtype=float),
            reference_frame=ReferenceFrame.BASE,
            metadata={
<<<<<<< HEAD
                'num_links': int(articulated.dof),
                'includes_tool_transform': True,
                'execution_adapter': 'articulated_serial_tree',
=======
                'num_links': int(spec.dof),
                'includes_tool_transform': True,
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            },
        )
