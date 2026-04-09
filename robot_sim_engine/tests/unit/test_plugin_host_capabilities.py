from __future__ import annotations

from pathlib import Path

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy


def test_plugin_loader_gates_required_host_capabilities(tmp_path: Path) -> None:
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: gated_solver\n'
        '    kind: solver\n'
        '    factory: robot_sim.plugins.research_demo_solver:build_plugin\n'
        '    source: shipped_plugin\n'
        '    enabled_profiles: [research]\n'
        '    required_host_capabilities: [profile:research, experimental_modules]\n',
        encoding='utf-8',
    )
    blocked = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', experimental_modules_enabled=False))
    audit = blocked.audit('solver')
    assert audit[0]['reason'] == 'required_host_capability_missing'
    allowed = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', experimental_modules_enabled=True))
    assert allowed.audit('solver')[0]['enabled'] is True
