from __future__ import annotations

import sys

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy


def test_public_solver_plugin_example_stays_loader_compatible(project_root, monkeypatch):
    examples_root = project_root / 'examples'
    manifest = project_root / 'configs' / 'plugins_example_solver.yaml'
    manifest.write_text(
        """plugins:
  - id: example_solver
    kind: solver
    factory: plugins.minimal_solver_plugin:build_plugin
    enabled_profiles: [research]
""",
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(examples_root))
    sys.path.insert(0, str(examples_root))
    try:
        loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True))
        registrations = loader.registrations('solver', display_name='SDK Example Solver')
        assert len(registrations) == 1
        assert registrations[0].metadata['display_name'] == 'SDK Example Solver'
        assert registrations[0].aliases == ('example_solver_alias',)
    finally:
        while str(examples_root) in sys.path:
            sys.path.remove(str(examples_root))
        manifest.unlink(missing_ok=True)


def test_public_importer_plugin_example_stays_loader_compatible(project_root, monkeypatch):
    examples_root = project_root / 'examples'
    manifest = project_root / 'configs' / 'plugins_example_importer.yaml'
    manifest.write_text(
        """plugins:
  - id: example_importer
    kind: importer
    factory: plugins.minimal_importer_plugin:build_plugin
    enabled_profiles: [research]
""",
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(examples_root))
    sys.path.insert(0, str(examples_root))
    try:
        loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True))
        registrations = loader.registrations('importer')
        assert len(registrations) == 1
        assert registrations[0].metadata['display_name'] == 'Example YAML importer'
        assert registrations[0].aliases == ('example_importer_alias',)
    finally:
        while str(examples_root) in sys.path:
            sys.path.remove(str(examples_root))
        manifest.unlink(missing_ok=True)
