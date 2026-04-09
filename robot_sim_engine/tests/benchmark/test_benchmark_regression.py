from __future__ import annotations

from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.services.perf_budget_service import PerfBudgetService
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.solver_config import IKConfig


def test_benchmark_service_compares_against_baseline(planar_spec, project_root):
    service = BenchmarkService(RunIKUseCase(DefaultSolverRegistry()))
    baseline = {'success_rate': 0.95, 'aggregate': {'p95_elapsed_ms': 50.0}}
    report = service.run(planar_spec, IKConfig(), baseline=baseline)
    assert 'comparison' in report
    assert 'regressed' in report['comparison']

    budget_service = PerfBudgetService.from_repo_root(project_root)
    eval_result = budget_service.evaluate_metrics(
        'ik_planar_default_suite',
        {
            'p95_elapsed_ms': report['aggregate']['p95_elapsed_ms'],
            'mean_final_pos_err': report['aggregate']['mean_final_pos_err'],
            'success_rate_min': report['success_rate'],
        },
        profile='ci',
    )
    assert eval_result.passed, eval_result.violations
