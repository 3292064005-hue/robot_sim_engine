from __future__ import annotations

from robot_sim.domain.quality_gate_catalog import QualityGateDefinition
from robot_sim.infra import quality_gate_runner


def test_execute_quality_gate_reports_missing_command_as_failed_result(monkeypatch, project_root):
    monkeypatch.setattr(
        quality_gate_runner,
        'quality_gate_definition',
        lambda gate_id: QualityGateDefinition(
            gate_id='missing_tool_gate',
            description='synthetic missing-tool gate for unit coverage',
            commands=(( '__definitely_missing_robot_sim_tool__', '--version'),),
        ),
    )

    result = quality_gate_runner.execute_quality_gate('missing_tool_gate', repo_root=project_root)
    assert result.gate_id == 'missing_tool_gate'
    assert result.commands
    assert result.ok is False
    first = result.commands[0]
    assert first.returncode == 127
    assert 'command unavailable' in first.stderr
    assert result.failure_kind == 'tooling_missing'
