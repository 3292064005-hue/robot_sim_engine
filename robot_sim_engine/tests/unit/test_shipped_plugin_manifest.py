from __future__ import annotations

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.runtime_feature_service import RuntimeFeatureService


def _loader(project_root, *, profile: str):
    config = ConfigService(project_root / 'configs', profile=profile, allow_legacy_local_override=False)
    policy = RuntimeFeatureService(config).load_policy()
    return PluginLoader(config.plugin_manifest_paths(), policy=policy)


def test_default_profile_loads_stable_shipped_plugins_and_reserved_plugin_kinds(project_root):
    loader = _loader(project_root, profile='default')
    solver_ids = {manifest.plugin_id for manifest in loader.manifests('solver')}
    planner_ids = {manifest.plugin_id for manifest in loader.manifests('planner')}
    importer_ids = {manifest.plugin_id for manifest in loader.manifests('importer')}
    scene_backend_ids = {manifest.plugin_id for manifest in loader.manifests('scene_backend')}
    collision_backend_ids = {manifest.plugin_id for manifest in loader.manifests('collision_backend')}

    assert solver_ids == {'stable_demo_lm'}
    assert planner_ids == {'stable_demo_joint_planner'}
    assert importer_ids == {'stable_demo_yaml_importer'}
    assert scene_backend_ids == {'stable_demo_scene_backend_contract'}
    assert collision_backend_ids == {'stable_demo_collision_backend_contract'}


def test_research_profile_loads_research_profile_plugins_while_reserved_stable_surfaces_remain_profile_scoped(project_root):
    loader = _loader(project_root, profile='research')
    solver_ids = {manifest.plugin_id for manifest in loader.manifests('solver')}
    planner_ids = {manifest.plugin_id for manifest in loader.manifests('planner')}
    importer_ids = {manifest.plugin_id for manifest in loader.manifests('importer')}
    scene_backend_ids = {manifest.plugin_id for manifest in loader.manifests('scene_backend')}
    collision_backend_ids = {manifest.plugin_id for manifest in loader.manifests('collision_backend')}

    assert solver_ids == {'research_demo_dls'}
    assert planner_ids == {'research_demo_cartesian_planner'}
    assert importer_ids == {'research_demo_yaml_importer'}
    assert scene_backend_ids == set()
    assert collision_backend_ids == set()


def test_profile_manifest_chain_stays_profile_scoped(project_root):
    default_audit = {row['id']: row for row in _loader(project_root, profile='default').audit()}
    research_audit = {row['id']: row for row in _loader(project_root, profile='research').audit()}

    assert default_audit['stable_demo_scene_backend_contract']['enabled'] is True
    assert default_audit['stable_demo_collision_backend_contract']['enabled'] is True
    assert 'research_demo_dls' not in default_audit
    assert 'research_demo_cartesian_planner' not in default_audit
    assert 'research_demo_yaml_importer' not in default_audit
    assert research_audit['research_demo_dls']['enabled'] is True
    assert research_audit['research_demo_cartesian_planner']['enabled'] is True
    assert research_audit['research_demo_yaml_importer']['enabled'] is True
    assert research_audit['stable_demo_lm']['enabled'] is False
    assert research_audit['stable_demo_scene_backend_contract']['enabled'] is False
    assert research_audit['stable_demo_collision_backend_contract']['enabled'] is False
    assert research_audit['stable_demo_scene_backend_contract']['reason'] == 'profile_disabled'
