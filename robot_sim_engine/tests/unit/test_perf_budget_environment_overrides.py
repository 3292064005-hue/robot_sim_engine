from __future__ import annotations

from robot_sim.application.services.perf_budget_service import PerfBudgetService


def test_perf_budget_service_applies_environment_overrides(project_root) -> None:
    service = PerfBudgetService.from_repo_root(project_root)
    base_budget = service.budget('ik_planar_smoke', profile='ci', environment={'platform_system': 'linux', 'python_major_minor': '3.10', 'platform_machine': 'x86_64'})
    override_budget = service.budget('ik_planar_smoke', profile='ci', environment={'platform_system': 'linux', 'python_major_minor': '3.13', 'platform_machine': 'x86_64'})
    assert float(base_budget['median_elapsed_ms']['max']) == 60.0
    assert float(override_budget['median_elapsed_ms']['max']) == 125.0
