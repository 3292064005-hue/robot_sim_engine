from __future__ import annotations

import sys
from pathlib import Path

import pytest

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.domain.enums import ModuleStatus


def _write_plugin_module(tmp_path: Path) -> None:
    plugin_module = tmp_path / 'demo_plugin.py'
    plugin_module.write_text(
        'class DemoSolver:\n'
        '    pass\n\n'
        'def build_plugin():\n'
        '    return {"instance": DemoSolver(), "metadata": {"family": "iterative"}}\n',
        encoding='utf-8',
    )


def test_plugin_loader_gates_status_by_runtime_policy(tmp_path: Path, monkeypatch):
    _write_plugin_module(tmp_path)
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: beta_solver\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    source: shipped_plugin\n'
        '    status: beta\n',
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.path.insert(0, str(tmp_path))
    try:
        default_loader = PluginLoader(
            manifest,
            policy=RuntimeFeaturePolicy(active_profile='default', plugin_discovery_enabled=False, plugin_status_allowlist=('stable', 'deprecated')),
        )
        assert default_loader.registrations('solver') == ()
        audit = default_loader.audit('solver')
        assert len(audit) == 1
        assert audit[0]['enabled'] is False
        assert audit[0]['reason'] == 'status_disabled'

        dev_loader = PluginLoader(
            manifest,
            policy=RuntimeFeaturePolicy(active_profile='dev', plugin_discovery_enabled=False, plugin_status_allowlist=('stable', 'beta', 'deprecated')),
        )
        registrations = dev_loader.registrations('solver')
        assert len(registrations) == 1
        assert registrations[0].metadata['status'] == 'beta'
        assert dev_loader.audit('solver')[0]['reason'] == 'enabled'
    finally:
        while str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


def test_plugin_loader_rejects_unknown_manifest_status(tmp_path: Path):
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: bad_solver\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    status: preview\n',
        encoding='utf-8',
    )
    loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True, plugin_status_allowlist=('stable', 'beta', 'experimental', 'internal', 'deprecated')))
    with pytest.raises(ValueError, match='unsupported plugin status'):
        loader.manifests('solver')


def test_capability_service_projects_plugin_statuses_into_module_status():
    solver_registry = SolverRegistry()
    solver_registry.register('stable_solver', object(), metadata={'status': 'stable'})
    solver_registry.register('beta_solver', object(), metadata={'status': 'beta'})
    solver_registry.register('experimental_solver', object(), metadata={'status': 'experimental'})

    planner_registry = PlannerRegistry()
    importer_registry = ImporterRegistry()
    importer_registry.register('yaml_like', object(), metadata={'status': 'deprecated', 'fidelity': 'native'})

    matrix = CapabilityService().build_matrix(
        solver_registry=solver_registry,
        planner_registry=planner_registry,
        importer_registry=importer_registry,
    )
    statuses = {descriptor.key: descriptor.status for descriptor in matrix.solvers}
    assert statuses['stable_solver'] is ModuleStatus.STABLE
    assert statuses['beta_solver'] is ModuleStatus.BETA
    assert statuses['experimental_solver'] is ModuleStatus.EXPERIMENTAL
    importer_statuses = {descriptor.key: descriptor.status for descriptor in matrix.importers}
    assert importer_statuses['yaml_like'] is ModuleStatus.DEPRECATED




def test_plugin_loader_gates_min_host_version(tmp_path: Path, monkeypatch):
    _write_plugin_module(tmp_path)
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: future_solver\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    source: shipped_plugin\n'
        '    min_host_version: 9.9.0\n',
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.path.insert(0, str(tmp_path))
    try:
        loader = PluginLoader(
            manifest,
            policy=RuntimeFeaturePolicy(active_profile='default', plugin_discovery_enabled=False, plugin_status_allowlist=('stable', 'deprecated')),
            host_version='0.7.0',
        )
        assert loader.registrations('solver') == ()
        audit = loader.audit('solver')
        assert audit[0]['enabled'] is False
        assert audit[0]['reason'] == 'host_version_too_old'
        assert audit[0]['host_version'] == '0.7.0'
    finally:
        while str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


def test_plugin_loader_rejects_invalid_min_host_version(tmp_path: Path):
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: bad_solver\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    min_host_version: dev-preview\n',
        encoding='utf-8',
    )
    loader = PluginLoader(
        manifest,
        policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True, plugin_status_allowlist=('stable', 'beta', 'experimental', 'internal', 'deprecated')),
    )
    with pytest.raises(ValueError, match='invalid plugin min_host_version'):
        loader.manifests('solver')


def test_plugin_loader_rejects_unknown_sdk_contract_version(tmp_path: Path):
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: bad_solver\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    sdk_contract_version: v2\n',
        encoding='utf-8',
    )
    loader = PluginLoader(
        manifest,
        policy=RuntimeFeaturePolicy(
            active_profile='research',
            plugin_discovery_enabled=True,
            plugin_status_allowlist=('stable', 'beta', 'experimental', 'internal', 'deprecated'),
        ),
    )
    with pytest.raises(ValueError, match='unsupported plugin sdk_contract_version'):
        loader.manifests('solver')
