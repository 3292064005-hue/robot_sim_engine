from __future__ import annotations

from robot_sim.app.container import build_container


def test_import_robot_use_case_records_skeleton_fidelity_warning(project_root, tmp_path):
    urdf = tmp_path / 'mini.urdf'
    urdf.write_text(
        '<robot name="mini"><joint name="j1" type="revolute"><origin xyz="0 0 1" rpy="0 0 0"/><limit lower="-1" upper="1"/></joint></robot>',
        encoding='utf-8',
    )
    container = build_container(project_root)
    spec = container.import_robot_uc.execute(urdf, importer_id='urdf_skeleton')

    assert spec.metadata['importer_resolved'] == 'urdf_skeleton'
    assert any('urdf_skeleton fidelity' in item for item in spec.metadata.get('warnings', []))


def test_import_robot_use_case_records_structured_urdf_summary(project_root, tmp_path):
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

    assert spec.metadata['importer_resolved'] == 'urdf_model'
    assert spec.source_model_summary['joint_count'] == 1
    assert spec.source_model_summary['has_visual'] is True
    assert spec.source_model_summary['has_collision'] is True
    contract = spec.source_model_summary['runtime_fidelity_contract']
    assert contract['execution_adapter'] == 'canonical_articulated_chain'
    assert contract['runtime_dispatch']['primary_execution_adapter'] == 'canonical_articulated_chain'
    assert contract['runtime_dispatch']['compatibility_execution_adapters'] == ['canonical_dh_chain']
    assert contract['selected_dynamic_joint_count'] == 1


def test_import_robot_use_case_keeps_geometry_in_typed_package_not_metadata(project_root, tmp_path):
    urdf = tmp_path / 'geometry.urdf'
    urdf.write_text(
        '<robot name="geo">'
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

    assert spec.imported_package is not None
    assert spec.imported_package.geometry_model is not None
    assert spec.metadata.get('serialized_robot_geometry') is None
    assert spec.metadata.get('serialized_collision_geometry') is None
    assert spec.geometry_bundle_ref == 'spec.imported_package.geometry_model.visual_geometry'
    assert spec.collision_bundle_ref == 'spec.imported_package.geometry_model.collision_geometry'
