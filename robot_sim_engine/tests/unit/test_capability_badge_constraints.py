from __future__ import annotations

import numpy as np
import pytest

from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_links import RobotJointLimit
from robot_sim.model.runtime_robot_model import RuntimeRobotModel
from robot_sim.model.scene_geometry_authority import SceneGeometryAuthority


def test_runtime_robot_model_requires_serial_chain_execution():
    model = RuntimeRobotModel(
        name='bad',
        execution_rows=(DHRow(a=0.0, alpha=0.0, d=0.0, theta_offset=0.0, joint_type='revolute', q_min=-1.0, q_max=1.0),),
        joint_names=('j1',),
        link_names=('base', 'tool'),
        joint_limits=(RobotJointLimit(-1.0, 1.0),),
        base_T=np.eye(4),
        tool_T=np.eye(4),
        home_q=np.zeros(1),
        semantic_family='tree_execution',
    )
    with pytest.raises(ValueError, match='serial-chain execution semantics'):
        model.require_serial_chain_execution()


def test_scene_geometry_authority_requires_supported_shape():
    authority = SceneGeometryAuthority(authority='planning_scene', supported_scene_shapes=('box',))
    with pytest.raises(ValueError, match='does not support shape'):
        authority.require_supported_shape('sphere')
