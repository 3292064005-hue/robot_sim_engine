from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from robot_sim.infra.quality_evidence import QualityEvidenceRecord, runtime_environment_fingerprint, write_quality_evidence, write_quality_evidence_markdown
from robot_sim.infra.quality_gate_runner import execute_quality_gates
from scripts.collect_quality_evidence import build_release_manifest
from robot_sim.infra.compatibility_budget import load_compatibility_budgets
from robot_sim.infra.compatibility_usage import write_compatibility_usage_snapshot

_DEFAULT_GATES = ('runtime_contracts', 'compatibility_budget')


def _ensure_compatibility_inventory_report() -> Path:
    """Generate the compatibility inventory snapshot required by retirement and budget gates.

    Returns:
        Path: Path to the generated compatibility inventory report.

    Raises:
        RuntimeError: If the prerequisite inventory report cannot be generated.
    """
    report_path = REPO_ROOT / 'artifacts' / 'compatibility_usage_report.json'
    budgets = load_compatibility_budgets(REPO_ROOT / 'configs' / 'compatibility_budget.yaml')
    scenario = 'clean_headless_mainline'
    budget = budgets[scenario]

    # Seed a structurally valid report first so retirement verification can resolve its inventory input.
    write_compatibility_usage_snapshot(report_path, scenario=scenario, budget=budget, violations=())

    command = [
        sys.executable,
        'scripts/verify_compatibility_budget.py',
        '--scenario',
        scenario,
        '--report-out',
        str(report_path),
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not report_path.exists():
        raise RuntimeError(
            'failed to generate compatibility inventory report for local evidence bundle: '
            f'returncode={completed.returncode}; stdout={completed.stdout!r}; stderr={completed.stderr!r}'
        )
    return report_path


def _record_from_result(gate_id: str, result) -> QualityEvidenceRecord:
    return QualityEvidenceRecord(
        evidence_id=str(gate_id),
        category='quality_gate',
        ok=bool(result.ok),
        environment=runtime_environment_fingerprint(REPO_ROOT),
        details=result.summary(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Build a reviewable local quality-evidence bundle.')
    parser.add_argument('--outdir', type=Path, default=REPO_ROOT / 'artifacts' / 'local_quality_evidence', help='output directory for the local evidence bundle')
    parser.add_argument('--gate', action='append', dest='gates', default=[], help='quality gate id to execute; may be passed multiple times')
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    _ensure_compatibility_inventory_report()
    gate_ids = tuple(dict.fromkeys(args.gates or _DEFAULT_GATES))
    results = execute_quality_gates(gate_ids, repo_root=REPO_ROOT)
    records = tuple(_record_from_result(gate_id, results[gate_id]) for gate_id in gate_ids)

    evidence_path = write_quality_evidence(outdir / 'quality_evidence.json', records)
    markdown_path = write_quality_evidence_markdown(outdir / 'quality_evidence.md', records)
    manifest = build_release_manifest(records, merged_files=(evidence_path,), executed_gate_ids=gate_ids, repo_root=REPO_ROOT)
    (outdir / 'release_manifest.json').write_text(__import__('json').dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'quality_evidence={evidence_path}')
    print(f'quality_evidence_markdown={markdown_path}')
    print(f'release_manifest={outdir / "release_manifest.json"}')
    return 0 if all(record.ok for record in records) else 1


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
