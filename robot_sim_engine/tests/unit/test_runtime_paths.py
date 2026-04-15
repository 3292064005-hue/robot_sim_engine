from __future__ import annotations

from pathlib import Path

import pytest

from robot_sim.app import runtime_paths as runtime_paths_module
from robot_sim.app.runtime_paths import resolve_runtime_paths



def _build_packaged_config_tree(root: Path) -> Path:
    config_root = root / 'packaged' / 'configs'
    (config_root / 'profiles').mkdir(parents=True)
    (config_root / 'robots').mkdir(parents=True)
    (config_root / 'robots' / 'planar_2dof.yaml').write_text('id: planar_2dof\nname: Planar\ndh_rows:\n- a: 1.0\n', encoding='utf-8')
    (config_root / 'logging.yaml').write_text('version: 1\n', encoding='utf-8')
    (config_root / 'plugins.yaml').write_text('{}\n', encoding='utf-8')
    (config_root / 'app.yaml').write_text('window:\n  title: Packaged\n', encoding='utf-8')
    (config_root / 'solver.yaml').write_text('solver:\n  mode: packaged\n', encoding='utf-8')
    (config_root / 'profiles' / 'default.yaml').write_text('window:\n  width: 123\n', encoding='utf-8')
    return config_root



def test_resolve_runtime_paths_uses_packaged_resources_when_source_layout_missing(tmp_path, monkeypatch):
    export_root = tmp_path / 'custom-exports'
    packaged_root = _build_packaged_config_tree(tmp_path)
    monkeypatch.setattr(runtime_paths_module, '_PACKAGE_CONFIG_ROOT', packaged_root)
    monkeypatch.setattr(runtime_paths_module, '_repository_root', lambda: tmp_path / 'missing-repository-root')
    monkeypatch.setenv('ROBOT_SIM_EXPORT_DIR', str(export_root))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'xdg-data'))
    paths = resolve_runtime_paths(tmp_path / 'missing-root')
    assert paths.source_layout_available is False
    assert paths.config_root == packaged_root
    assert paths.logging_config_path.name == 'logging.yaml'
    assert paths.plugin_manifest_path.name == 'plugins.yaml'
    assert paths.export_root == export_root
    assert paths.robot_root == tmp_path / 'xdg-data' / 'robot-sim-engine' / 'robots'
    assert paths.bundled_robot_root == packaged_root / 'robots'
    assert paths.layout_mode == 'packaged'
    assert paths.project_root == packaged_root.parent



def test_resolve_runtime_paths_prefers_source_layout(project_root: Path):
    paths = resolve_runtime_paths(project_root)
    assert paths.source_layout_available is True
    assert paths.config_root == project_root / 'configs'
    assert paths.robot_root == project_root / 'configs' / 'robots'
    assert paths.bundled_robot_root == project_root / 'configs' / 'robots'
    assert paths.export_root == project_root / 'exports'
    assert paths.layout_mode == 'source'



def test_resolve_runtime_paths_uses_repository_source_layout_when_requested_root_is_compatibility_only(tmp_path, project_root: Path):
    paths = resolve_runtime_paths(tmp_path / 'compat-root')
    assert paths.source_layout_available is True
    assert paths.project_root == tmp_path / 'compat-root'
    assert paths.resource_root == project_root
    assert paths.config_root == project_root / 'configs'
    assert paths.robot_root == project_root / 'configs' / 'robots'
    assert paths.export_root == tmp_path / 'compat-root' / 'exports'


def test_resolve_runtime_paths_uses_platform_data_root_for_packaged_exports_and_robot_library(tmp_path, monkeypatch):
    packaged_root = _build_packaged_config_tree(tmp_path)
    monkeypatch.setattr(runtime_paths_module, '_PACKAGE_CONFIG_ROOT', packaged_root)
    monkeypatch.setattr(runtime_paths_module, '_repository_root', lambda: tmp_path / 'missing-repository-root')
    monkeypatch.delenv('ROBOT_SIM_EXPORT_DIR', raising=False)
    monkeypatch.delenv('ROBOT_SIM_EXPORT_POLICY', raising=False)
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'xdg-data'))
    paths = resolve_runtime_paths(tmp_path / 'missing-root')
    assert paths.layout_mode == 'packaged'
    assert paths.project_root == packaged_root.parent
    assert paths.export_root == tmp_path / 'xdg-data' / 'robot-sim-engine' / 'exports'
    assert paths.robot_root == tmp_path / 'xdg-data' / 'robot-sim-engine' / 'robots'



def test_resolve_runtime_paths_supports_legacy_cwd_packaged_export_policy(tmp_path, monkeypatch):
    packaged_root = _build_packaged_config_tree(tmp_path)
    monkeypatch.setattr(runtime_paths_module, '_PACKAGE_CONFIG_ROOT', packaged_root)
    monkeypatch.setattr(runtime_paths_module, '_repository_root', lambda: tmp_path / 'missing-repository-root')
    monkeypatch.delenv('ROBOT_SIM_EXPORT_DIR', raising=False)
    monkeypatch.setenv('ROBOT_SIM_EXPORT_POLICY', 'legacy_cwd')
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'xdg-data'))
    monkeypatch.chdir(tmp_path)
    paths = resolve_runtime_paths(tmp_path / 'missing-root')
    assert paths.project_root == packaged_root.parent
    assert paths.export_root == tmp_path / 'exports'
    assert paths.robot_root == tmp_path / 'xdg-data' / 'robot-sim-engine' / 'robots'



def test_resolve_runtime_paths_fails_fast_when_packaged_resources_are_missing(tmp_path, monkeypatch):
    fake_module_path = tmp_path / 'pkg' / 'app' / 'runtime_paths.py'
    fake_module_path.parent.mkdir(parents=True, exist_ok=True)
    fake_module_path.write_text('# fake runtime paths module location\n', encoding='utf-8')
    monkeypatch.setattr(runtime_paths_module, '_PACKAGE_CONFIG_ROOT', tmp_path / 'missing-packaged-configs')
    monkeypatch.setattr(runtime_paths_module, '_repository_root', lambda: tmp_path / 'missing-repository-root')
    monkeypatch.setattr(runtime_paths_module, '__file__', str(fake_module_path))
    with pytest.raises(FileNotFoundError, match='packaged runtime configs not found'):
        resolve_runtime_paths(tmp_path / 'missing-root')
