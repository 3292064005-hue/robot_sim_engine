from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from robot_sim.domain.benchmark_target_contracts import benchmark_target_contract
from robot_sim.infra.quality_gate_catalog import ensure_quality_gates_registered


@dataclass(frozen=True)
class BenchmarkExecutionTarget:
    kind: str
    selector: str
    execution_environment: str = 'headless'

    def summary(self) -> dict[str, str]:
        return {'kind': str(self.kind), 'selector': str(self.selector), 'execution_environment': str(self.execution_environment)}


@dataclass(frozen=True)
class BenchmarkMatrixPair:
    runtime_surface: str
    importer_variant: str
    scene_variant: str
    solver_suite: str
    capture_mode: str
    execution_targets: tuple[BenchmarkExecutionTarget, ...]

    @property
    def execution_environment(self) -> str:
        environments = {target.execution_environment for target in self.execution_targets}
        return next(iter(environments)) if len(environments) == 1 else 'mixed'

    @property
    def pair_id(self) -> str:
        return '|'.join((self.runtime_surface, self.importer_variant, self.scene_variant, self.solver_suite, self.capture_mode))

    def summary(self) -> dict[str, object]:
        return {
            'runtime_surface': self.runtime_surface,
            'importer_variant': self.importer_variant,
            'scene_variant': self.scene_variant,
            'solver_suite': self.solver_suite,
            'capture_mode': self.capture_mode,
            'execution_targets': [target.summary() for target in self.execution_targets],
            'execution_environment': self.execution_environment,
        }


@dataclass(frozen=True)
class BenchmarkMatrix:
    matrix_id: str
    runtime_surfaces: tuple[str, ...]
    importer_variants: tuple[str, ...]
    scene_variants: tuple[str, ...]
    solver_suites: tuple[str, ...]
    capture_modes: tuple[str, ...]
    required_quality_gates: tuple[str, ...]
    required_pairs: tuple[BenchmarkMatrixPair, ...]

    @property
    def pytest_targets(self) -> tuple[str, ...]:
        selectors: list[str] = []
        for pair in self.required_pairs:
            for target in pair.execution_targets:
                if target.kind == 'pytest' and target.selector not in selectors:
                    selectors.append(target.selector)
        return tuple(selectors)

    def summary(self) -> dict[str, object]:
        return {
            'matrix_id': self.matrix_id,
            'runtime_surfaces': list(self.runtime_surfaces),
            'importer_variants': list(self.importer_variants),
            'scene_variants': list(self.scene_variants),
            'solver_suites': list(self.solver_suites),
            'capture_modes': list(self.capture_modes),
            'required_quality_gates': list(self.required_quality_gates),
            'required_pairs': [pair.summary() for pair in self.required_pairs],
        }


class BenchmarkMatrixService:
    """Load and validate the benchmark verification matrix used by docs and CI gates."""

    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path)

    def load(self) -> BenchmarkMatrix:
        payload = yaml.safe_load(self._config_path.read_text(encoding='utf-8')) or {}
        if not isinstance(payload, Mapping):
            raise ValueError(f'benchmark matrix must be a mapping: {self._config_path}')
        root = payload.get('benchmark_matrix')
        if not isinstance(root, Mapping):
            raise ValueError(f'benchmark_matrix root missing or invalid: {self._config_path}')
        runtime_surfaces = self._normalize_string_sequence(root.get('runtime_surfaces'), field_name='runtime_surfaces')
        importer_variants = self._normalize_string_sequence(root.get('importer_variants'), field_name='importer_variants')
        scene_variants = self._normalize_string_sequence(root.get('scene_variants'), field_name='scene_variants')
        solver_suites = self._normalize_string_sequence(root.get('solver_suites'), field_name='solver_suites')
        capture_modes = self._normalize_string_sequence(root.get('capture_modes'), field_name='capture_modes')
        required_quality_gates = self._normalize_string_sequence(root.get('required_quality_gates'), field_name='required_quality_gates')
        repo_root = self._config_path.parent.parent
        gate_repo_root = repo_root if (repo_root / 'pyproject.toml').exists() else None
        gate_errors = ensure_quality_gates_registered(required_quality_gates, repo_root=gate_repo_root)
        if gate_errors:
            raise ValueError('; '.join(gate_errors))
        raw_pairs = root.get('required_pairs') or ()
        if not isinstance(raw_pairs, (list, tuple)) or not raw_pairs:
            raise ValueError(f'benchmark_matrix.required_pairs must be a non-empty list: {self._config_path}')
        seen_keys: set[tuple[str, str, str, str, str]] = set()
        pairs: list[BenchmarkMatrixPair] = []
        for item in raw_pairs:
            if not isinstance(item, Mapping):
                raise ValueError(f'benchmark matrix pair must be a mapping: {self._config_path}')
            execution_targets = self._parse_execution_targets(item.get('execution_targets'))
            pair = BenchmarkMatrixPair(
                runtime_surface=str(item.get('runtime_surface', '')).strip(),
                importer_variant=str(item.get('importer_variant', '')).strip(),
                scene_variant=str(item.get('scene_variant', '')).strip(),
                solver_suite=str(item.get('solver_suite', '')).strip(),
                capture_mode=str(item.get('capture_mode', '')).strip(),
                execution_targets=execution_targets,
            )
            key = (pair.runtime_surface, pair.importer_variant, pair.scene_variant, pair.solver_suite, pair.capture_mode)
            if not all(key):
                raise ValueError(f'benchmark matrix pair contains an empty field: {self._config_path}')
            if pair.runtime_surface not in runtime_surfaces:
                raise ValueError(f'benchmark matrix pair references unknown runtime_surface: {pair.runtime_surface!r}')
            if pair.importer_variant not in importer_variants:
                raise ValueError(f'benchmark matrix pair references unknown importer_variant: {pair.importer_variant!r}')
            if pair.scene_variant not in scene_variants:
                raise ValueError(f'benchmark matrix pair references unknown scene_variant: {pair.scene_variant!r}')
            if pair.solver_suite not in solver_suites:
                raise ValueError(f'benchmark matrix pair references unknown solver_suite: {pair.solver_suite!r}')
            if pair.capture_mode not in capture_modes:
                raise ValueError(f'benchmark matrix pair references unknown capture_mode: {pair.capture_mode!r}')
            if key in seen_keys:
                raise ValueError(f'duplicate benchmark matrix pair: {key!r}')
            self._validate_target_contracts(pair)
            seen_keys.add(key)
            pairs.append(pair)
        return BenchmarkMatrix(
            matrix_id=str(root.get('matrix_id', 'v1') or 'v1'),
            runtime_surfaces=runtime_surfaces,
            importer_variants=importer_variants,
            scene_variants=scene_variants,
            solver_suites=solver_suites,
            capture_modes=capture_modes,
            required_quality_gates=required_quality_gates,
            required_pairs=tuple(pairs),
        )


    @staticmethod
    def _validate_target_contracts(pair: BenchmarkMatrixPair) -> None:
        expected_environment = 'gui' if pair.runtime_surface == 'gui_offscreen' else 'headless'
        observed_environments = {target.execution_environment for target in pair.execution_targets}
        if observed_environments != {expected_environment}:
            raise ValueError(
                f'benchmark matrix pair environment mismatch for {pair.pair_id!r}: '
                f'expected {expected_environment!r}, got {sorted(observed_environments)!r}'
            )
        for target in pair.execution_targets:
            contract = benchmark_target_contract(target.selector)
            if contract is None:
                raise ValueError(f'benchmark execution target selector missing semantic contract: {target.selector!r}')
            expected = (
                pair.runtime_surface,
                pair.importer_variant,
                pair.scene_variant,
                pair.solver_suite,
                pair.capture_mode,
            )
            observed = (
                contract.runtime_surface,
                contract.importer_variant,
                contract.scene_variant,
                contract.solver_suite,
                contract.capture_mode,
            )
            if observed != expected:
                raise ValueError(
                    f'benchmark target contract mismatch for {target.selector!r}: {observed!r} != {expected!r}'
                )

    @staticmethod
    def _normalize_string_sequence(raw_value: object, *, field_name: str) -> tuple[str, ...]:
        if not isinstance(raw_value, (list, tuple)) or not raw_value:
            raise ValueError(f'benchmark_matrix.{field_name} must be a non-empty list')
        normalized: list[str] = []
        for item in raw_value:
            value = str(item or '').strip()
            if not value:
                raise ValueError(f'benchmark_matrix.{field_name} contains an empty value')
            if value not in normalized:
                normalized.append(value)
        return tuple(normalized)

    @staticmethod
    def _parse_execution_targets(raw_value: object) -> tuple[BenchmarkExecutionTarget, ...]:
        if not isinstance(raw_value, (list, tuple)) or not raw_value:
            raise ValueError('benchmark_matrix.required_pairs.execution_targets must be a non-empty list')
        targets: list[BenchmarkExecutionTarget] = []
        seen: set[tuple[str, str]] = set()
        for item in raw_value:
            if not isinstance(item, Mapping):
                raise ValueError('benchmark matrix execution target must be a mapping')
            selector = str(item.get('selector', '')).strip()
            contract = benchmark_target_contract(selector)
            execution_environment = str(item.get('execution_environment', contract.execution_environment if contract is not None else 'headless')).strip() or 'headless'
            target = BenchmarkExecutionTarget(
                kind=str(item.get('kind', '')).strip(),
                selector=selector,
                execution_environment=execution_environment,
            )
            if target.kind != 'pytest':
                raise ValueError(f'unsupported benchmark execution target kind: {target.kind!r}')
            if not target.selector:
                raise ValueError('benchmark execution target selector must be non-empty')
            if contract is None:
                raise ValueError(f'benchmark execution target selector missing semantic contract: {target.selector!r}')
            if contract.execution_environment != target.execution_environment:
                raise ValueError(
                    f'benchmark execution target environment mismatch for {target.selector!r}: '
                    f'{target.execution_environment!r} != {contract.execution_environment!r}'
                )
            key = (target.kind, target.selector)
            if key not in seen:
                seen.add(key)
                targets.append(target)
        return tuple(targets)
