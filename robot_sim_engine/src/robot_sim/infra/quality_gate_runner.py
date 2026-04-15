from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Iterable

from robot_sim.infra.quality_gate_catalog import quality_gate_definition

def _parse_gui_smoke_details(commands: tuple["QualityGateCommandResult", ...]) -> dict[str, object]:
    """Extract structured GUI runtime classification from ``gui_smoke`` command output.

    Args:
        commands: Executed command results for the GUI smoke gate.

    Returns:
        dict[str, object]: Parsed runtime-kind and real/shim booleans when present.
    """
    runtime_kind = 'unknown'
    qt_platform = ''
    real_runtime_ok = False
    shim_runtime_ok = False
    for command in commands:
        for line in str(command.stdout or '').splitlines():
            line = str(line).strip()
            if line.startswith('runtime_kind='):
                runtime_kind = line.split('=', 1)[1].strip() or runtime_kind
            elif line.startswith('qt_platform='):
                qt_platform = line.split('=', 1)[1].strip()
            elif line.startswith('real_runtime_ok='):
                real_runtime_ok = line.split('=', 1)[1].strip().lower() == 'true'
            elif line.startswith('shim_runtime_ok='):
                shim_runtime_ok = line.split('=', 1)[1].strip().lower() == 'true'
    return {
        'gui_runtime_kind': runtime_kind,
        'gui_qt_platform': qt_platform,
        'gui_real_runtime_ok': bool(real_runtime_ok),
        'gui_shim_runtime_ok': bool(shim_runtime_ok),
    }


@dataclass(frozen=True)
class QualityGateCommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return int(self.returncode) == 0

    @property
    def failure_kind(self) -> str:
        if self.ok:
            return 'none'
        haystack = (str(self.stdout or '') + '\n' + str(self.stderr or '')).lower()
        environment_markers = (
            'baseline requires',
            'environment requires',
            'requires ubuntu',
            'requires python',
            'requires pyside6',
            'pyside6 is unavailable',
            'build=missing',
            'got missing',
        )
        if any(marker in haystack for marker in environment_markers):
            return 'environment_mismatch'
        if 'command unavailable' in haystack:
            return 'tooling_missing'
        return 'command_failure'


@dataclass(frozen=True)
class QualityGateExecutionResult:
    gate_id: str
    ok: bool
    commands: tuple[QualityGateCommandResult, ...]
    environment: str = 'headless'

    @property
    def failure_kind(self) -> str:
        for command in self.commands:
            if not command.ok:
                return command.failure_kind
        return 'none'

    def summary(self) -> dict[str, object]:
        summary = {
            'gate_id': self.gate_id,
            'ok': bool(self.ok),
            'environment': self.environment,
            'failure_kind': self.failure_kind,
            'commands': [
                {
                    'command': list(item.command),
                    'returncode': int(item.returncode),
                    'stdout': item.stdout,
                    'stderr': item.stderr,
                    'failure_kind': item.failure_kind,
                }
                for item in self.commands
            ],
        }
        if self.gate_id == 'gui_smoke':
            summary.update(_parse_gui_smoke_details(self.commands))
        return summary


def _normalize_command(command: tuple[str, ...]) -> tuple[str, ...]:
    if not command:
        raise ValueError('quality gate command must be non-empty')
    head = str(command[0]).strip()
    if head == 'python':
        return (sys.executable, *command[1:])
    if head == 'pytest':
        return (sys.executable, '-m', 'pytest', *command[1:])
    if head == 'mypy':
        return (sys.executable, '-m', 'mypy', *command[1:])
    return tuple(str(item) for item in command)


def execute_quality_gate(gate_id: str, *, repo_root: str | Path) -> QualityGateExecutionResult:
    definition = quality_gate_definition(gate_id)
    if definition is None:
        raise ValueError(f'unknown quality gate: {gate_id}')
    root = Path(repo_root)
    command_results: list[QualityGateCommandResult] = []
    overall_ok = True
    for command in definition.commands:
        normalized = _normalize_command(tuple(command))
        try:
            completed = subprocess.run(
                normalized,
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            result = QualityGateCommandResult(
                command=tuple(normalized),
                returncode=int(completed.returncode),
                stdout=str(completed.stdout or ''),
                stderr=str(completed.stderr or ''),
            )
        except FileNotFoundError as exc:
            result = QualityGateCommandResult(
                command=tuple(normalized),
                returncode=127,
                stdout='',
                stderr=f'command unavailable: {normalized[0]} ({exc})',
            )
        command_results.append(result)
        if not result.ok:
            overall_ok = False
            break
    return QualityGateExecutionResult(
        gate_id=str(gate_id),
        ok=bool(overall_ok),
        commands=tuple(command_results),
        environment=str(definition.environment or 'headless'),
    )


def execute_quality_gates(gate_ids: Iterable[str], *, repo_root: str | Path) -> dict[str, QualityGateExecutionResult]:
    results: dict[str, QualityGateExecutionResult] = {}
    for gate_id in tuple(str(item) for item in gate_ids):
        if gate_id in results:
            continue
        results[gate_id] = execute_quality_gate(gate_id, repo_root=repo_root)
    return results
