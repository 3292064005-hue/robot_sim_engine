from __future__ import annotations

from robot_sim.app.container import build_container


def test_urdf_model_importer_collapses_fixed_prefix_chain(project_root, tmp_path):
    urdf = tmp_path / 'fixed_prefix.urdf'
    urdf.write_text(
        '<robot name="fixed_prefix">'
        '<link name="base"/>'
        '<link name="mount"/>'
        '<link name="tip"/>'
        '<joint name="mount_fixed" type="fixed">'
        '<parent link="base"/><child link="mount"/><origin xyz="0 0 0.2" rpy="0 0 0"/>'
        '</joint>'
        '<joint name="j1" type="revolute">'
        '<parent link="mount"/><child link="tip"/>'
        '<origin xyz="0 0 0.8" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-1" upper="1"/>'
        '</joint>'
        '</robot>',
        encoding='utf-8',
    )
    container = build_container(project_root)
    spec = container.import_robot_uc.execute(urdf, importer_id='urdf')

    assert spec.metadata['importer_resolved'] == 'urdf_model'
    assert spec.dof == 1
    assert spec.joint_names == ('j1',)
    assert spec.structured_joints[0].parent_link == 'base'
    assert float(spec.dh_rows[0].d) == 1.0
    assert any('fixed joints were collapsed' in item for item in spec.metadata.get('warnings', []))
    contract = spec.source_model_summary['runtime_fidelity_contract']
    assert contract['runtime_family'] == 'articulated_serial_tree'
    assert any(item['kind'] == 'fixed_joints_collapsed' for item in contract['downgrade_records'])


def test_urdf_model_importer_selects_best_root_over_orphan_root(project_root, tmp_path):
    urdf = tmp_path / 'multi_root.urdf'
    urdf.write_text(
        '<robot name="multi_root">'
        '<link name="orphan"/>'
        '<link name="base"/>'
        '<link name="tip"/>'
        '<joint name="j1" type="revolute">'
        '<parent link="base"/><child link="tip"/>'
        '<origin xyz="0 0 1" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-1" upper="1"/>'
        '</joint>'
        '</robot>',
        encoding='utf-8',
    )
    container = build_container(project_root)
    spec = container.import_robot_uc.execute(urdf, importer_id='urdf')

    assert spec.metadata['importer_resolved'] == 'urdf_model'
    assert spec.dof == 1
    assert spec.source_model_summary['joint_count'] == 1
    assert spec.source_model_summary['root_link'] == 'base'
    assert any('multiple disconnected root candidates' in item for item in spec.metadata.get('warnings', []))
    contract = spec.source_model_summary['runtime_fidelity_contract']
    assert contract['selected_root_link'] == 'base'
    assert any(item['kind'] == 'disconnected_roots' for item in contract['downgrade_records'])
