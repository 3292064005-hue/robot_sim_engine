from __future__ import annotations

from pathlib import Path

from robot_sim.application.services.benchmark_execution_harness import BenchmarkExecutionHarness
from robot_sim.application.services.benchmark_matrix_service import BenchmarkMatrixService


def test_benchmark_execution_harness_deduplicates_matrix_targets(project_root: Path):
    matrix = BenchmarkMatrixService(project_root / 'configs' / 'benchmark_matrix.yaml').load()
    harness = BenchmarkExecutionHarness(python_executable='python')

    plan = harness.execution_plan(matrix)

    selectors = [item.selector for item in plan]
    assert selectors == list(dict.fromkeys(selectors))
    assert selectors == list(matrix.target_ids)
    assert all(item.kind == 'runtime_case' for item in plan)


def test_benchmark_execution_harness_executes_runtime_targets_through_shared_runner(project_root: Path):
    matrix = BenchmarkMatrixService(project_root / 'configs' / 'benchmark_matrix.yaml').load()
    executed: list[tuple[str, Path]] = []

    def runtime_runner(selector: str, repo_root: Path) -> dict[str, object]:
        executed.append((selector, repo_root))
        assert repo_root == project_root
        return {'case_id': selector, 'ok': True, 'summary': {'selector': selector}}

    harness = BenchmarkExecutionHarness(python_executable='python', runtime_case_runner=runtime_runner)
    result = harness.execute(matrix, repo_root=project_root)

    assert result.ok is True
    assert len(executed) == len(matrix.target_ids)
    assert [selector for selector, _ in executed] == list(matrix.target_ids)
    assert all(command[0] == 'runtime_case' for command in result.command_list)
    assert result.summary()['ok'] is True
