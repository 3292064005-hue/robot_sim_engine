from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import sys

from robot_sim.application.services.benchmark_matrix_service import BenchmarkExecutionTarget, BenchmarkMatrix, BenchmarkMatrixPair
from robot_sim.infra.benchmark_runtime_cases import run_benchmark_runtime_case


@dataclass(frozen=True)
class BenchmarkHarnessTargetPlan:
    """Stable summary of one executable benchmark target selected from the matrix."""

    pair_id: str
    kind: str
    selector: str
    execution_environment: str
    metadata: dict[str, object] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        return {
            'pair_id': self.pair_id,
            'kind': self.kind,
            'selector': self.selector,
            'execution_environment': self.execution_environment,
            'metadata': dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class BenchmarkHarnessExecutionResult:
    """Structured execution result for a single harness target."""

    pair_id: str
    kind: str
    selector: str
    command: tuple[str, ...]
    ok: bool
    returncode: int
    execution_environment: str
    details: dict[str, object] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        return {
            'pair_id': self.pair_id,
            'kind': self.kind,
            'selector': self.selector,
            'command': list(self.command),
            'ok': bool(self.ok),
            'returncode': int(self.returncode),
            'execution_environment': self.execution_environment,
            'details': dict(self.details or {}),
        }


@dataclass(frozen=True)
class BenchmarkHarnessRun:
    """Aggregated benchmark execution-harness run result."""

    matrix_id: str
    targets: tuple[BenchmarkHarnessExecutionResult, ...]

    @property
    def ok(self) -> bool:
        return all(target.ok for target in self.targets)

    @property
    def command_list(self) -> list[list[str]]:
        return [list(target.command) for target in self.targets]

    def summary(self) -> dict[str, object]:
        return {
            'matrix_id': self.matrix_id,
            'ok': bool(self.ok),
            'targets': [target.summary() for target in self.targets],
            'command_list': self.command_list,
        }


class BenchmarkExecutionHarness:
    """Execute benchmark-matrix targets through a stable harness contract.

    The matrix remains the declarative source of truth for importer/scene/solver/capture
    coverage. Unlike the legacy pytest-selector harness, runtime cases execute the shipped
    application services directly so coverage is expressed as importer/scene/planner/capture
    runtime flows instead of only as test-node indirection.
    """

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        runtime_case_runner: Callable[[str, Path], dict[str, object]] | None = None,
    ) -> None:
        self._python_executable = str(python_executable or sys.executable)
        self._runtime_case_runner = runtime_case_runner or self._default_runtime_case_runner

    def execution_plan(self, matrix: BenchmarkMatrix) -> tuple[BenchmarkHarnessTargetPlan, ...]:
        """Return the deduplicated target plan implied by the benchmark matrix."""
        plans: list[BenchmarkHarnessTargetPlan] = []
        seen: set[tuple[str, str]] = set()
        for pair in matrix.required_pairs:
            for target in pair.execution_targets:
                key = (target.kind, target.selector)
                if key in seen:
                    continue
                seen.add(key)
                plans.append(self._plan_from_pair(pair, target))
        return tuple(plans)

    def execute(self, matrix: BenchmarkMatrix, *, repo_root: str | Path) -> BenchmarkHarnessRun:
        """Execute the benchmark matrix through the shared harness."""
        root = Path(repo_root)
        results: list[BenchmarkHarnessExecutionResult] = []
        for plan in self.execution_plan(matrix):
            result = self._execute_plan(plan, repo_root=root)
            results.append(result)
        return BenchmarkHarnessRun(matrix_id=matrix.matrix_id, targets=tuple(results))

    def _execute_plan(self, plan: BenchmarkHarnessTargetPlan, *, repo_root: Path) -> BenchmarkHarnessExecutionResult:
        command = self._build_command(plan)
        details = dict(self._runtime_case_runner(plan.selector, repo_root))
        ok = bool(details.get('ok', True))
        return BenchmarkHarnessExecutionResult(
            pair_id=plan.pair_id,
            kind=plan.kind,
            selector=plan.selector,
            command=tuple(command),
            ok=ok,
            returncode=0 if ok else 1,
            execution_environment=plan.execution_environment,
            details=details,
        )

    def _plan_from_pair(self, pair: BenchmarkMatrixPair, target: BenchmarkExecutionTarget) -> BenchmarkHarnessTargetPlan:
        return BenchmarkHarnessTargetPlan(
            pair_id=pair.pair_id,
            kind=str(target.kind),
            selector=str(target.selector),
            execution_environment=str(target.execution_environment),
            metadata=dict(target.metadata or {}),
        )

    def _build_command(self, plan: BenchmarkHarnessTargetPlan) -> tuple[str, ...]:
        if plan.kind != 'runtime_case':
            raise ValueError(f'unsupported benchmark harness target kind: {plan.kind!r}')
        return ('runtime_case', plan.selector)

    @staticmethod
    def _default_runtime_case_runner(selector: str, repo_root: Path) -> dict[str, object]:
        result = run_benchmark_runtime_case(selector, repo_root=repo_root)
        return {
            'case_id': result.case_id,
            'ok': bool(result.ok),
            'summary': dict(result.summary or {}),
        }
