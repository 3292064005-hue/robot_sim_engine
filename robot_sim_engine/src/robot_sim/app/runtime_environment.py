from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from robot_sim.app.runtime_paths import RuntimePaths
from robot_sim.infra.release_environment_gate import ReleaseEnvironmentGate, ReleaseEnvironmentReport


@dataclass(frozen=True)
class StartupEnvironmentStatus:
    mode: str
    report: ReleaseEnvironmentReport | None
    strict: bool

    @property
    def ok(self) -> bool:
        return True if self.report is None else bool(self.report.ok)

    def summary(self) -> dict[str, object]:
        if self.report is None:
            return {'mode': self.mode, 'strict': self.strict, 'enabled': False, 'ok': True, 'errors': [], 'warnings': []}
        return {
            'mode': self.mode,
            'strict': bool(self.strict),
            'enabled': True,
            'ok': bool(self.report.ok),
            'errors': list(self.report.errors),
            'warnings': list(self.report.warnings),
        }


def evaluate_startup_environment(runtime_paths: RuntimePaths, *, mode: str = 'gui') -> StartupEnvironmentStatus:
    normalized_mode = str(mode or 'gui').strip().lower() or 'gui'
    config_path = Path(runtime_paths.config_root) / 'release_environment.yaml'
    strict_env = str(os.environ.get('ROBOT_SIM_STRICT_RUNTIME_ENVIRONMENT', '') or '').strip()
    if strict_env == '1':
        strict = True
    elif strict_env == '0':
        strict = False
    else:
        strict = normalized_mode in {'gui', 'release'}
    if normalized_mode == 'headless' or not config_path.exists():
        return StartupEnvironmentStatus(mode=normalized_mode, report=None, strict=strict)
    report = ReleaseEnvironmentGate(config_path).evaluate(normalized_mode)
    return StartupEnvironmentStatus(mode=normalized_mode, report=report, strict=strict)
