from __future__ import annotations

import numpy as np

from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.application.validators.collision_validator import evaluate_collision_summary
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.core.collision.scene import SceneObject


def test_planar_yaml_import_populates_canonical_model(project_root):
    registry = RobotRegistry(project_root / 'configs' / 'robots')
    spec = registry.load('planar_2dof')
    assert spec.canonical_model is not None
    assert spec.canonical_model.source_format == 'yaml'
    assert spec.canonical_model.execution_adapter == 'canonical_dh_chain'
    assert spec.execution_rows == spec.canonical_model.execution_rows
    assert spec.runtime_joint_names == spec.canonical_model.joint_names
    assert spec.runtime_link_names == spec.canonical_model.link_names
    assert spec.execution_summary['execution_adapter'] == 'canonical_dh_chain'
    assert spec.execution_summary['execution_surface'] == 'canonical_model'
    assert spec.execution_summary['execution_row_count'] == spec.dof
    runtime_summary = spec.runtime_model.summary()
    assert runtime_summary['semantic_family'] == 'articulated_serial_tree'
    assert runtime_summary['source_surface'] == 'canonical_model'
    assert runtime_summary['execution_row_count'] == spec.dof


def test_robot_registry_roundtrip_preserves_canonical_model(project_root, tmp_path):
    registry = RobotRegistry(tmp_path)
    source_registry = RobotRegistry(project_root / 'configs' / 'robots')
    spec = source_registry.load('planar_2dof')
    registry.save(spec)
    loaded = registry.load('planar_2dof')
    assert loaded.canonical_model is not None
    assert loaded.canonical_model.summary()['joint_count'] == spec.dof
    assert loaded.runtime_joint_limits[0].lower == spec.runtime_joint_limits[0].lower
    assert loaded.runtime_model.summary()['joint_names'] == list(spec.runtime_joint_names)


def test_runtime_asset_service_enables_capsule_backend_under_experimental_policy(planar_spec):
    service = RobotRuntimeAssetService(experimental_collision_backends_enabled=True)
    assets = service.build_assets(planar_spec)
    assert assets.planning_scene.collision_backend == 'capsule'
    assert assets.planning_scene.metadata['resolved_collision_backend'] == 'capsule'
    assert len(assets.planning_scene.metadata['collision_link_radii']) == planar_spec.dof


def test_collision_validator_uses_capsule_backend_when_scene_requests_it(planar_spec):
    service = RobotRuntimeAssetService(experimental_collision_backends_enabled=True)
    assets = service.build_assets(planar_spec)
    joint_positions = np.array([
        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [1.0, 0.0, 0.0]],
        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [1.0, 0.0, 0.0]],
    ], dtype=float)
    trajectory = type('Trajectory', (), {'joint_positions': joint_positions, 'metadata': {}})()
    obstacle = SceneObject('wall', aabb_from_points(np.array([[0.49, -0.02, -0.02], [0.51, 0.02, 0.02]], dtype=float), padding=0.0))
    scene = assets.planning_scene.replace_obstacles((obstacle,))
    _, summary = evaluate_collision_summary(trajectory, planning_scene=scene)
    assert summary['resolved_backend'] == 'capsule'
    assert summary['environment_collision'] is True
    assert ('link_0', 'wall') in summary['environment_pairs']


def test_urdf_import_uses_articulated_execution_adapter(project_root, tmp_path):
    from robot_sim.app.container import build_container

    urdf = tmp_path / 'structured.urdf'
    urdf.write_text(
        '<robot name="mini">'
        '<link name="base"><visual><geometry><box size="1 1 1"/></geometry></visual></link>'
        '<link name="tip"><collision><geometry><sphere radius="0.1"/></geometry></collision></link>'
        '<joint name="j1" type="revolute">'
        '<parent link="base"/><child link="tip"/>'
        '<origin xyz="0 0 1" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-1" upper="1"/>'
        '</joint></robot>',
        encoding='utf-8',
    )
    container = build_container(project_root)
    spec = container.import_robot_uc.execute(urdf, importer_id='urdf')

    assert spec.canonical_model is not None
    assert spec.canonical_model.execution_adapter == 'canonical_articulated_chain'
    assert spec.execution_summary['execution_adapter'] == 'canonical_articulated_chain'
    assert spec.runtime_model.summary()['execution_adapter'] == 'canonical_articulated_chain'
    assert spec.runtime_model.summary()['semantic_family'] == 'articulated_serial_tree'
