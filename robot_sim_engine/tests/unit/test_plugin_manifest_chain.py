from __future__ import annotations

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy


def test_plugin_loader_merges_manifest_chain_and_detects_duplicates(tmp_path):
    base_manifest = tmp_path / 'plugins.yaml'
    profile_manifest = tmp_path / 'profiles' / 'research.plugins.yaml'
    profile_manifest.parent.mkdir(parents=True, exist_ok=True)
    base_manifest.write_text('plugins: []\n', encoding='utf-8')
    profile_manifest.write_text(
        'plugins:\n'
        '  - id: demo_solver\n'
        '    kind: solver\n'
        '    factory: robot_sim.plugins.research_dls_solver_plugin:build_plugin\n'
        '    enabled_profiles: [research]\n',
        encoding='utf-8',
    )
    loader = PluginLoader((base_manifest, profile_manifest), policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True))
    manifests = loader.manifests('solver')
    assert len(manifests) == 1
    assert manifests[0].plugin_id == 'demo_solver'

    duplicate_manifest = tmp_path / 'profiles' / 'duplicate.plugins.yaml'
    duplicate_manifest.write_text(
        'plugins:\n'
        '  - id: demo_solver\n'
        '    kind: solver\n'
        '    factory: robot_sim.plugins.research_dls_solver_plugin:build_plugin\n',
        encoding='utf-8',
    )
    duplicate_loader = PluginLoader((base_manifest, profile_manifest, duplicate_manifest), policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True))
    try:
        duplicate_loader.audit()
    except ValueError as exc:
        assert 'duplicate plugin id in manifest chain' in str(exc)
    else:
        raise AssertionError('duplicate manifest chain should fail')
