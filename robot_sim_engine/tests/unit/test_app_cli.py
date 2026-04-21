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
        self.bootstrap_bundle = type('BootstrapBundle', (), {
            'services': type('Services', (), {'config_service': self.config_service})(),
        })()


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


class _DummyHeadlessWorkflowService:
    def __init__(self, container) -> None:
        self.container = container

    def execute(self, command: str, request: dict[str, object]) -> dict[str, object]:
        if command == 'fk' and request.get('robot') == 'planar_2dof':
            return {'pose': 'ok', 'robot': request['robot']}
        raise cli.HeadlessRequestError('bad payload')


def test_cli_batch_command_prints_machine_readable_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'bootstrap', lambda startup_mode='headless': _DummyContext())
    monkeypatch.setattr(cli, 'HeadlessWorkflowService', _DummyHeadlessWorkflowService)
    assert cli.main(['batch', 'fk', '--request-json', '{"robot": "planar_2dof"}']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is True
    assert payload['command'] == 'fk'
    assert payload['result']['robot'] == 'planar_2dof'


def test_cli_batch_command_prints_machine_readable_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'bootstrap', lambda startup_mode='headless': _DummyContext())
    monkeypatch.setattr(cli, 'HeadlessWorkflowService', _DummyHeadlessWorkflowService)
    assert cli.main(['batch', 'fk', '--request-json', '{"robot": "bad"}']) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is False
    assert payload['error_type'] == 'HeadlessRequestError'




def test_cli_batch_output_write_failure_falls_back_to_stdout(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(cli, 'bootstrap', lambda startup_mode='headless': _DummyContext())
    monkeypatch.setattr(cli, 'HeadlessWorkflowService', _DummyHeadlessWorkflowService)
    output_dir = tmp_path / 'outdir'
    output_dir.mkdir()
    assert cli.main(['batch', 'fk', '--request-json', '{"robot": "planar_2dof"}', '--output', str(output_dir)]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is False
    assert payload['error_type'] == 'HeadlessExecutionError'
    assert 'failed to write output payload' in payload['message']
def test_cli_batch_request_parse_failure_does_not_bootstrap(monkeypatch, capsys) -> None:
    calls = []
    def _boom(startup_mode='headless'):
        calls.append(startup_mode)
        raise AssertionError('bootstrap should not be called for malformed request payloads')
    monkeypatch.setattr(cli, 'bootstrap', _boom)
    assert cli.main(['batch', 'fk', '--request-json', '{bad json}']) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is False
    assert payload['error_type'] == 'HeadlessRequestError'
    assert calls == []
