from __future__ import annotations

from pathlib import Path

from robot_sim.application.importers.urdf_model_importer import URDFModelImporter
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
from robot_sim.model.imported_robot_package import ImportedRobotPackage
from robot_sim.model.robot_model_bundle import RobotModelBundle


class _ImporterRegistryStub:
    def __init__(self, importer) -> None:
        self._importer = importer
        self._metadata = {'urdf_model': type('Descriptor', (), {'metadata': {'family': 'serial_model_import'}})()}

    def resolve_id(self, importer_id: str) -> str:
        return str(importer_id)

    def get(self, importer_id: str):
        assert importer_id == 'urdf_model'
        return self._importer


def test_import_robot_use_case_builds_imported_package(tmp_path: Path) -> None:
    source = tmp_path / 'planar_2r.urdf'
    source.write_text(
        '<robot name="planar_2r">\n'
        '  <link name="base"/>\n'
        '  <link name="link_1"/>\n'
        '  <link name="link_2"/>\n'
        '  <joint name="joint_1" type="revolute">\n'
        '    <parent link="base"/>\n'
        '    <child link="link_1"/>\n'
        '    <origin xyz="1 0 0" rpy="0 0 0"/>\n'
        '    <axis xyz="0 0 1"/>\n'
        '    <limit lower="-3.14" upper="3.14"/>\n'
        '  </joint>\n'
        '  <joint name="joint_2" type="revolute">\n'
        '    <parent link="link_1"/>\n'
        '    <child link="link_2"/>\n'
        '    <origin xyz="1 0 0" rpy="0 0 0"/>\n'
        '    <axis xyz="0 0 1"/>\n'
        '    <limit lower="-3.14" upper="3.14"/>\n'
        '  </joint>\n'
        '</robot>\n',
        encoding='utf-8',
    )
    use_case = ImportRobotUseCase(_ImporterRegistryStub(URDFModelImporter()))
    bundle = use_case.execute_bundle(source, importer_id='urdf_model')
    assert isinstance(bundle, RobotModelBundle)
    assert isinstance(bundle.imported_package, ImportedRobotPackage)
    summary = bundle.imported_package.summary()
    assert summary['runtime_model']['semantic_family'] == 'articulated_serial_tree'
    assert summary['runtime_model']['execution_adapter'] == 'canonical_articulated_chain'
    assert summary['articulated_model']['semantic_family'] == 'articulated_serial_tree'
    assert summary['geometry_model']['geometry_contract'] == 'split_visual_collision'
    assert summary['fidelity_breakdown']['runtime_executable'] is True
    assert summary['fidelity_breakdown']['source_recovered'] is True


def test_robot_registry_round_trips_imported_package_summaries(tmp_path: Path, project_root) -> None:
    from robot_sim.app.container import build_container

    source = tmp_path / 'registry_roundtrip.urdf'
    source.write_text(
        '<robot name="registry_roundtrip">\n'
        '  <link name="base"/>\n'
        '  <link name="link_1"/>\n'
        '  <joint name="joint_1" type="revolute">\n'
        '    <parent link="base"/>\n'
        '    <child link="link_1"/>\n'
        '    <origin xyz="1 0 0" rpy="0 0 0"/>\n'
        '    <axis xyz="0 0 1"/>\n'
        '    <limit lower="-3.14" upper="3.14"/>\n'
        '  </joint>\n'
        '</robot>\n',
        encoding='utf-8',
    )
    container = build_container(project_root)
    spec = container.import_robot_uc.execute(source, importer_id='urdf')

    registry = RobotRegistry(tmp_path / 'registry_store')
    registry.save(spec)
    loaded = registry.load(spec.name)
    assert loaded.imported_package is not None
    assert loaded.imported_package.runtime_model.semantic_family == 'articulated_serial_tree'
    assert loaded.imported_package.runtime_model.execution_adapter == 'canonical_articulated_chain'
    assert loaded.imported_package.articulated_model is not None
    assert loaded.imported_package.articulated_model.semantic_family == 'articulated_serial_tree'
    assert 'runtime_model_summary' not in loaded.metadata
    assert 'articulated_model_summary' not in loaded.metadata
