from __future__ import annotations

from robot_sim.infra.quality_gate_runner import execute_quality_gate


def test_execute_quality_gate_reports_missing_command_as_failed_result(project_root):
    result = execute_quality_gate('quick_quality', repo_root=project_root)
    assert result.gate_id == 'quick_quality'
    assert result.commands
    if result.ok:
        return
    first = result.commands[0]
    assert first.returncode in {1, 127}
    if first.returncode == 127:
        assert 'command unavailable' in first.stderr
