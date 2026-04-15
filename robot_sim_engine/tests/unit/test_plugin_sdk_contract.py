from __future__ import annotations

import tomllib
from pathlib import Path

from robot_sim.plugin_sdk import plugin_payload


class _Plugin:
    pass


def test_plugin_payload_normalizes_metadata_and_aliases() -> None:
    payload = plugin_payload(_Plugin(), aliases=['alpha', 'beta'], metadata={'display_name': 'Example'})
    assert payload['aliases'] == ('alpha', 'beta')
    assert payload['metadata']['display_name'] == 'Example'
    assert payload['instance'].__class__.__name__ == '_Plugin'


def test_pyproject_keeps_research_demo_plugins_out_of_repository_entry_points(project_root: Path) -> None:
    data = tomllib.loads((project_root / 'pyproject.toml').read_text(encoding='utf-8'))
    assert data['project']['scripts']['robot-sim'] == 'robot_sim.app.cli:main'
    assert 'entry-points' not in data['project'] or 'robot_sim.plugins' not in data['project'].get('entry-points', {})
    assert 'research' in data['project']['optional-dependencies']
