from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _configure_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / 'src'
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_configure_path()

from robot_sim.application.services.benchmark_matrix_service import BenchmarkMatrixService  # noqa: E402
from robot_sim.infra.quality_evidence import QualityEvidenceRecord, runtime_environment_fingerprint, write_quality_evidence  # noqa: E402
from robot_sim.infra.quality_gate_runner import execute_quality_gates  # noqa: E402


def build_benchmark_evidence_details(*, matrix, executed_gate_results: dict[str, dict[str, object]], execute_gates_requested: bool, execute_requested: bool, gate_ok: bool, target_ok: bool | None, executed_pytest_command: list[str]) -> dict[str, object]:
    executed_pytest = bool(execute_requested and gate_ok)
    pytest_targets_status = 'not_requested'
    pytest_targets_failure_kind = 'none'
    if execute_requested:
        if gate_ok:
            pytest_targets_status = 'passed' if target_ok else 'failed'
            pytest_targets_failure_kind = 'none' if target_ok else 'command_failure'
        else:
            pytest_targets_status = 'skipped_due_to_failed_gates'
            pytest_targets_failure_kind = 'gates_failed'
    return {
        'matrix_id': matrix.matrix_id,
        'execute_gates_requested': bool(execute_gates_requested),
        'execute_requested': bool(execute_requested),
        'required_quality_gates': list(matrix.required_quality_gates),
        'executed_gate_results': executed_gate_results,
        'required_gate_result_count': len(tuple(matrix.required_quality_gates)),
        'executed_gate_result_count': len(executed_gate_results),
        'environment_failures': [gate_id for gate_id, result in executed_gate_results.items() if result.get('failure_kind') == 'environment_mismatch'],
        'tooling_failures': [gate_id for gate_id, result in executed_gate_results.items() if result.get('failure_kind') == 'tooling_missing'],
        'command_failures': [gate_id for gate_id, result in executed_gate_results.items() if result.get('failure_kind') == 'command_failure'],
        'pytest_targets': list(matrix.pytest_targets),
        'pytest_targets_executed': executed_pytest,
        'pytest_targets_command': executed_pytest_command,
        'pytest_targets_status': pytest_targets_status,
        'pytest_targets_ok': target_ok if executed_pytest else None,
        'pytest_targets_failure_kind': pytest_targets_failure_kind,
    }


def _execute_pytest_targets(repo_root: Path, targets: tuple[str, ...]) -> tuple[bool, list[str]]:
    if not targets:
        return True, []
    command = [sys.executable, '-m', 'pytest', '-q', *targets]
    completed = subprocess.run(command, cwd=repo_root, check=False)
    return completed.returncode == 0, command


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify the benchmark execution matrix and optionally execute its required targets.')
    parser.add_argument('--execute', action='store_true', help='Execute the unique pytest targets declared by the matrix.')
    parser.add_argument('--execute-gates', action='store_true', help='Execute the matrix-level quality gates before running pytest targets.')
    parser.add_argument('--evidence-out', type=Path, default=None, help='Optional JSON path used to persist structured benchmark evidence records.')
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    service = BenchmarkMatrixService(repo_root / 'configs' / 'benchmark_matrix.yaml')
    matrix = service.load()

    executed_gate_results = {}
    gate_ok = True
    if args.execute_gates:
        gate_results = execute_quality_gates(matrix.required_quality_gates, repo_root=repo_root)
        executed_gate_results = {gate_id: result.summary() for gate_id, result in gate_results.items()}
        gate_ok = all(result.get('ok', False) for result in executed_gate_results.values())
        if not gate_ok:
            for gate_id, result in executed_gate_results.items():
                if not result.get('ok', False):
                    print(f"benchmark matrix quality gate failed: {gate_id} ({result.get('failure_kind', 'command_failure')})")

    target_ok: bool | None = None
    executed_pytest_command: list[str] = []
    if args.execute and gate_ok:
        target_ok, executed_pytest_command = _execute_pytest_targets(repo_root, matrix.pytest_targets)

    overall_ok = bool(gate_ok and (target_ok is not False))
    if args.evidence_out is not None:
        records = [
            QualityEvidenceRecord(
                evidence_id='benchmark_matrix',
                category='benchmark_matrix',
                ok=overall_ok,
                environment=runtime_environment_fingerprint(repo_root),
                details=build_benchmark_evidence_details(
                    matrix=matrix,
                    executed_gate_results=executed_gate_results,
                    execute_gates_requested=bool(args.execute_gates),
                    execute_requested=bool(args.execute),
                    gate_ok=gate_ok,
                    target_ok=target_ok,
                    executed_pytest_command=executed_pytest_command,
                ),
            )
        ]
        write_quality_evidence(args.evidence_out, records)
    if not overall_ok:
        raise SystemExit(1)
    print(f'benchmark matrix verified: {matrix.matrix_id} pairs={len(matrix.required_pairs)} targets={len(matrix.pytest_targets)}')
