from __future__ import annotations

from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService


def test_scene_authority_summary_exposes_three_geometry_layers() -> None:
    service = SceneAuthorityService()
    scene = service.ensure_scene(None, authority='scene_service')
    updated = service.apply_obstacle_edit(
        scene,
        SceneObstacleEdit(object_id='fixture', center=(0.1, 0.2, 0.3), size=(0.4, 0.5, 0.6), shape='cylinder'),
        source='scene_toolbar',
    )

    summary = updated.summary()
    assert summary['scene_geometry_contract'] == 'declaration_validation_render'
    authority = summary['geometry_authority']
    assert authority['declaration_geometry_source'] == 'stable_scene_editor'
    assert authority['validation_geometry_source'] == 'aabb_planning_scene'
    assert authority['render_geometry_source'] == 'stable_scene_editor'
    record = authority['records'][0]
    assert record['declaration_geometry']['kind'] == 'cylinder'
    assert record['validation_geometry']['kind'] == 'aabb'
    assert record['render_geometry']['kind'] == 'cylinder'
    assert record['validation_projection']['projection_degraded'] is True
    assert summary['validation_projection']['record_count'] == 1
    assert summary['validation_projection']['degraded_record_count'] == 1
    assert record['declaration_geometry']['kind'] == 'cylinder'
    assert record['validation_geometry']['kind'] == 'aabb'


def test_runtime_asset_service_projects_three_layer_scene_authority(planar_spec):
    assets = RobotRuntimeAssetService().build_assets(planar_spec)
    authority = assets.scene_summary['geometry_authority']
    assert assets.geometry_model.summary()['geometry_contract'] == 'split_visual_collision'
    assert authority['scene_geometry_contract'] == 'declaration_validation_render'
    assert authority['authority_kind'] == 'runtime_robot_scene'
    assert authority['validation_geometry_source'] == 'planning_scene_runtime_projection'
