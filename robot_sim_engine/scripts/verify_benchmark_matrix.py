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
from robot_sim.infra.quality_evidence import QualityEvidenceRecord, write_quality_evidence  # noqa: E402
from robot_sim.infra.quality_gate_runner import execute_quality_gates  # noqa: E402


def _execute_pytest_targets(repo_root: Path, targets: tuple[str, ...]) -> None:
    if not targets:
        return
    command = [sys.executable, '-m', 'pytest', '-q', *targets]
    completed = subprocess.run(command, cwd=repo_root, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify the benchmark execution matrix and optionally execute its required targets.')
    parser.add_argument('--execute', action='store_true', help='Execute the unique pytest targets declared by the matrix.')
    parser.add_argument('--execute-gates', action='store_true', help='Execute the matrix-level quality gates before running pytest targets.')
    parser.add_argument('--evidence-out', type=Path, default=None, help='Optional JSON path used to persist structured benchmark evidence records.')
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    service = BenchmarkMatrixService(repo_root / 'configs' / 'benchmark_matrix.yaml')
    matrix = service.load()
    if args.execute_gates:
        gate_results = execute_quality_gates(matrix.required_quality_gates, repo_root=repo_root)
        failed = [gate_id for gate_id, result in gate_results.items() if not result.ok]
        if failed:
            for gate_id in failed:
                print(f'benchmark matrix quality gate failed: {gate_id}')
            raise SystemExit(1)
    target_ok = True
    if args.execute:
        try:
            _execute_pytest_targets(repo_root, matrix.pytest_targets)
        except SystemExit as exc:
            target_ok = False
            raise
        finally:
            if args.evidence_out is not None:
                records = [
                    QualityEvidenceRecord(
                        evidence_id='benchmark_matrix',
                        category='benchmark_matrix',
                        ok=bool(target_ok),
                        details={
                            'matrix_id': matrix.matrix_id,
                            'required_quality_gates': list(matrix.required_quality_gates),
                            'pytest_targets': list(matrix.pytest_targets),
                        },
                    )
                ]
                write_quality_evidence(args.evidence_out, records)
    elif args.evidence_out is not None:
        records = [
            QualityEvidenceRecord(
                evidence_id='benchmark_matrix',
                category='benchmark_matrix',
                ok=True,
                details={
                    'matrix_id': matrix.matrix_id,
                    'required_quality_gates': list(matrix.required_quality_gates),
                    'pytest_targets': list(matrix.pytest_targets),
                },
            )
        ]
        write_quality_evidence(args.evidence_out, records)
    print(f'benchmark matrix verified: {matrix.matrix_id} pairs={len(matrix.required_pairs)} targets={len(matrix.pytest_targets)}')
