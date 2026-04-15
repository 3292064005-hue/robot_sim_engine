from __future__ import annotations

from robot_sim.application.importers.yaml_importer import YAMLRobotImporter
from robot_sim.plugin_sdk import plugin_payload


def build_plugin(*, robot_registry):
    """Return the repository-shipped stable importer plugin payload."""
    return plugin_payload(
        YAMLRobotImporter(robot_registry),
        aliases=('stable_yaml',),
        metadata={
            'source_format': 'yaml',
            'extensions': ('yaml', 'yml'),
            'display_name': 'Stable shipped YAML importer',
            'fidelity': 'native',
            'family': 'config',
            'notes': 'Repository-shipped stable importer plugin fixture used to exercise mainline plugin loading.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
        },
    )
