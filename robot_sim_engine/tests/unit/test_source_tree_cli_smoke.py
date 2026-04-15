from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_source_tree_cli_smoke_is_side_effect_free_and_reports_bootstrap_consistent_paths(project_root, tmp_path):
    export_root = tmp_path / 'probe_exports'
    env = dict(os.environ)
    env['ROBOT_SIM_EXPORT_DIR'] = str(export_root)
    completed = subprocess.run(
        [sys.executable, '-m', 'robot_sim.app.cli', 'source-layout-smoke'],
        cwd=project_root / 'src',
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    payload = json.loads(completed.stdout)
    assert payload['entrypoint_mode'] == 'python -m robot_sim.app.cli'
    assert payload['layout_mode'] == 'source'
    assert payload['source_layout_available'] is True
    assert payload['project_root'] == str(project_root)
    assert payload['side_effect_free_probe'] is True
    assert payload['export_root'] == str(Path(env['ROBOT_SIM_EXPORT_DIR']))
    assert not export_root.exists()


def test_packaged_runtime_paths_project_root_tracks_packaged_resource_root(tmp_path, monkeypatch):
    from robot_sim.app import runtime_paths as runtime_paths_module
    from robot_sim.app.runtime_paths import resolve_runtime_paths

    config_root = tmp_path / 'wheel_root' / 'robot_sim' / 'resources' / 'configs'
    (config_root / 'profiles').mkdir(parents=True)
    (config_root / 'robots').mkdir(parents=True)
    (config_root / 'logging.yaml').write_text('version: 1\n', encoding='utf-8')
    (config_root / 'plugins.yaml').write_text('{}\n', encoding='utf-8')
    (config_root / 'app.yaml').write_text('window:\n  title: Wheel\n', encoding='utf-8')
    (config_root / 'solver.yaml').write_text('solver:\n  mode: packaged\n', encoding='utf-8')
    (config_root / 'profiles' / 'default.yaml').write_text('window:\n  width: 321\n', encoding='utf-8')
    monkeypatch.setattr(runtime_paths_module, '_PACKAGE_CONFIG_ROOT', config_root)
    monkeypatch.setattr(runtime_paths_module, '_repository_root', lambda: tmp_path / 'missing-repository-root')
    paths = resolve_runtime_paths(tmp_path / 'ignored-root', create_dirs=False)
    assert paths.layout_mode == 'packaged'
    assert paths.project_root == config_root.parent
    assert paths.resource_root == config_root.parent
