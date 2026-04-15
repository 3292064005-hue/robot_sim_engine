from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

def _configure_path() -> None:
    src_root = REPO_ROOT / 'src'
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_configure_path()

import argparse
import json

from robot_sim.domain.module_governance import governance_for_module, verify_experimental_module_governance  # noqa: E402
from robot_sim.domain.runtime_contracts import MODULE_STATUSES  # noqa: E402
from robot_sim.infra.quality_evidence import QualityEvidenceRecord, runtime_environment_fingerprint, write_quality_evidence  # noqa: E402
from robot_sim.infra.quality_gate_runner import execute_quality_gates  # noqa: E402


def _module_status_label(payload: object) -> str:
    if isinstance(payload, dict):
        return str(payload.get('status', 'unknown'))
    return str(payload)


def _required_gates() -> tuple[str, ...]:
    gates: list[str] = []
    for module_id, status in MODULE_STATUSES.items():
        if _module_status_label(status) != 'experimental':
            continue
        policy = governance_for_module(str(module_id))
        if policy is None:
            continue
        for gate in policy.required_quality_gates:
            if gate not in gates:
                gates.append(gate)
    return tuple(gates)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify experimental module governance metadata and optionally execute promotion gates.')
    parser.add_argument('--execute-gates', action='store_true', help='Execute the union of required quality gates and feed their results into governance evaluation.')
    parser.add_argument('--json-out', type=Path, default=None, help='Optional JSON path used to persist the executed gate ok-map.')
    parser.add_argument('--evidence-out', type=Path, default=None, help='Optional JSON path used to persist structured governance evidence records.')
    args = parser.parse_args()

    required_gates = _required_gates()
    executed_gate_results = {}
    gate_results: dict[str, bool] | None = None
    if args.execute_gates:
        executed = execute_quality_gates(required_gates, repo_root=REPO_ROOT)
        executed_gate_results = {gate_id: result.summary() for gate_id, result in executed.items()}
        gate_results = {gate_id: bool(result.ok) for gate_id, result in executed.items()}
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(gate_results, indent=2, sort_keys=True), encoding='utf-8')
    errors = verify_experimental_module_governance(
        MODULE_STATUSES,
        repo_root=str(REPO_ROOT),
        gate_results=gate_results,
        require_gate_results=bool(args.execute_gates),
    )
    if args.evidence_out is not None:
        records = [
            QualityEvidenceRecord(
                evidence_id='module_governance',
                category='governance',
                ok=not errors,
                environment=runtime_environment_fingerprint(REPO_ROOT),
                details={
                    'execute_gates_requested': bool(args.execute_gates),
                    'required_gates': list(required_gates),
                    'executed_gates': dict(gate_results or {}),
                    'executed_gate_results': executed_gate_results,
                    'required_gate_result_count': len(required_gates),
                    'executed_gate_result_count': len(executed_gate_results),
                    'failed_gates': [gate_id for gate_id, result in executed_gate_results.items() if not result.get('ok', False)],
                    'environment_failures': [
                        gate_id for gate_id, result in executed_gate_results.items() if result.get('failure_kind') == 'environment_mismatch'
                    ],
                    'tooling_failures': [
                        gate_id for gate_id, result in executed_gate_results.items() if result.get('failure_kind') == 'tooling_missing'
                    ],
                    'command_failures': [
                        gate_id for gate_id, result in executed_gate_results.items() if result.get('failure_kind') == 'command_failure'
                    ],
                    'error_count': len(errors),
                    'errors': list(errors),
                },
            )
        ]
        write_quality_evidence(args.evidence_out, records)
    if errors:
        for item in errors:
            print(item)
        raise SystemExit(1)
    print('module governance verified')
