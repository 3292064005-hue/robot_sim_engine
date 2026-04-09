from __future__ import annotations

import numpy as np

from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.core.collision.geometry import AABB
from robot_sim.domain.enums import JointType
from robot_sim.model.articulated_robot_model import ArticulatedJointModel, ArticulatedRobotModel
from robot_sim.model.dh_row import DHRow


def test_articulated_execution_preserves_joint_axis_and_origin() -> None:
    model = ArticulatedRobotModel(
        name='axis_x_robot',
        root_link='base',
        joint_models=(
            ArticulatedJointModel(
                name='joint_1',
                parent_link='base',
                child_link='link_1',
                joint_type=JointType.REVOLUTE,
                axis=(1.0, 0.0, 0.0),
                origin_translation=(0.0, 1.0, 0.0),
                origin_rpy=(0.0, 0.0, 0.0),
                parent_index=None,
            ),
        ),
        link_names=('base', 'link_1'),
        base_T=np.eye(4, dtype=float),
        tool_T=np.eye(4, dtype=float),
        home_q=np.zeros(1, dtype=float),
    )

    frames = model.forward_transforms(np.array([np.pi / 2.0], dtype=float))
    axis_world, origin_world = model.world_joint_axes_origins(np.array([0.0], dtype=float))[0]

    np.testing.assert_allclose(origin_world, np.array([0.0, 1.0, 0.0], dtype=float))
    np.testing.assert_allclose(axis_world, np.array([1.0, 0.0, 0.0], dtype=float))
    np.testing.assert_allclose(frames[1][:3, :3], np.array([
        [1.0, 0.0, 0.0],
        [0.0, 0.0, -1.0],
        [0.0, 1.0, 0.0],
    ], dtype=float), atol=1.0e-9)
    np.testing.assert_allclose(frames[1][:3, 3], np.array([0.0, 1.0, 0.0], dtype=float))


def test_robot_spec_articulated_model_prefers_canonical_source_semantics(planar_spec) -> None:
    articulated = planar_spec.articulated_model
    assert articulated.source_surface == 'canonical_model'
    assert articulated.joint_models[0].axis == (0.0, 0.0, 1.0)
    np.testing.assert_allclose(np.asarray(articulated.joint_models[0].origin_translation, dtype=float), np.array([1.0, 0.0, 0.0], dtype=float))



def test_scene_graph_authority_retains_robot_frames_after_scene_edit(planar_spec) -> None:
    service = RobotRuntimeAssetService(experimental_collision_backends_enabled=True)
    assets = service.build_assets(planar_spec)
    seeded_scene = assets.planning_scene

    assert {'world', *planar_spec.runtime_link_names}.issubset(set(seeded_scene.scene_graph_authority.frame_ids))

    updated_scene = seeded_scene.add_obstacle(
        'box_keep_robot_graph',
        AABB(np.array([-0.1, -0.1, -0.1], dtype=float), np.array([0.1, 0.1, 0.1], dtype=float)),
        metadata={'shape': 'box'},
    )

    frame_ids = set(updated_scene.scene_graph_authority.frame_ids)
    assert {'world', *planar_spec.runtime_link_names, 'box_keep_robot_graph'}.issubset(frame_ids)
    assert all(
        edge in set(updated_scene.scene_graph_authority.attachment_edges)
        for edge in tuple(zip(planar_spec.runtime_link_names[:-1], planar_spec.runtime_link_names[1:]))
    )



def test_canonical_articulated_projection_rejects_unresolved_parent_chain() -> None:
    from robot_sim.model.canonical_robot_model import CanonicalRobotModel
    from robot_sim.model.robot_links import RobotJointSpec
    from robot_sim.model.articulated_robot_model import build_articulated_robot_model_from_canonical

    canonical = CanonicalRobotModel(
        name='bad_topology',
        joints=(
            RobotJointSpec(name='j1', parent_link='base', child_link='l1', joint_type=JointType.REVOLUTE),
            RobotJointSpec(name='j2', parent_link='missing_parent', child_link='l2', joint_type=JointType.REVOLUTE),
        ),
        links=(),
        root_link='base',
        source_format='urdf',
        execution_rows=(
            DHRow(a=1.0, alpha=0.0, d=0.0, theta_offset=0.0, joint_type=JointType.REVOLUTE, q_min=-3.14, q_max=3.14),
            DHRow(a=1.0, alpha=0.0, d=0.0, theta_offset=0.0, joint_type=JointType.REVOLUTE, q_min=-3.14, q_max=3.14),
        ),
        metadata={},
    )
    try:
        build_articulated_robot_model_from_canonical(
            canonical,
            base_T=np.eye(4, dtype=float),
            tool_T=np.eye(4, dtype=float),
            home_q=np.zeros(2, dtype=float),
        )
    except ValueError as exc:
        assert 'could not resolve parent link' in str(exc)
    else:
        raise AssertionError('expected ValueError for unresolved canonical parent chain')
