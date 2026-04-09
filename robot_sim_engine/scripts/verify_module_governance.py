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
from robot_sim.infra.quality_evidence import QualityEvidenceRecord, write_quality_evidence  # noqa: E402
from robot_sim.infra.quality_gate_runner import execute_quality_gates  # noqa: E402


def _required_gates() -> tuple[str, ...]:
    gates: list[str] = []
    for module_id, status in MODULE_STATUSES.items():
        if str(status) != 'experimental':
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
    parser.add_argument('--json-out', type=Path, default=None, help='Optional JSON path used to persist executed gate results.')
    parser.add_argument('--evidence-out', type=Path, default=None, help='Optional JSON path used to persist structured governance evidence records.')
    args = parser.parse_args()

    gate_results: dict[str, bool] | None = None
    if args.execute_gates:
        executed = execute_quality_gates(_required_gates(), repo_root=REPO_ROOT)
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
                details={'executed_gates': dict(gate_results or {}), 'error_count': len(errors)},
            )
        ]
        write_quality_evidence(args.evidence_out, records)
    if errors:
        for item in errors:
            print(item)
        raise SystemExit(1)
    print('module governance verified')
