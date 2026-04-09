from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from robot_sim.app.compatibility_matrix import COMPATIBILITY_MATRIX


@dataclass(frozen=True)
class CompatibilityScenarioBudget:
    scenario: str
    allowed_counts: dict[str, int]


@dataclass(frozen=True)
class CompatibilityBudgetReport:
    scenario: str
    observed_counts: dict[str, int]
    allowed_counts: dict[str, int]
    violations: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.violations


def default_allowed_counts() -> dict[str, int]:
    return {entry.surface: 0 for entry in COMPATIBILITY_MATRIX}


def load_compatibility_budgets(path: str | Path) -> dict[str, CompatibilityScenarioBudget]:
    """Load compatibility-usage budgets keyed by scenario name.

    Args:
        path: YAML file containing ``scenarios`` with per-surface maximum counts.

    Returns:
        dict[str, CompatibilityScenarioBudget]: Normalized scenario budgets.

    Raises:
        ValueError: If the file shape is invalid or references unknown surfaces.
    """
    payload = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    if not isinstance(payload, dict):
        raise ValueError('compatibility budget file must be a mapping')
    raw_scenarios = payload.get('scenarios', {})
    if not isinstance(raw_scenarios, dict):
        raise ValueError('compatibility budget scenarios must be a mapping')
    known_surfaces = {entry.surface for entry in COMPATIBILITY_MATRIX}
    budgets: dict[str, CompatibilityScenarioBudget] = {}
    for scenario, raw_budget in raw_scenarios.items():
        if raw_budget is None:
            raw_budget = {}
        if not isinstance(raw_budget, dict):
            raise ValueError(f'compatibility budget for {scenario!r} must be a mapping')
        allowed = default_allowed_counts()
        for surface, value in raw_budget.items():
            if surface not in known_surfaces:
                raise ValueError(f'unknown compatibility surface in budget: {surface}')
            allowed[surface] = int(value)
        budgets[str(scenario)] = CompatibilityScenarioBudget(scenario=str(scenario), allowed_counts=allowed)
    return budgets


def evaluate_compatibility_budget(
    *,
    scenario: str,
    observed_counts: Mapping[str, int],
    budget: CompatibilityScenarioBudget,
) -> CompatibilityBudgetReport:
    """Compare observed runtime compatibility usage with a scenario budget."""
    allowed = dict(budget.allowed_counts)
    observed = {surface: int(observed_counts.get(surface, 0)) for surface in allowed}
    violations = []
    for surface, allowed_count in allowed.items():
        count = int(observed.get(surface, 0))
        if count > int(allowed_count):
            violations.append(
                f'compatibility budget exceeded for {scenario}: {surface!r} observed={count} allowed={allowed_count}'
            )
    return CompatibilityBudgetReport(
        scenario=str(scenario),
        observed_counts=observed,
        allowed_counts=allowed,
        violations=tuple(violations),
    )
