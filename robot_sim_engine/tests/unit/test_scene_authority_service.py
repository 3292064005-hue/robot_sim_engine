from __future__ import annotations

from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene


def test_scene_authority_service_bootstraps_stable_scene_from_summary():
    service = SceneAuthorityService()
    scene = service.ensure_scene(
        None,
        scene_summary={'revision': 4, 'collision_backend': 'aabb', 'scene_fidelity': 'approximate'},
        authority='scene_coordinator',
        edit_surface='stable_scene_editor',
    )

    assert isinstance(scene, PlanningScene)
    assert scene.revision == 4
    assert scene.scene_authority == 'scene_coordinator'
    assert scene.edit_surface == 'stable_scene_editor'
    assert scene.scene_fidelity == 'approximate'
    assert scene.summary()['geometry_authority']['authority'] == 'scene_coordinator'


def test_scene_authority_service_applies_obstacle_and_allowed_pairs():
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_coordinator', edit_surface='stable_scene_editor')
    edit = SceneObstacleEdit.from_mapping(
        {
            'object_id': 'fixture',
            'center': (0.4, 0.0, 0.3),
            'size': (0.2, 0.1, 0.3),
            'allowed_collision_pairs': (('fixture', 'link_2'), ('tool', 'fixture')),
            'clear_allowed_collision_pairs': True,
            'metadata': {'label': 'test fixture'},
        }
    )

    updated = service.apply_obstacle_edit(scene, edit, source='scene_toolbar')

    assert updated.obstacle_ids == ('fixture',)
    assert updated.allowed_collision_pairs == (('fixture', 'link_2'), ('fixture', 'tool'))
    assert updated.obstacles[0].metadata['label'] == 'test fixture'
    assert updated.obstacles[0].metadata['editor'] == 'stable_scene_editor'
    assert updated.obstacles[0].metadata['declared_geometry']['kind'] == 'box'
    assert updated.obstacles[0].metadata['resolved_geometry']['kind'] == 'aabb'
    assert updated.metadata['last_edit_source'] == 'scene_toolbar'
    assert updated.summary()['scene_geometry_contract'] == 'declaration_validation_render'
    assert updated.summary()['collision_filter_pair_count'] == 2
    authority = updated.summary()['geometry_authority']
    assert authority['declaration_geometry_source'] == 'stable_scene_editor'
    assert authority['validation_geometry_source'] == 'aabb_planning_scene'
    assert authority['render_geometry_source'] == 'stable_scene_editor'


def test_scene_authority_service_suffixes_duplicate_obstacle_ids_without_replace():
    service = SceneAuthorityService()
    scene = PlanningScene().add_obstacle('fixture', AABB([-0.1, -0.1, -0.1], [0.1, 0.1, 0.1]))
    edit = SceneObstacleEdit.from_mapping(
        {
            'object_id': 'fixture',
            'center': (0.4, 0.0, 0.3),
            'size': (0.2, 0.2, 0.2),
        }
    )

    updated = service.apply_obstacle_edit(scene, edit, source='scene_toolbar')

    assert updated.obstacle_ids == ('fixture', 'fixture_2')


def test_scene_authority_service_bootstraps_summary_pairs_and_backend_normalization():
    service = SceneAuthorityService()
    scene = service.ensure_scene(
        None,
        scene_summary={
            'revision': 7,
            'collision_backend': 'capsule',
            'geometry_source': 'bundle',
            'allowed_collision_pairs': (('tool', 'fixture'), ('link_2', 'fixture')),
        },
        authority='scene_coordinator',
        edit_surface='stable_scene_editor',
    )

    assert scene.revision == 7
    assert scene.collision_backend == 'aabb'
    assert scene.allowed_collision_pairs == (('fixture', 'link_2'), ('fixture', 'tool'))
    assert scene.metadata['requested_collision_backend'] == 'capsule'
    assert scene.metadata['resolved_collision_backend'] == 'aabb'
    assert 'collision_backend_warning' in scene.metadata


def test_planning_scene_default_edit_surface_is_stable_scene_editor():
    scene = PlanningScene()

    assert scene.edit_surface == 'stable_scene_editor'
    assert scene.summary()['edit_surface'] == 'stable_scene_editor'


def test_scene_authority_service_supports_sphere_attached_objects():
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_coordinator', edit_surface='stable_scene_editor')
    edit = SceneObstacleEdit.from_mapping(
        {
            'object_id': 'tool_guard',
            'center': (0.0, 0.0, 0.4),
            'shape': 'sphere',
            'radius': 0.15,
            'attached': True,
            'attach_link': 'tool0',
        }
    )

    updated = service.apply_obstacle_edit(scene, edit, source='scene_toolbar')

    assert updated.attached_object_ids == ('tool_guard',)
    assert updated.attached_objects[0].metadata['shape'] == 'sphere'
    assert updated.attached_objects[0].metadata['attach_link'] == 'tool0'
    assert updated.metadata['last_edit_kind'] == 'attached_object'


def test_scene_authority_service_accepts_cylinder_shape_payload():
    edit = SceneObstacleEdit.from_mapping(
        {
            'object_id': 'fixture',
            'center': (0.4, 0.0, 0.3),
            'shape': 'cylinder',
            'radius': 0.1,
            'height': 0.6,
        }
    )

    assert edit.shape == 'cylinder'
    assert edit.size == (0.2, 0.2, 0.6)
