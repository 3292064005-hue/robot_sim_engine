from __future__ import annotations

from pathlib import Path

from robot_sim.application.dto import FKRequest
from robot_sim.application.importers.urdf_model_importer import URDFModelImporter
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.application.use_cases.import_robot import ImportRobotUseCase


class _ImporterRegistryStub:
    def __init__(self, importer) -> None:
        self._importer = importer
        self._metadata = {'urdf_model': type('Descriptor', (), {'metadata': {'family': 'serial_model_import'}})()}

    def resolve_id(self, importer_id: str) -> str:
        return str(importer_id)

    def get(self, importer_id: str):
        assert importer_id == 'urdf_model'
        return self._importer


def test_branching_urdf_preserves_articulated_graph_and_scene_projection(tmp_path: Path) -> None:
    source = tmp_path / 'branching.urdf'
    source.write_text(
        '<robot name="branching">\n'
        '  <link name="base"/>\n'
        '  <link name="shoulder"/>\n'
        '  <link name="left_tip"/>\n'
        '  <link name="right_tip"/>\n'
        '  <joint name="joint_base" type="revolute">\n'
        '    <parent link="base"/><child link="shoulder"/>\n'
        '    <origin xyz="0 0 0.2" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-1.5" upper="1.5"/>\n'
        '  </joint>\n'
        '  <joint name="joint_left" type="revolute">\n'
        '    <parent link="shoulder"/><child link="left_tip"/>\n'
        '    <origin xyz="0.5 0 0" rpy="0 0 0"/><axis xyz="0 1 0"/><limit lower="-1.0" upper="1.0"/>\n'
        '  </joint>\n'
        '  <joint name="joint_right" type="revolute">\n'
        '    <parent link="shoulder"/><child link="right_tip"/>\n'
        '    <origin xyz="0.5 0 0" rpy="0 0 0"/><axis xyz="0 1 0"/><limit lower="-1.0" upper="1.0"/>\n'
        '  </joint>\n'
        '</robot>\n',
        encoding='utf-8',
    )
    use_case = ImportRobotUseCase(_ImporterRegistryStub(URDFModelImporter()))
    spec = use_case.execute(source, importer_id='urdf_model')

    contract = spec.source_model_summary['runtime_fidelity_contract']
    graph_layer = contract['articulated_graph_layer']
    assert contract['branched_tree_supported'] is True
    assert graph_layer['supports_branched_tree_projection'] is True
    assert graph_layer['branching_link_names'] == ['shoulder']
    assert ['shoulder', 'left_tip'] in graph_layer['graph_edge_pairs']
    assert ['shoulder', 'right_tip'] in graph_layer['graph_edge_pairs']
    assert all(record['kind'] != 'branching_tree_pruned' for record in contract['downgrade_records'])

    assert spec.imported_package is not None
    articulated = spec.imported_package.articulated_model
    assert articulated is not None
    assert articulated.semantic_family == 'articulated_tree_projection'
    assert articulated.topology_summary['leaf_count'] == 2
    assert articulated.topology_summary['branching_joint_names'] == ['joint_base']

    assets = RobotRuntimeAssetService().build_assets(spec)
    edges = set(assets.planning_scene.scene_graph_authority.attachment_edges)
    assert ('base', 'shoulder') in edges
    assert ('shoulder', 'left_tip') in edges
    assert ('shoulder', 'right_tip') in edges


def test_branching_urdf_fk_uses_active_execution_path(tmp_path: Path) -> None:
    source = tmp_path / 'branching_fk.urdf'
    source.write_text(
        '<robot name="branching_fk">\n'
        '  <link name="base"/>\n'
        '  <link name="shoulder"/>\n'
        '  <link name="left_tip"/>\n'
        '  <link name="right_tip"/>\n'
        '  <joint name="joint_base" type="revolute">\n'
        '    <parent link="base"/><child link="shoulder"/>\n'
        '    <origin xyz="0 0 0.2" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-1.5" upper="1.5"/>\n'
        '  </joint>\n'
        '  <joint name="joint_left" type="revolute">\n'
        '    <parent link="shoulder"/><child link="left_tip"/>\n'
        '    <origin xyz="0.5 0 0" rpy="0 0 0"/><axis xyz="0 1 0"/><limit lower="-1.0" upper="1.0"/>\n'
        '  </joint>\n'
        '  <joint name="joint_right" type="revolute">\n'
        '    <parent link="shoulder"/><child link="right_tip"/>\n'
        '    <origin xyz="0.6 0 0" rpy="0 0 0"/><axis xyz="0 1 0"/><limit lower="-1.0" upper="1.0"/>\n'
        '  </joint>\n'
        '</robot>\n',
        encoding='utf-8',
    )
    use_case = ImportRobotUseCase(_ImporterRegistryStub(URDFModelImporter()))
    spec = use_case.execute(source, importer_id='urdf_model')

    result = use_case.fk_use_case.execute(FKRequest(spec=spec, q=spec.home_q)) if hasattr(use_case, 'fk_use_case') else None
    if result is None:
        from robot_sim.application.use_cases.run_fk import RunFKUseCase

        result = RunFKUseCase().execute(FKRequest(spec=spec, q=spec.home_q))
    topology = spec.execution_summary['articulated_topology']
    assert topology['execution_semantics'] == 'tree_active_path'
    assert topology['execution_joint_indices'] in ([0, 1], [0, 2])
    assert result.metadata['execution_semantics'] == 'tree_active_path'
    assert result.metadata['execution_joint_indices'] == topology['execution_joint_indices']

