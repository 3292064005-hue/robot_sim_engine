from __future__ import annotations

import numpy as np

from robot_sim.domain.enums import ReferenceFrame
from robot_sim.core.kinematics.execution_adapter import resolve_execution_adapter
from robot_sim.domain.types import FloatArray
from robot_sim.model.fk_result import FKResult
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec


class ForwardKinematicsSolver:
    def solve(self, spec: RobotSpec, q: FloatArray) -> FKResult:
        adapter = resolve_execution_adapter(spec)
        adapter.require_active_path_execution()
        q_arr = np.asarray(q, dtype=float).reshape(-1)
        frames = adapter.forward_transforms(q_arr)
        graph_frames = adapter.forward_graph_transforms(q_arr)
        joint_pairs = adapter.world_joint_axes_origins(q_arr)
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
            joint_positions=np.asarray(joint_positions, dtype=float),
            ee_pose=pose,
            joint_axes=np.asarray(joint_axes, dtype=float),
            joint_origins=np.asarray(joint_origins, dtype=float),
            reference_frame=ReferenceFrame.BASE,
            metadata={
                'num_links': int(adapter.active_dof),
                'graph_joint_count': int(adapter.graph_dof),
                'graph_frame_count': int(len(graph_frames)),
                'includes_tool_transform': True,
                'execution_adapter': adapter.descriptor.adapter_id,
                'execution_semantics': adapter.descriptor.execution_semantics,
                'execution_joint_indices': [int(index) for index in adapter.active_joint_indices],
                'execution_tip_joint_index': int(adapter.tip_joint_index),
            },
        )
