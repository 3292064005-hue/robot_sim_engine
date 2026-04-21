from __future__ import annotations

from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import SceneObject
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
    assert updated.obstacles[0].metadata['declaration_geometry']['kind'] == 'box'
    assert updated.obstacles[0].metadata['validation_geometry']['kind'] == 'aabb'
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
    assert scene.collision_backend == 'capsule'
    assert scene.allowed_collision_pairs == (('fixture', 'link_2'), ('fixture', 'tool'))
    assert scene.metadata['requested_collision_backend'] == 'capsule'
    assert scene.metadata['resolved_collision_backend'] == 'capsule'
    assert 'collision_backend_warning' not in scene.metadata


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


def test_scene_summary_reprojects_validation_geometry_from_declaration_truth() -> None:
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_service')
    updated = service.apply_obstacle_edit(
        scene,
        SceneObstacleEdit(object_id='fixture', center=(0.0, 0.0, 0.0), size=(0.4, 0.4, 0.4), shape='sphere'),
        source='scene_toolbar',
    )
    tampered = SceneObject(
        object_id='fixture',
        geometry=AABB([-10.0, -10.0, -10.0], [10.0, 10.0, 10.0]),
        metadata=dict(updated.obstacles[0].metadata),
    )
    tampered_scene = updated._spawn(obstacles=(tampered,), revision=updated.revision + 1)
    summary = tampered_scene.summary()['obstacles'][0]
    assert summary['declaration_geometry']['kind'] == 'sphere'
    assert summary['validation_geometry']['kind'] == 'aabb'
    assert summary['validation_query_geometry']['maximum'] == [0.2, 0.2, 0.2]



def test_scene_authority_service_emits_scene_command_log_for_obstacle_mutations() -> None:
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_coordinator', edit_surface='stable_scene_editor')

    mutation = service.execute_obstacle_edit(
        scene,
        SceneObstacleEdit(object_id='fixture', center=(0.0, 0.0, 0.0), size=(0.2, 0.2, 0.2)),
        source='scene_toolbar',
    )

    summary = mutation.scene.summary()
    assert mutation.command.summary()['command_kind'] == 'upsert_obstacle'
    assert summary['last_scene_command']['command_kind'] == 'upsert_obstacle'
    assert summary['scene_command_log_tail'][-1]['source'] == 'scene_toolbar'
    assert summary['scene_command_log_tail'][-1]['revision_after'] == mutation.scene.revision
    assert summary['log_policy']['intended_use'] == 'diagnostic_log_and_replay'
    assert summary['log_policy']['supports_replay'] is True
    assert summary['log_policy']['supports_clone'] is True
    assert summary['log_policy']['supports_diff_replication'] is True
    assert summary['log_policy']['supports_concurrent_snapshots'] is True
    assert summary['environment_contract']['version'] == 'v2'
    assert summary['replay_cursor'] == f"rev:{mutation.scene.revision}"
    assert summary['scene_command_history'][-1]['command_kind'] == 'upsert_obstacle'


def test_scene_authority_service_emits_scene_command_log_for_clear_operations() -> None:
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_coordinator', edit_surface='stable_scene_editor')
    scene = service.apply_obstacle_edit(
        scene,
        SceneObstacleEdit(object_id='fixture', center=(0.0, 0.0, 0.0), size=(0.2, 0.2, 0.2)),
        source='scene_toolbar',
    )

    mutation = service.execute_clear_obstacles(scene, source='scene_toolbar')

    assert mutation.scene.obstacle_ids == ()
    assert mutation.command.summary()['command_kind'] == 'clear_obstacles'
    assert mutation.scene.summary()['scene_command_log_tail'][-1]['metadata']['cleared_obstacle_count'] == 1


def test_scene_authority_service_clone_and_replay_supports_concurrent_snapshots() -> None:
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_coordinator', edit_surface='stable_scene_editor')
    first = service.execute_obstacle_edit(
        scene,
        SceneObstacleEdit(object_id='fixture', center=(0.0, 0.0, 0.0), size=(0.2, 0.2, 0.2)),
        source='scene_toolbar',
    )

    cloned = service.clone_scene(first.scene, planner_id='planner.alpha', clone_reason='concurrent_validation')
    clone_summary = cloned.summary()
    assert clone_summary['clone_token'].endswith(':planner.alpha')
    assert clone_summary['concurrent_snapshot_tokens'][-1] == clone_summary['clone_token']
    assert clone_summary['environment_contract']['supports_concurrent_snapshots'] is True

    replayed = service.replay_scene(
        service.ensure_scene(None, authority='scene_coordinator', edit_surface='stable_scene_editor'),
        first.scene.summary()['scene_command_history'],
        planner_id='planner.beta',
    )
    replay_summary = replayed.summary()
    assert replay_summary['obstacle_ids'] == ['fixture']
    assert replay_summary['scene_command_history'][-1]['command_kind'] == 'upsert_obstacle'
    assert replay_summary['diff_replication']['target_revision'] == replay_summary['revision']
    assert replay_summary['environment_contract']['supports_replay'] is True
    assert replay_summary['replay_cursor'].startswith('rev:')
