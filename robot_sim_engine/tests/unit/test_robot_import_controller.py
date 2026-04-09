from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from robot_sim.app.container import build_container
from robot_sim.presentation.main_controller import MainController


def _seed_project(project_root: Path, target_root: Path) -> None:
    shutil.copytree(project_root / 'configs', target_root / 'configs')


def test_import_robot_persists_unique_name_and_loads_runtime_state(project_root: Path, tmp_path: Path) -> None:
    _seed_project(project_root, tmp_path)
    external_dir = tmp_path / 'external_sources'
    external_dir.mkdir()
    source_path = external_dir / 'planar_2dof.yaml'
    source_path.write_text((project_root / 'configs' / 'robots' / 'planar_2dof.yaml').read_text(encoding='utf-8'), encoding='utf-8')

    controller = MainController(tmp_path, container=build_container(tmp_path))
    result = controller.import_robot(str(source_path), importer_id='yaml')

    assert result.persisted_path.exists()
    assert result.persisted_path.parent == tmp_path / 'configs' / 'robots'
    assert result.persisted_name == 'planar_2dof_2'
    assert result.importer_id == 'yaml'
    assert controller.state.robot_spec is not None
    assert controller.state.robot_spec.name == 'planar_2dof_2'
    assert controller.state.robot_geometry is not None
    assert controller.state.planning_scene is not None
    assert controller.state.scene_summary['geometry_source'] in {'yaml', 'dh_config'}
    persisted_payload = yaml.safe_load(result.persisted_path.read_text(encoding='utf-8'))
    assert persisted_payload['id'] == 'planar_2dof_2'


def test_import_robot_uses_existing_library_path_without_forced_rename(project_root: Path, tmp_path: Path) -> None:
    _seed_project(project_root, tmp_path)
    library_yaml = tmp_path / 'configs' / 'robots' / 'planar_2dof.yaml'

    controller = MainController(tmp_path, container=build_container(tmp_path))
    result = controller.import_robot(str(library_yaml), importer_id='yaml')

    assert result.persisted_path == library_yaml
    assert controller.state.robot_spec is not None
    assert controller.state.robot_spec.name == 'planar_2dof'
    assert controller.state.robot_geometry is not None
    assert controller.state.planning_scene is not None
