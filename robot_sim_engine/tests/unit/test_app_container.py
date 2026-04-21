from __future__ import annotations

from robot_sim.app.container import build_container


def test_build_container_exposes_registries(project_root):
    container = build_container(project_root)
    assert 'dls' in container.solver_registry.ids()
    assert 'lm' in container.solver_registry.ids()
    assert 'joint_trapezoidal' in container.planner_registry.ids()
    assert 'yaml' in container.importer_registry.ids()
    assert container.runtime_context['layout_mode'] == 'source'
    assert container.runtime_context['config_resolution']['active_profile'] == container.config_service.profile


def test_build_container_uses_profile_from_environment(project_root, monkeypatch):
    monkeypatch.setenv('ROBOT_SIM_PROFILE', 'ci')
    container = build_container(project_root)
    assert container.config_service.profile == 'ci'


def test_build_container_resolution_summary_no_longer_tracks_legacy_repo_override_files(project_root):
    container = build_container(project_root)
    resolution = container.runtime_context['config_resolution']
    assert 'legacy_local_override_enabled' not in resolution
    assert 'ignored_legacy_override_files' not in resolution


def test_build_container_exposes_grouped_bundles(project_root):
    container = build_container(project_root)
    assert container.registry_bundle.robot_registry is container.robot_registry
    assert container.service_bundle.config_service is container.config_service
    assert container.workflow_bundle.traj_uc is container.traj_uc


def test_build_container_exposes_workflow_facade_and_bootstrap_bundle(project_root):
    container = build_container(project_root)
    assert container.bootstrap_bundle.workflow_facade is not None
    assert container.bootstrap_bundle.workflow_facade.registries.robot_registry is container.robot_registry
    assert container.workflow_facade.workflows.import_robot_uc is container.import_robot_uc


def test_build_presentation_bootstrap_bundle_requires_bootstrap_bundle_surface(project_root):
    from types import SimpleNamespace

    from robot_sim.app.contracts import build_presentation_bootstrap_bundle

    container = build_container(project_root)
    broken = SimpleNamespace(bootstrap_bundle=container.bootstrap_bundle)
    bundle = build_presentation_bootstrap_bundle(project_root, container=broken)
    assert bundle.services.runtime_paths == container.runtime_paths
    assert bundle.services.workflow_facade.registries.robot_registry is container.robot_registry
