from __future__ import annotations

from robot_sim.application.importers.yaml_importer import YAMLRobotImporter
from robot_sim.plugin_sdk import plugin_payload


def build_plugin(*, robot_registry):
    """Return the repository-shipped production importer plugin payload."""
    return plugin_payload(
        YAMLRobotImporter(robot_registry),        metadata={
            'source_format': 'yaml',
            'extensions': ('yaml', 'yml'),
            'display_name': 'Shipped YAML importer',
            'fidelity': 'native',
            'family': 'config',
            'notes': 'Repository-shipped production importer plugin used by the default runtime surface.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
            'canonical_target': 'yaml',
        },
    )
