from __future__ import annotations

from pathlib import Path

import pytest

from robot_sim.app import runtime_paths as runtime_paths_module



def test_package_config_root_raises_when_no_packaged_or_source_configs(monkeypatch, tmp_path: Path) -> None:
    missing_packaged_root = tmp_path / 'missing-packaged-configs'
    monkeypatch.setattr(runtime_paths_module, '_PACKAGE_CONFIG_ROOT', missing_packaged_root)

    fake_module_path = tmp_path / 'pkg' / 'app' / 'runtime_paths.py'
    fake_module_path.parent.mkdir(parents=True, exist_ok=True)
    fake_module_path.write_text('# fake runtime paths module location\n', encoding='utf-8')
    monkeypatch.setattr(runtime_paths_module, '__file__', str(fake_module_path))

    with pytest.raises(FileNotFoundError, match='packaged runtime configs not found'):
        runtime_paths_module._package_config_root()
