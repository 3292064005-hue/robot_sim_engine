from __future__ import annotations

import json

from robot_sim.app import cli


class _DummyConfigService:
    def describe_effective_snapshot(self) -> dict[str, object]:
        return {'profile': 'default', 'app': {'window': {'title': 'Robot Sim Engine'}}, 'solver': {}}


class _DummyContainer:
    def __init__(self) -> None:
        self.startup_summary = {'runtime': {'layout_mode': 'source'}}
        self.config_service = _DummyConfigService()


class _DummyContext:
    def __init__(self) -> None:
        self.container = _DummyContainer()


def test_cli_runtime_summary_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'bootstrap', lambda startup_mode='headless': _DummyContext())
    assert cli.main(['runtime-summary']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['runtime']['layout_mode'] == 'source'


def test_cli_config_snapshot_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'bootstrap', lambda startup_mode='headless': _DummyContext())
    assert cli.main(['config-snapshot']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['profile'] == 'default'
    assert payload['app']['window']['title'] == 'Robot Sim Engine'



def test_cli_config_snapshot_creates_parent_directories(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, 'bootstrap', lambda startup_mode='headless': _DummyContext())
    output_path = tmp_path / 'nested' / 'config' / 'snapshot.json'
    assert cli.main(['config-snapshot', '--output', str(output_path)]) == 0
    payload = json.loads(output_path.read_text(encoding='utf-8'))
    assert payload['profile'] == 'default'
