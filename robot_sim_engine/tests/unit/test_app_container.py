from __future__ import annotations

from robot_sim.app.container import build_container


def test_build_container_exposes_registries(project_root):
    container = build_container(project_root)
    assert 'dls' in container.solver_registry.ids()
    assert 'lm' in container.solver_registry.ids()
    assert 'joint_trapezoidal' in container.planner_registry.ids()
    assert 'yaml' in container.importer_registry.ids()
<<<<<<< HEAD
    assert container.runtime_context['layout_mode'] == 'source'
    assert container.runtime_context['config_resolution']['active_profile'] == container.config_service.profile
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


def test_build_container_uses_profile_from_environment(project_root, monkeypatch):
    monkeypatch.setenv('ROBOT_SIM_PROFILE', 'ci')
    container = build_container(project_root)
    assert container.config_service.profile == 'ci'
<<<<<<< HEAD


def test_build_container_disables_legacy_repo_override_files(project_root):
    container = build_container(project_root)
    resolution = container.runtime_context['config_resolution']
    assert resolution['legacy_local_override_enabled'] is False
    assert resolution['ignored_legacy_override_files']['app'] is True
    assert resolution['ignored_legacy_override_files']['solver'] is True
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
