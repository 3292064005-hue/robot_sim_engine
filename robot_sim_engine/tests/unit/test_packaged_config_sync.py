from __future__ import annotations

from pathlib import Path

from robot_sim.infra.packaged_config_sync import (
    build_lib_config_root,
    install_packaged_configs,
    packaged_config_root,
    source_config_root,
    sync_packaged_configs,
    verify_packaged_config_sync,
)


def test_packaged_config_sync_detects_and_repairs_drift(tmp_path: Path) -> None:
    source_root = source_config_root(tmp_path)
    packaged_root = packaged_config_root(tmp_path)
    (source_root / 'profiles').mkdir(parents=True)
    (packaged_root / 'profiles').mkdir(parents=True)
    (source_root / 'app.yaml').write_text('window:\n  title: Source\n', encoding='utf-8')
    (source_root / 'profiles' / 'default.yaml').write_text('window:\n  width: 123\n', encoding='utf-8')
    (packaged_root / 'app.yaml').write_text('window:\n  title: Drift\n', encoding='utf-8')
    (packaged_root / 'profiles' / 'extra.yaml').write_text('{}\n', encoding='utf-8')

    errors = verify_packaged_config_sync(tmp_path)
    assert 'staged config drift: app.yaml' in errors
    assert 'extraneous staged config: profiles/extra.yaml' in errors

    summary = sync_packaged_configs(tmp_path)
    assert summary['copied'] >= 1
    assert summary['removed'] == 1
    assert verify_packaged_config_sync(tmp_path) == []


def test_install_packaged_configs_populates_build_lib(tmp_path: Path) -> None:
    source_root = source_config_root(tmp_path)
    (source_root / 'profiles').mkdir(parents=True)
    (source_root / 'app.yaml').write_text('window:\n  title: Source\n', encoding='utf-8')
    (source_root / 'profiles' / 'default.yaml').write_text('window:\n  width: 123\n', encoding='utf-8')

    summary = install_packaged_configs(tmp_path / 'build-lib', tmp_path)
    installed_root = build_lib_config_root(tmp_path / 'build-lib')

    assert summary['copied'] == 2
    assert (installed_root / 'app.yaml').read_text(encoding='utf-8') == 'window:\n  title: Source\n'
    assert (installed_root / 'profiles' / 'default.yaml').exists()
