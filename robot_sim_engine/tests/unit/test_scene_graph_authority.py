from __future__ import annotations

from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene
from robot_sim.model.scene_graph_authority import SceneFrame, SceneGraphAuthority


def test_planning_scene_summary_exposes_scene_graph_authority() -> None:
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_service')
    scene = service.apply_obstacle_edit(
        scene,
        SceneObstacleEdit(object_id='box_1', center=(0.0, 0.0, 0.0), size=(1.0, 1.0, 1.0)),
        source='unit_test',
    )
    summary = scene.summary()
    assert summary['scene_graph_authority']['provider'].startswith('planning_scene_')
    assert ['world', 'box_1'] in summary['scene_graph_authority']['attachment_edges']


def test_planning_scene_carries_scene_graph_authority_instance() -> None:
    scene = PlanningScene()
    assert scene.scene_graph_authority.backend == scene.collision_backend
    scene.scene_graph_authority.require_query_kind('scene_summary')


def test_scene_graph_authority_does_not_leak_robot_frames_without_matching_robot_identity() -> None:
    previous = PlanningScene().with_scene_graph_authority(
        SceneGraphAuthority(
            frame_ids=('world', 'base', 'link_1'),
            attachment_edges=(('base', 'link_1'),),
            frames=(
                SceneFrame('world', 'world', 'root'),
                SceneFrame('base', 'world', 'robot_link'),
                SceneFrame('link_1', 'base', 'robot_link'),
            ),
            metadata={'robot_graph_key': 'robot_a:base|link_1'},
        )
    )

    refreshed = SceneGraphAuthority.from_scene(PlanningScene(), previous=previous.scene_graph_authority)

    assert refreshed.frame_ids == ('world',)
    assert refreshed.attachment_edges == ()


def test_scene_graph_authority_drops_old_robot_frames_when_robot_identity_changes() -> None:
    previous = PlanningScene(
        metadata={'robot_name': 'robot_a', 'collision_link_names': ['base', 'link_1'], 'robot_graph_key': 'robot_a:base|link_1'}
    ).with_scene_graph_authority(
        SceneGraphAuthority(
            frame_ids=('world', 'base', 'link_1'),
            attachment_edges=(('base', 'link_1'),),
            frames=(
                SceneFrame('world', 'world', 'root'),
                SceneFrame('base', 'world', 'robot_link'),
                SceneFrame('link_1', 'base', 'robot_link'),
            ),
            metadata={'robot_graph_key': 'robot_a:base|link_1'},
        )
    )

    new_scene = PlanningScene(metadata={'robot_name': 'robot_b', 'collision_link_names': ['base_b', 'link_b'], 'robot_graph_key': 'robot_b:base_b|link_b'})
    refreshed = SceneGraphAuthority.from_scene(new_scene, previous=previous.scene_graph_authority)

    assert refreshed.frame_ids == ('world',)
    assert refreshed.attachment_edges == ()



def test_planning_scene_summary_exposes_scene_graph_diff_after_edit() -> None:
    scene = PlanningScene()
    edited = scene.add_obstacle(
        'box_1',
        AABB(minimum=__import__('numpy').array([-0.5, -0.5, -0.5], dtype=float), maximum=__import__('numpy').array([0.5, 0.5, 0.5], dtype=float)),
        metadata={'shape': 'box'},
    )
    diff = edited.summary()['scene_graph_diff']
    assert 'box_1' in diff['added_frames']
    assert ['world', 'box_1'] in diff['added_edges']


def test_scene_authority_service_preserves_scene_graph_diff_after_metadata_patch() -> None:
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_service')
    updated = service.apply_obstacle_edit(
        scene,
        SceneObstacleEdit(object_id='box', center=(0.0, 0.0, 0.0), size=(1.0, 1.0, 1.0)),
        source='unit_test',
    )

    diff = updated.summary()['scene_graph_diff']
    assert 'box' in diff['added_frames']
    assert ['world', 'box'] in diff['added_edges']
