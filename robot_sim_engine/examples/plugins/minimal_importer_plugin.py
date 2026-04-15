from __future__ import annotations

from pathlib import Path

from robot_sim.plugin_sdk import plugin_payload


class MinimalExampleImporter:
    """Tiny importer plugin used as a public SDK reference."""

    importer_id = 'example_yaml'

    def capabilities(self) -> dict[str, object]:
        return {
            'source_format': 'yaml',
            'fidelity': 'native',
            'family': 'structured_loader',
        }

    def load(self, source, **kwargs):
        return {
            'source': str(Path(source)),
            'kwargs': dict(kwargs),
        }


def build_plugin():
    """Return a manifest-compatible importer plugin payload for ``PluginLoader`` examples."""
    return plugin_payload(
        MinimalExampleImporter(),
        aliases=('example_importer_alias',),
        metadata={
            'family': 'structured_loader',
            'display_name': 'Example YAML importer',
            'source': 'sdk_example',
            'accepts_suffixes': ('.yaml', '.yml'),
            'sample_path_hint': str(Path('examples') / 'plugins' / 'robot.yaml'),
        },
    )
