from __future__ import annotations

from dataclasses import replace

import numpy as np

from robot_sim.app.container import build_container
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.application.dto import FKRequest
from robot_sim.presentation.state_store import StateStore


def _build_structured_spec(project_root, tmp_path):
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
    return container.import_robot_uc.execute(urdf, importer_id='urdf')


def test_build_robot_from_editor_invalidates_structured_source_after_dh_edit(project_root, tmp_path):
    structured_spec = _build_structured_spec(project_root, tmp_path)
    controller = RobotController(StateStore(), RobotRegistry(tmp_path), build_container(project_root).fk_uc)

    edited_rows = list(structured_spec.dh_rows)
    edited_rows[0] = replace(edited_rows[0], a=float(edited_rows[0].a) + 0.05)
    edited = controller.build_robot_from_editor(structured_spec, edited_rows, structured_spec.home_q)

    assert edited.structured_joints == ()
    assert edited.structured_links == ()
    assert edited.kinematic_source == 'dh_config'
    assert edited.geometry_bundle_ref == ''
    assert edited.collision_bundle_ref == ''
    assert edited.metadata['source_model_invalidated'] is True
    assert edited.source_model_summary['forked_runtime_model'] is True


def test_build_robot_from_editor_preserves_structured_source_when_only_home_changes(project_root, tmp_path):
    structured_spec = _build_structured_spec(project_root, tmp_path)
    controller = RobotController(StateStore(), RobotRegistry(tmp_path), build_container(project_root).fk_uc)

    edited = controller.build_robot_from_editor(
        structured_spec,
        structured_spec.dh_rows,
        np.array([0.2], dtype=float),
    )

    assert edited.structured_joints
    assert edited.geometry_bundle_ref == structured_spec.geometry_bundle_ref
    assert edited.collision_bundle_ref == structured_spec.collision_bundle_ref
    assert edited.metadata.get('source_model_invalidated', False) is False


def test_save_current_robot_recomputes_runtime_fk_after_editor_change(project_root, tmp_path):
    container = build_container(project_root)
    registry = RobotRegistry(tmp_path, readonly_roots=(project_root / 'configs' / 'robots',))
    controller = RobotController(StateStore(), registry, container.fk_uc)

    controller.load_robot('planar_2dof')
    loaded_spec = controller._state_store.state.robot_spec
    edited_rows = list(loaded_spec.dh_rows)
    edited_rows[0] = replace(edited_rows[0], a=float(edited_rows[0].a) + 0.5)

    controller.save_current_robot(rows=edited_rows, home_q=loaded_spec.home_q, name='planar_2dof_edited')

    runtime_spec = controller._state_store.state.robot_spec
    runtime_fk = controller._state_store.state.fk_result
    expected_fk = container.fk_uc.execute(FKRequest(runtime_spec, runtime_spec.home_q.copy()))

    assert np.allclose(runtime_fk.ee_pose.p, expected_fk.ee_pose.p)
    assert np.allclose(controller._state_store.state.q_current, runtime_spec.home_q)


def test_imported_geometry_round_trips_through_registry_load(project_root, tmp_path):
    urdf = tmp_path / 'structured_roundtrip.urdf'
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
    registry = RobotRegistry(tmp_path)
    controller = RobotController(StateStore(), registry, container.fk_uc, import_robot_uc=container.import_robot_uc)

    result = controller.import_robot(str(urdf), importer_id='urdf')

    reloaded = registry.load(result.persisted_name)
    from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
    reloaded_assets = RobotRuntimeAssetService().build_assets(reloaded)

    assert reloaded.metadata['geometry_available'] is True
    assert reloaded_assets.robot_geometry is not None
    assert len(reloaded_assets.robot_geometry.links) >= 2
    assert reloaded_assets.robot_geometry.source == 'urdf_model'


def test_save_current_robot_save_as_updates_runtime_identity(project_root, tmp_path):
    container = build_container(project_root)
    registry = RobotRegistry(tmp_path, readonly_roots=(project_root / 'configs' / 'robots',))
    controller = RobotController(StateStore(), registry, container.fk_uc)

    controller.load_robot('planar_2dof')
    path = controller.save_current_robot(name='planar_2dof_copy')

    runtime_spec = controller._state_store.state.robot_spec
    assert path.stem == 'planar_2dof_copy'
    assert runtime_spec.name == 'planar_2dof_copy'
    assert controller._state_store.state.fk_result is not None
