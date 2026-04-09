from __future__ import annotations

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.runtime_feature_service import RuntimeFeatureService


def _research_loader(project_root):
    research_policy = RuntimeFeatureService(
        ConfigService(project_root / 'configs', profile='research', allow_legacy_local_override=False)
    ).load_policy()
    manifest_path = project_root / 'configs' / 'plugins.yaml'
    return PluginLoader(manifest_path, policy=research_policy)


def _default_loader(project_root):
    default_policy = RuntimeFeatureService(
        ConfigService(project_root / 'configs', profile='default', allow_legacy_local_override=False)
    ).load_policy()
    manifest_path = project_root / 'configs' / 'plugins.yaml'
    return PluginLoader(manifest_path, policy=default_policy)


def test_shipped_research_solver_plugin_manifest_is_only_loaded_for_research_profile(project_root):
    default_loader = _default_loader(project_root)
    research_loader = _research_loader(project_root)

    assert default_loader.manifests('solver') == ()
    registrations = research_loader.registrations('solver')
    assert len(registrations) == 1
    registration = registrations[0]
    assert registration.plugin_id == 'research_demo_dls'
    assert registration.aliases == ('research_demo',)
    assert registration.metadata['family'] == 'iterative'
    assert registration.metadata['verification_scope'] == 'registry_smoke'
    assert registration.metadata['sdk_contract_version'] == 'v1'
    assert registration.metadata['min_host_version'] == '0.7.0'
    assert registration.source == 'shipped_plugin'


def test_shipped_research_planner_plugin_manifest_is_only_loaded_for_research_profile(project_root):
    default_loader = _default_loader(project_root)
    research_loader = _research_loader(project_root)

    assert default_loader.manifests('planner') == ()
    registrations = research_loader.registrations('planner', ik_uc=object())
    assert len(registrations) == 1
    registration = registrations[0]
    assert registration.plugin_id == 'research_demo_cartesian_planner'
    assert registration.aliases == ('research_cartesian',)
    assert registration.metadata['family'] == 'cartesian'
    assert registration.metadata['verification_scope'] == 'registry_smoke'
    assert registration.metadata['sdk_contract_version'] == 'v1'
    assert registration.metadata['min_host_version'] == '0.7.0'
    assert registration.source == 'shipped_plugin'


def test_shipped_research_importer_plugin_manifest_is_only_loaded_for_research_profile(project_root):
    default_loader = _default_loader(project_root)
    research_loader = _research_loader(project_root)

    assert default_loader.manifests('importer') == ()
    registrations = research_loader.registrations('importer', robot_registry=object())
    assert len(registrations) == 1
    registration = registrations[0]
    assert registration.plugin_id == 'research_demo_yaml_importer'
    assert registration.aliases == ('research_yaml',)
    assert registration.metadata['source_format'] == 'yaml'
    assert registration.metadata['fidelity'] == 'native'
    assert registration.metadata['verification_scope'] == 'registry_smoke'
    assert registration.metadata['sdk_contract_version'] == 'v1'
    assert registration.metadata['min_host_version'] == '0.7.0'
    assert registration.source == 'shipped_plugin'
