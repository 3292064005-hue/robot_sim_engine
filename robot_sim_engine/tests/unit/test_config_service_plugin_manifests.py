from __future__ import annotations

from robot_sim.application.services.config_service import ConfigService


def test_plugin_manifest_paths_include_profile_overlay(project_root):
    service = ConfigService(project_root / 'configs', profile='research', allow_legacy_local_override=False)
    manifest_paths = service.plugin_manifest_paths()
    relative_paths = [path.relative_to(project_root / 'configs').as_posix() for path in manifest_paths]
    assert relative_paths == ['plugins.yaml', 'profiles/research.plugins.yaml']


def test_plugin_manifest_paths_omit_missing_profile_overlay(project_root):
    service = ConfigService(project_root / 'configs', profile='default', allow_legacy_local_override=False)
    manifest_paths = service.plugin_manifest_paths()
    relative_paths = [path.relative_to(project_root / 'configs').as_posix() for path in manifest_paths]
    assert relative_paths == ['plugins.yaml']
