from __future__ import annotations

from pathlib import Path

import pytest

from robot_sim.application.services.perf_budget_service import PerfBudgetService



def test_perf_budget_service_requires_existing_budget_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PerfBudgetService(tmp_path / 'missing-perf-budgets.yaml')



def test_perf_budget_service_rejects_invalid_sampling_counts(tmp_path: Path) -> None:
    budget_path = tmp_path / 'perf_budgets.yaml'
    budget_path.write_text(
        'profiles:\n'
        '  ci:\n'
        '    bad_budget:\n'
        '      sampling:\n'
        '        warmup_runs: -1\n'
        '        measured_runs: 0\n'
        '      median_elapsed_ms: 10.0\n',
        encoding='utf-8',
    )
    service = PerfBudgetService(budget_path)

    with pytest.raises(ValueError, match='invalid warmup run count'):
        service.sampling_plan('bad_budget', profile='ci')



def test_perf_budget_service_reports_missing_and_non_numeric_metrics(project_root: Path) -> None:
    service = PerfBudgetService.from_repo_root(project_root)
    result = service.evaluate_metrics(
        'ik_planar_smoke',
        {
            'median_elapsed_ms': 'not-a-number',
        },
        profile='ci',
    )

    assert result.passed is False
    assert 'non-numeric metric: median_elapsed_ms=\'not-a-number\'' in result.violations
    assert 'missing metric: p95_elapsed_ms' in result.violations
    assert 'missing metric: max_single_elapsed_ms' in result.violations


def test_perf_budget_service_rejects_negative_tolerance(tmp_path: Path) -> None:
    budget_path = tmp_path / 'perf_budgets.yaml'
    budget_path.write_text(
        """profiles:
  ci:
    tol_budget:
      latency_ms:
        max: 10.0
        tolerance: -0.1
""",
        encoding='utf-8',
    )
    service = PerfBudgetService(budget_path)

    with pytest.raises(ValueError, match='invalid tolerance'):
        service.evaluate_metrics('tol_budget', {'latency_ms': 1.0}, profile='ci')
