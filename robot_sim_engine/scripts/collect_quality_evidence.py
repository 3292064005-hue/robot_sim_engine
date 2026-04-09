from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from robot_sim.infra.quality_evidence import QualityEvidenceRecord, write_quality_evidence, write_quality_evidence_markdown
from robot_sim.infra.quality_gate_runner import execute_quality_gates


def _load_records(path: Path) -> list[QualityEvidenceRecord]:
    payload = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    records: list[QualityEvidenceRecord] = []
    for item in payload:
        records.append(
            QualityEvidenceRecord(
                evidence_id=str(item.get('evidence_id', '')),
                category=str(item.get('category', 'unknown')),
                ok=bool(item.get('ok', False)),
                environment=dict(item.get('environment', {}) or {}),
                details=dict(item.get('details', {}) or {}),
            )
        )
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect quality evidence records for a set of quality gates and pre-generated evidence files.')
    parser.add_argument('--out', type=Path, default=REPO_ROOT / 'artifacts' / 'quality_evidence.json', help='Output JSON path.')
    parser.add_argument('--merge', nargs='*', default=(), help='Optional evidence JSON files to merge into the collected output.')
    parser.add_argument('--markdown-out', type=Path, default=None, help='Optional markdown path used to render a human-readable evidence view.')
    parser.add_argument('gate_ids', nargs='*', help='Quality gate IDs to execute and record.')
    args = parser.parse_args()

    results = execute_quality_gates(tuple(str(item) for item in args.gate_ids), repo_root=REPO_ROOT)
    records = [
        QualityEvidenceRecord(
            evidence_id=gate_id,
            category='quality_gate',
            ok=result.ok,
            details=result.summary(),
        )
        for gate_id, result in results.items()
    ]
    for merge_path in tuple(Path(item) for item in args.merge):
        records.extend(_load_records(merge_path))
    write_quality_evidence(args.out, records)
    if args.markdown_out is not None:
        write_quality_evidence_markdown(args.markdown_out, records)
    failed = [record.evidence_id for record in records if not record.ok]
    if failed:
        for gate_id in failed:
            print(f'quality evidence gate failed: {gate_id}')
        raise SystemExit(1)
    print(f'quality evidence written: {args.out}')
