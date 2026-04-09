from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
from typing import Any

import yaml


@dataclass(frozen=True)
class PerfBudgetResult:
    """Result of validating a concrete measurement payload against a named budget."""

    key: str
    profile: str
    passed: bool
    violations: tuple[str, ...]


class PerfBudgetService:
    """Load and enforce repository performance budgets.

    The service keeps performance expectations in checked-in YAML instead of burying
    them inside ad hoc benchmark tests. Budget evaluation supports both legacy single
    metrics and statistical thresholds (median / p95 / max-single) so CI can enforce
    stable performance expectations without overfitting to a single noisy sample.
    """

    DEFAULT_PROFILE = 'ci'
    DEFAULT_WARMUP_RUNS = 1
    DEFAULT_MEASURED_RUNS = 5
    _RESERVED_BUDGET_KEYS = {'sampling'}

    def __init__(self, budget_path: str | Path) -> None:
        self._path = Path(budget_path)
        if not self._path.exists():
            raise FileNotFoundError(f'performance budget file not found: {self._path}')
        self._payload = yaml.safe_load(self._path.read_text(encoding='utf-8')) or {}
        self._profiles = dict(self._payload.get('profiles', {}) or {})

    @classmethod
    def from_repo_root(cls, project_root: str | Path) -> 'PerfBudgetService':
        return cls(Path(project_root) / 'configs' / 'perf_budgets.yaml')

    def budget(self, key: str, *, profile: str | None = None, environment: dict[str, str] | None = None) -> dict[str, Any]:
        active_profile = str(profile or self.DEFAULT_PROFILE)
        profile_payload = dict(self._profiles.get(active_profile, {}) or {})
        environment_overrides = tuple(profile_payload.pop('environment_overrides', ()) or ())
        budget = profile_payload.get(key)
        if budget is None:
            raise KeyError(f'performance budget not found for profile={active_profile!r}, key={key!r}')
        resolved = dict(budget)
        fingerprint = environment or self.runtime_environment()
        for override in environment_overrides:
            if not isinstance(override, dict):
                continue
            selector = dict(override.get('selector', {}) or {})
            if not self._environment_matches(selector, fingerprint):
                continue
            budget_overrides = dict(override.get('budgets', {}) or {})
            if key in budget_overrides and isinstance(budget_overrides[key], dict):
                resolved = self._deep_merge(resolved, dict(budget_overrides[key]))
        return resolved

    def sampling_plan(self, key: str, *, profile: str | None = None) -> dict[str, int]:
        """Return the configured warmup and measured sample counts for a budget.

        Args:
            key: Budget identifier.
            profile: Optional performance-profile override.

        Returns:
            dict[str, int]: Sampling plan with ``warmup_runs`` and ``measured_runs``.

        Raises:
            KeyError: If the requested budget is not defined.
            ValueError: If the sampling plan contains invalid counts.
        """
        budget = self.budget(key, profile=profile)
        sampling = dict(budget.get('sampling', {}) or {})
        warmup_runs = int(sampling.get('warmup_runs', self.DEFAULT_WARMUP_RUNS) or self.DEFAULT_WARMUP_RUNS)
        measured_runs = int(sampling.get('measured_runs', self.DEFAULT_MEASURED_RUNS) or self.DEFAULT_MEASURED_RUNS)
        if warmup_runs < 0:
            raise ValueError(f'invalid warmup run count for budget {key!r}: {warmup_runs}')
        if measured_runs <= 0:
            raise ValueError(f'invalid measured run count for budget {key!r}: {measured_runs}')
        return {'warmup_runs': warmup_runs, 'measured_runs': measured_runs}

    def evaluate_metrics(self, key: str, metrics: dict[str, Any], *, profile: str | None = None) -> PerfBudgetResult:
        budget = self.budget(key, profile=profile)
        active_profile = str(profile or self.DEFAULT_PROFILE)
        thresholds = self._normalized_thresholds(budget)
        violations: list[str] = []
        for metric_name, rule in thresholds.items():
            if metric_name not in metrics:
                violations.append(f'missing metric: {metric_name}')
                continue
            value = metrics[metric_name]
            try:
                observed = float(value)
            except (TypeError, ValueError):
                violations.append(f'non-numeric metric: {metric_name}={value!r}')
                continue
            violations.extend(self._evaluate_threshold(metric_name, observed, rule))
        return PerfBudgetResult(
            key=key,
            profile=active_profile,
            passed=not violations,
            violations=tuple(violations),
        )

    def evaluate_benchmark_report(self, report, *, key: str, profile: str | None = None) -> PerfBudgetResult:
        aggregate = dict(getattr(report, 'aggregate', {}) or {})
        metrics = {
            'p95_elapsed_ms': aggregate.get('p95_elapsed_ms', 0.0),
            'mean_final_pos_err': aggregate.get('mean_final_pos_err', 0.0),
            'success_rate_min': float(getattr(report, 'success_rate', 0.0) or 0.0),
        }
        return self.evaluate_metrics(key, metrics, profile=profile)


    @staticmethod
    def runtime_environment() -> dict[str, str]:
        """Return the runtime fingerprint used by performance-budget selection."""
        return {
            'python_major_minor': '.'.join(platform.python_version().split('.')[:2]),
            'platform_system': platform.system().lower(),
            'platform_machine': platform.machine().lower(),
        }

    @staticmethod
    def _environment_matches(selector: dict[str, str], fingerprint: dict[str, str]) -> bool:
        for key, expected in dict(selector or {}).items():
            actual = str(fingerprint.get(str(key), ''))
            expected_value = str(expected or '')
            if not expected_value:
                continue
            if actual != expected_value:
                return False
        return True

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = PerfBudgetService._deep_merge(dict(merged[key]), dict(value))
            else:
                merged[key] = value
        return merged

    @classmethod
    def _normalized_thresholds(cls, budget: dict[str, Any]) -> dict[str, dict[str, float]]:
        thresholds: dict[str, dict[str, float]] = {}
        for metric_name, rule in budget.items():
            if metric_name in cls._RESERVED_BUDGET_KEYS:
                continue
            if isinstance(rule, dict):
                tolerance = float(rule.get('tolerance', 0.0) or 0.0)
                if tolerance < 0.0:
                    raise ValueError(f'invalid tolerance for perf budget {metric_name!r}: {tolerance}')
                if 'max' in rule:
                    thresholds[metric_name] = {'kind': 'max', 'value': float(rule['max']), 'tolerance': tolerance}
                elif 'min' in rule:
                    thresholds[metric_name] = {'kind': 'min', 'value': float(rule['min']), 'tolerance': tolerance}
                else:
                    raise ValueError(f'unsupported perf budget rule for {metric_name!r}: {rule!r}')
            else:
                kind = 'min' if metric_name.endswith('_min') else 'max'
                thresholds[metric_name] = {'kind': kind, 'value': float(rule), 'tolerance': 0.0}
        return thresholds

    @staticmethod
    def _evaluate_threshold(metric_name: str, observed: float, rule: dict[str, float]) -> list[str]:
        threshold = float(rule['value'])
        tolerance = float(rule.get('tolerance', 0.0) or 0.0)
        kind = str(rule['kind'])
        if kind == 'max':
            effective_limit = threshold + tolerance
            if observed > effective_limit:
                if tolerance > 0.0:
                    return [f'{metric_name} exceeded budget: observed={observed:.4f}, limit={threshold:.4f}, tolerance={tolerance:.4f}']
                return [f'{metric_name} exceeded budget: observed={observed:.4f}, limit={threshold:.4f}']
            return []
        if kind == 'min':
            effective_minimum = threshold - tolerance
            if observed < effective_minimum:
                if tolerance > 0.0:
                    return [f'{metric_name} below budget: observed={observed:.4f}, minimum={threshold:.4f}, tolerance={tolerance:.4f}']
                return [f'{metric_name} below budget: observed={observed:.4f}, minimum={threshold:.4f}']
            return []
        raise ValueError(f'unsupported perf budget threshold kind for {metric_name!r}: {kind!r}')
