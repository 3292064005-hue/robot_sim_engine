from __future__ import annotations

import numpy as np

from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.domain.enums import JointType
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec, RobotLinkSpec
from robot_sim.model.robot_spec import RobotSpec


def test_robot_registry_roundtrip_preserves_structured_model(tmp_path):
    registry = RobotRegistry(tmp_path)
    spec = RobotSpec(
        name='structured_arm',
        dh_rows=(DHRow(1.0, 0.0, 0.0, 0.0, JointType.REVOLUTE, -1.0, 1.0),),
        base_T=np.eye(4, dtype=float),
        tool_T=np.eye(4, dtype=float),
        home_q=np.zeros(1, dtype=float),
        joint_names=('j1',),
        link_names=('base', 'tip'),
        joint_types=(JointType.REVOLUTE,),
        joint_axes=((0.0, 0.0, 1.0),),
        joint_limits=(RobotJointLimit(-1.0, 1.0),),
        structured_joints=(
            RobotJointSpec(
                name='j1',
                parent_link='base',
                child_link='tip',
                joint_type=JointType.REVOLUTE,
                axis=np.array([0.0, 0.0, 1.0], dtype=float),
                limit=RobotJointLimit(-1.0, 1.0),
                origin_translation=np.array([0.0, 0.0, 1.0], dtype=float),
                origin_rpy=np.zeros(3, dtype=float),
            ),
        ),
        structured_links=(RobotLinkSpec(name='base', has_visual=True), RobotLinkSpec(name='tip', has_collision=True)),
        source_model_summary={'joint_count': 1, 'has_visual': True},
    )
    registry.save(spec)
    loaded = registry.load('structured_arm')
    assert loaded.joint_names == ('j1',)
    assert loaded.structured_joints[0].child_link == 'tip'
    assert loaded.source_model_summary['joint_count'] == 1
