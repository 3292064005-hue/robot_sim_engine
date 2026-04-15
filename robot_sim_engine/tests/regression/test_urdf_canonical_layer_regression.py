from __future__ import annotations

from robot_sim.app.container import build_container


def test_urdf_model_importer_emits_explicit_canonical_intermediate_layer(project_root, tmp_path):
    urdf = tmp_path / 'serial.urdf'
    urdf.write_text(
        '<robot name="serial">'
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

    assert spec.canonical_model is not None
    assert spec.canonical_model.metadata['canonical_model_contract_version'] == 'v1'
    assert spec.canonical_model.metadata['canonical_model_layer'] == 'urdf_serial_intermediate'
