import sys
from pathlib import Path

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy


def test_plugin_loader_resolves_whitelisted_factory(tmp_path: Path, monkeypatch):
    plugin_module = tmp_path / 'demo_plugin.py'
    plugin_module.write_text(
        'class DemoSolver:\n'
        '    pass\n\n'
        'def build_plugin():\n'
        '    return {\"instance\": DemoSolver(), \"metadata\": {\"family\": \"iterative\"}, \"aliases\": (\"demo_alias\",)}\n',
        encoding='utf-8',
    )
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: demo_solver\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    enabled_profiles: [research]\n',
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.path.insert(0, str(tmp_path))
    try:
        loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True))
        registrations = loader.registrations('solver')
        assert len(registrations) == 1
        registration = registrations[0]
        assert registration.plugin_id == 'demo_solver'
        assert registration.aliases == ('demo_alias',)
        assert registration.metadata['family'] == 'iterative'
        assert registration.metadata['sdk_contract_version'] == 'v1'
        assert registration.metadata['min_host_version'] == ''
    finally:
        while str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


def test_shipped_plugin_manifest_loads_without_external_discovery(tmp_path: Path, monkeypatch):
    plugin_module = tmp_path / 'demo_plugin.py'
    plugin_module.write_text(
        'def build_plugin():\n'
        '    return {"instance": object(), "metadata": {"family": "iterative"}}\n',
        encoding='utf-8',
    )
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: shipped_demo\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    source: shipped_plugin\n'
        '    api_version: v1\n'
        '    enabled_profiles: [dev]\n',
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='dev', plugin_discovery_enabled=False))
    registrations = loader.registrations('solver')
    assert len(registrations) == 1
    assert registrations[0].plugin_id == 'shipped_demo'
    assert registrations[0].metadata['api_version'] == 'v1'
    assert registrations[0].metadata['sdk_contract_version'] == 'v1'


def test_plugin_loader_projects_governance_only_aliases_into_compatibility_map(tmp_path: Path, monkeypatch):
    plugin_module = tmp_path / 'demo_plugin.py'
    plugin_module.write_text(
        'def build_plugin():\n'
        '    return {"instance": object(), "metadata": {"runtime_provider_id": "lm"}}\n',
        encoding='utf-8',
    )
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: shipped_demo_alias\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    source: shipped_plugin\n'
        '    enabled_profiles: [default]\n'
        '    metadata:\n'
        '      canonical_target: lm\n',
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='default'))
    assert loader.capability_registrations('solver') == ()
    assert loader.compatibility_aliases('solver') == {'shipped_demo_alias': 'lm'}
