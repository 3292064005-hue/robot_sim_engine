from __future__ import annotations

from robot_sim.application.importers.yaml_importer import YAMLRobotImporter


def build_plugin(*, robot_registry):
    """Return a repository-shipped importer plugin payload.

    The implementation deliberately wraps the stable YAML importer so importer plugins are
    continuously exercised without introducing an independent parsing stack.
    """
    return {
        'instance': YAMLRobotImporter(robot_registry),
        'aliases': ('research_yaml',),
        'metadata': {
            'source_format': 'yaml',
            'extensions': ('yaml', 'yml'),
            'display_name': 'Research demo YAML importer',
            'fidelity': 'native',
            'family': 'config',
            'notes': 'Repository-shipped importer plugin fixture used to exercise controlled plugin discovery.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
        },
    }
