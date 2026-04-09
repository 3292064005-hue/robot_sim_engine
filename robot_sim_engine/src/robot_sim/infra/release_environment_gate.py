from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from robot_sim.infra.runtime_baseline import evaluate_runtime_baseline, _is_version_at_least


def _dedupe_messages(messages: list[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for item in messages:
        normalized = str(item).strip()
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return tuple(ordered)


@dataclass(frozen=True)
class ReleaseEnvironmentContract:
    platform_system: str
    os_id: str
    os_version_id: str
    python_major: int
    python_minor: int
    requires_build: bool = False
    pyside_min_version: str = ''


@dataclass(frozen=True)
class ReleaseEnvironmentReport:
    mode: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class ReleaseEnvironmentGate:
    """Load and enforce the checked-in release environment contract."""

    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path)

    def load_contract(self, mode: str) -> ReleaseEnvironmentContract:
        payload = yaml.safe_load(self._config_path.read_text(encoding='utf-8')) or {}
        if not isinstance(payload, Mapping):
            raise ValueError(f'release environment config must be a mapping: {self._config_path}')
        root = payload.get('release_environment')
        if not isinstance(root, Mapping):
            raise ValueError(f'release_environment root missing or invalid: {self._config_path}')
        section = root.get(str(mode))
        if not isinstance(section, Mapping):
            raise ValueError(f'release environment mode missing or invalid: {mode}')
        return ReleaseEnvironmentContract(
            platform_system=str(section.get('platform_system', '')).strip(),
            os_id=str(section.get('os_id', '')).strip(),
            os_version_id=str(section.get('os_version_id', '')).strip(),
            python_major=int(section.get('python_major', 0)),
            python_minor=int(section.get('python_minor', 0)),
            requires_build=bool(section.get('requires_build', False)),
            pyside_min_version=str(section.get('pyside_min_version', '')).strip(),
        )

    def evaluate(self, mode: str) -> ReleaseEnvironmentReport:
        contract = self.load_contract(mode)
        baseline = evaluate_runtime_baseline('gui' if mode == 'gui' else 'release' if mode == 'release' else 'headless')
        errors = list(baseline.errors)
        warnings = list(baseline.warnings)
        if contract.platform_system and baseline.platform_system != contract.platform_system:
            errors.append(f'{mode} environment requires platform {contract.platform_system}, got {baseline.platform_system}')
        if contract.os_id and baseline.os_id != contract.os_id:
            errors.append(f'{mode} environment requires os_id {contract.os_id}, got {baseline.os_id or "unknown"}')
        if contract.os_version_id and baseline.os_version_id != contract.os_version_id:
            errors.append(f'{mode} environment requires os_version_id {contract.os_version_id}, got {baseline.os_version_id or "unknown"}')
        if contract.python_major and contract.python_minor:
            expected = f'{contract.python_major}.{contract.python_minor}'
            if baseline.python_version.split('.')[:2] != [str(contract.python_major), str(contract.python_minor)]:
                errors.append(f'{mode} environment requires Python {expected}, got {baseline.python_version}')
        if contract.requires_build and not baseline.build_available:
            errors.append(f'{mode} environment requires build tooling to be installed')
        if contract.pyside_min_version:
            observed = baseline.pyside_version or ''
            if not observed:
                errors.append(f'{mode} environment requires PySide6 >= {contract.pyside_min_version}, got missing')
            elif not _is_version_at_least(observed, major=int(contract.pyside_min_version.split('.')[0]), minor=int(contract.pyside_min_version.split('.')[1])):
                errors.append(f'{mode} environment requires PySide6 >= {contract.pyside_min_version}, got {observed}')
        return ReleaseEnvironmentReport(mode=str(mode), errors=_dedupe_messages(errors), warnings=_dedupe_messages(warnings))
