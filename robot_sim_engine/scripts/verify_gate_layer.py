from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from robot_sim.infra.quality_gate_catalog import quality_gate_ids_for_layer  # noqa: E402
from robot_sim.infra.quality_gate_runner import execute_quality_gates  # noqa: E402


_ALLOWED_LAYERS = ('release_blockers', 'runtime_contracts', 'governance_evidence')


def verify_gate_layer(layer: str, *, repo_root: Path = REPO_ROOT) -> int:
    normalized = str(layer or '').strip()
    if normalized not in _ALLOWED_LAYERS:
        raise ValueError(f'unsupported quality gate layer: {normalized!r}')
    gate_ids = quality_gate_ids_for_layer(normalized)
    if not gate_ids:
        raise ValueError(f'quality gate layer has no registered gates: {normalized}')
    results = execute_quality_gates(gate_ids, repo_root=repo_root)
    failed = [gate_id for gate_id, result in results.items() if not result.ok]
    if failed:
        for gate_id in failed:
            summary = results[gate_id].summary()
            print(f'{normalized} gate failed: {gate_id} ({summary.get("failure_kind", "command_failure")})')
        return 1
    print(f'{normalized} verified ({len(gate_ids)} gates)')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Execute one declared quality-gate layer.')
    parser.add_argument('--layer', required=True, choices=_ALLOWED_LAYERS)
    args = parser.parse_args()
    return verify_gate_layer(args.layer)


if __name__ == '__main__':
    raise SystemExit(main())
