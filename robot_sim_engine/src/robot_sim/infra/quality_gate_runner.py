from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Iterable

from robot_sim.infra.quality_gate_catalog import quality_gate_definition


@dataclass(frozen=True)
class QualityGateCommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return int(self.returncode) == 0


@dataclass(frozen=True)
class QualityGateExecutionResult:
    gate_id: str
    ok: bool
    commands: tuple[QualityGateCommandResult, ...]

    def summary(self) -> dict[str, object]:
        return {
            'gate_id': self.gate_id,
            'ok': bool(self.ok),
            'commands': [
                {
                    'command': list(item.command),
                    'returncode': int(item.returncode),
                    'stdout': item.stdout,
                    'stderr': item.stderr,
                }
                for item in self.commands
            ],
        }


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
    return QualityGateExecutionResult(gate_id=str(gate_id), ok=bool(overall_ok), commands=tuple(command_results))


def execute_quality_gates(gate_ids: Iterable[str], *, repo_root: str | Path) -> dict[str, QualityGateExecutionResult]:
    results: dict[str, QualityGateExecutionResult] = {}
    for gate_id in tuple(str(item) for item in gate_ids):
        if gate_id in results:
            continue
        results[gate_id] = execute_quality_gate(gate_id, repo_root=repo_root)
    return results
