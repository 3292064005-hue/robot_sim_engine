from __future__ import annotations

from robot_sim.application.services.perf_budget_service import PerfBudgetService


def test_perf_budget_service_loads_repository_budgets(project_root):
    service = PerfBudgetService.from_repo_root(project_root)
    budget = service.budget('ik_planar_smoke', profile='ci')
    assert float((budget['median_elapsed_ms'].get('max') if isinstance(budget['median_elapsed_ms'], dict) else budget['median_elapsed_ms'])) > 0.0
    assert budget['sampling']['measured_runs'] > 0


def test_perf_budget_service_exposes_sampling_plan(project_root):
    service = PerfBudgetService.from_repo_root(project_root)
    sampling = service.sampling_plan('ik_planar_smoke', profile='ci')
    assert sampling['warmup_runs'] >= 0
    assert sampling['measured_runs'] > 0


def test_perf_budget_service_flags_budget_violations(project_root):
    service = PerfBudgetService.from_repo_root(project_root)
    result = service.evaluate_metrics(
        'ik_planar_smoke',
        {
            'median_elapsed_ms': 999.0,
            'p95_elapsed_ms': 999.0,
            'max_single_elapsed_ms': 999.0,
        },
        profile='ci',
    )
    assert result.passed is False
    assert result.violations


def test_perf_budget_service_supports_minimum_thresholds(project_root):
    service = PerfBudgetService.from_repo_root(project_root)
    result = service.evaluate_metrics('ik_planar_default_suite', {'p95_elapsed_ms': 1.0, 'mean_final_pos_err': 0.0, 'success_rate_min': 0.10}, profile='ci')
    assert result.passed is False
    assert any('success_rate_min below budget' in item for item in result.violations)


def test_perf_budget_service_supports_rule_tolerances(tmp_path):
    budget_path = tmp_path / 'perf_budgets.yaml'
    budget_path.write_text(
        """profiles:
  ci:
    tol_budget:
      latency_ms:
        max: 10.0
        tolerance: 0.5
""",
        encoding='utf-8',
    )
    service = PerfBudgetService(budget_path)
    assert service.evaluate_metrics('tol_budget', {'latency_ms': 10.4}, profile='ci').passed is True
    assert service.evaluate_metrics('tol_budget', {'latency_ms': 10.6}, profile='ci').passed is False
