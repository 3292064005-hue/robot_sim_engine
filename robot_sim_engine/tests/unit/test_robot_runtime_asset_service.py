from __future__ import annotations

from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService


def test_runtime_asset_service_builds_canonical_scene(planar_spec):
    service = RobotRuntimeAssetService()
    assets = service.build_assets(planar_spec)

    assert assets.robot_geometry is not None
    assert assets.collision_geometry is not None
    assert assets.planning_scene.collision_backend == 'capsule'
    assert assets.scene_summary['collision_backend'] == 'capsule'
    assert assets.scene_summary['geometry_source'] == planar_spec.model_source
    assert assets.planning_scene.edit_surface == 'stable_scene_editor'
    assert assets.scene_summary['edit_surface'] == 'stable_scene_editor'
    assert assets.planning_scene.metadata['scene_fidelity'] == 'approximate'
    assert assets.scene_summary['stable_surface_version'] == 'v3'
    assert assets.scene_summary['supported_scene_shapes'] == ['box', 'cylinder', 'sphere']
    assert assets.planning_scene.metadata['robot_geometry_fidelity']
    assert assets.planning_scene.metadata['collision_geometry_fidelity']
    assert assets.planning_scene.metadata['runtime_semantic_family'] == 'articulated_serial_tree'
    assert assets.geometry_model.geometry_contract == 'split_visual_collision'
    assert assets.scene_summary['runtime_model_summary']['execution_row_count'] == planar_spec.dof
    assert assets.scene_summary['geometry_authority']['authority_kind'] == 'runtime_robot_scene'
    assert assets.scene_summary['geometry_authority']['scene_geometry_contract'] == 'declaration_validation_render'



def test_runtime_asset_service_invalidates_when_runtime_context_changes(planar_spec):
    service = RobotRuntimeAssetService()
    service.build_assets(planar_spec)
    assert service.cache_stats()['entries'] == 1
    service.bind_runtime_context(
        profile_id='research',
        collision_backend_scope='experimental',
        experimental_collision_backends_enabled=True,
    )
    stats = service.cache_stats()
    assert stats['entries'] == 0
    assert stats['invalidations'] >= 1
    assert service.invalidation_log()[-1].reason == 'runtime_context_changed'
