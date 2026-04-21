from __future__ import annotations

from robot_sim.application.importers.yaml_importer import YAMLRobotImporter
from robot_sim.plugin_sdk import plugin_payload


def build_plugin(*, robot_registry):
    """Return a repository-shipped importer plugin payload.

    The implementation deliberately wraps the stable YAML importer so importer plugins are
    continuously exercised without introducing an independent parsing stack.
    """
    return plugin_payload(
        YAMLRobotImporter(robot_registry),        metadata={
            'source_format': 'yaml',
            'extensions': ('yaml', 'yml'),
            'display_name': 'Research YAML importer',
            'fidelity': 'native',
            'family': 'config',
            'notes': 'Repository-shipped importer plugin used by the research runtime surface.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
        },
    )
