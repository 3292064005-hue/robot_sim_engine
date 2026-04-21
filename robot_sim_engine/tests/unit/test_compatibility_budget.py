from __future__ import annotations

from robot_sim.infra.compatibility_budget import evaluate_compatibility_budget, load_compatibility_budgets


def test_load_compatibility_budget_defaults_to_empty_surface_set(project_root):
    budgets = load_compatibility_budgets(project_root / 'configs' / 'compatibility_budget.yaml')
    report = evaluate_compatibility_budget(
        scenario='clean_bootstrap',
        observed_counts={},
        budget=budgets['clean_bootstrap'],
    )
    assert report.ok is True
    assert report.allowed_counts == {}


def test_compatibility_budget_ignores_observed_counts_when_no_retained_surfaces_exist(project_root):
    budgets = load_compatibility_budgets(project_root / 'configs' / 'compatibility_budget.yaml')
    report = evaluate_compatibility_budget(
        scenario='clean_headless_mainline',
        observed_counts={'retired_surface_probe': 1},
        budget=budgets['clean_headless_mainline'],
    )
    assert report.ok is True
    assert report.observed_counts == {}
