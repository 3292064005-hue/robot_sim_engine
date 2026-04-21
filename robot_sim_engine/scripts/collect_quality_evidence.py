from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from robot_sim.infra.quality_evidence import (  # noqa: E402
    QualityEvidenceRecord,
    runtime_environment_fingerprint,
    write_quality_evidence,
    write_quality_evidence_markdown,
)
from robot_sim.infra.quality_gate_catalog import quality_gate_definition  # noqa: E402
from robot_sim.infra.quality_gate_runner import execute_quality_gates  # noqa: E402
from robot_sim.infra.release_environment_gate import ReleaseEnvironmentGate  # noqa: E402

_REQUIRED_PROVENANCE_FIELDS = (
    'repo_root',
    'source_tree_fingerprint',
    'source_tree_file_count',
    'generated_at_utc',
)


def _build_record(item: dict[str, object]) -> QualityEvidenceRecord:
    return QualityEvidenceRecord(
        evidence_id=str(item.get('evidence_id', '')),
        category=str(item.get('category', 'unknown')),
        ok=bool(item.get('ok', False)),
        environment=dict(item.get('environment', {}) or {}),
        details=dict(item.get('details', {}) or {}),
    )


def _expected_provenance(repo_root: Path) -> dict[str, str]:
    env = runtime_environment_fingerprint(repo_root)
    return {key: str(env.get(key, '')) for key in _REQUIRED_PROVENANCE_FIELDS}


def _transport_relative(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


def _normalize_loaded_record(record: QualityEvidenceRecord, *, source_path: Path, repo_root: Path) -> QualityEvidenceRecord:
    details = dict(record.details or {})
    integrity_errors: list[str] = [str(item) for item in details.get('integrity_errors', []) if str(item).strip()]

    if record.evidence_id == 'module_governance':
        required = tuple(str(item) for item in details.get('required_gates', ()) or ())
        executed = dict(details.get('executed_gate_results', {}) or {})
        execute_gates_requested = details.get('execute_gates_requested')
        if required and execute_gates_requested is not True:
            integrity_errors.append('module_governance evidence must be generated with --execute-gates')
        if required and set(executed) != set(required):
            integrity_errors.append('module_governance evidence must include executed results for every required gate')
    if record.evidence_id == 'benchmark_matrix':
        required = tuple(str(item) for item in details.get('required_quality_gates', ()) or ())
        executed = dict(details.get('executed_gate_results', {}) or {})
        execute_gates_requested = details.get('execute_gates_requested')
        if required and execute_gates_requested is not True:
            integrity_errors.append('benchmark_matrix evidence must be generated with --execute-gates')
        if required and set(executed) != set(required):
            integrity_errors.append('benchmark_matrix evidence must include executed results for every required quality gate')
        targets_executed = bool(details.get('executed_targets', False))
        target_ok = details.get('target_ok')
        target_status = str(details.get('target_status', ''))
        if not targets_executed and target_ok is not None:
            integrity_errors.append('benchmark_matrix evidence cannot mark benchmark targets ok when targets were not executed')
        if not targets_executed and target_status not in {'not_requested', 'skipped_due_to_failed_gates'}:
            integrity_errors.append('benchmark_matrix evidence must explain why benchmark targets were not executed')

    environment = dict(record.environment or {})
    expected_provenance = _expected_provenance(repo_root)
    for key in _REQUIRED_PROVENANCE_FIELDS:
        value = str(environment.get(key, '') or '')
        if not value:
            integrity_errors.append(f'{record.evidence_id} evidence is missing provenance field: {key}')
    expected_repo_root = expected_provenance['repo_root']
    for key in ('source_tree_fingerprint', 'source_tree_file_count'):
        actual = str(environment.get(key, '') or '')
        expected = expected_provenance[key]
        if actual and actual != expected:
            integrity_errors.append(
                f'{record.evidence_id} evidence provenance drifted for {key}: expected {expected}, got {actual}'
            )

    nested_gui = details.get('executed_gate_results', {}) if isinstance(details.get('executed_gate_results', {}), dict) else {}
    if isinstance(nested_gui, dict) and 'gui_smoke' in nested_gui:
        gui_result = nested_gui.get('gui_smoke')
        if not isinstance(gui_result, dict):
            integrity_errors.append(f'{record.evidence_id} evidence must record gui_smoke as a structured result mapping')
        else:
            for key in ('gui_runtime_kind', 'gui_qt_platform', 'gui_real_runtime_ok', 'gui_shim_runtime_ok'):
                if key not in gui_result:
                    integrity_errors.append(f'{record.evidence_id} evidence must preserve gui_smoke field: {key}')

    if integrity_errors:
        details['integrity_errors'] = sorted(dict.fromkeys(integrity_errors))
        details['integrity_source_path'] = str(source_path)
        details['integrity_expected_repo_root'] = expected_repo_root
        details['integrity_expected_source_tree_fingerprint'] = expected_provenance['source_tree_fingerprint']
        return QualityEvidenceRecord(
            evidence_id=record.evidence_id,
            category=record.category,
            ok=False,
            environment=dict(record.environment or {}),
            details=details,
        )
    return record


def _load_records(path: Path, *, repo_root: Path = REPO_ROOT) -> list[QualityEvidenceRecord]:
    if not path.exists():
        raise FileNotFoundError(f'evidence file not found: {path}')
    payload = json.loads(path.read_text(encoding='utf-8'))
    records: list[QualityEvidenceRecord] = []
    for item in payload:
        record = _build_record(dict(item or {}))
        records.append(_normalize_loaded_record(record, source_path=path, repo_root=repo_root))
    return records


def _resolve_gate_and_merge_inputs(*, merge_items: tuple[str, ...], gate_items: tuple[str, ...], positional_items: tuple[str, ...]) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    merge_paths: list[Path] = []
    gate_ids: list[str] = []
    for gate_id in (*gate_items, *positional_items):
        normalized = str(gate_id).strip()
        if normalized and normalized not in gate_ids:
            gate_ids.append(normalized)
    for raw_item in merge_items:
        normalized = str(raw_item).strip()
        if not normalized:
            continue
        candidate = Path(normalized)
        if candidate.exists():
            merge_paths.append(candidate)
            continue
        if quality_gate_definition(normalized) is not None:
            if normalized not in gate_ids:
                gate_ids.append(normalized)
            continue
        raise FileNotFoundError(f'expected evidence file or known quality gate id, got: {normalized}')
    return tuple(merge_paths), tuple(gate_ids)


def _evaluate_release_environment(repo_root: Path) -> dict[str, object]:
    gate = ReleaseEnvironmentGate(repo_root / 'configs' / 'release_environment.yaml')
    release_report = gate.evaluate('release')
    gui_report = gate.evaluate('gui')
    failed_modes: list[str] = []
    if not release_report.ok:
        failed_modes.append('release_environment.release')
    if not gui_report.ok:
        failed_modes.append('release_environment.gui')
    return {
        'release_environment': {
            'release': {'ok': bool(release_report.ok), 'errors': list(release_report.errors), 'warnings': list(release_report.warnings)},
            'gui': {'ok': bool(gui_report.ok), 'errors': list(gui_report.errors), 'warnings': list(gui_report.warnings)},
        },
        'release_environment_failures': failed_modes,
    }


def build_release_manifest(records: tuple[QualityEvidenceRecord, ...], *, merged_files: tuple[Path, ...], executed_gate_ids: tuple[str, ...], repo_root: str | Path = REPO_ROOT) -> dict[str, object]:
    failed_ids = [record.evidence_id for record in records if not record.ok]
    environment_failures: list[str] = []
    tooling_failures: list[str] = []
    command_failures: list[str] = []
    integrity_failures: list[str] = []
    if not records:
        failed_ids.append('quality_evidence_collection')
        integrity_failures.append('quality_evidence_collection')
        command_failures.append('quality_evidence_collection')
    gui_runtime_kind = 'unknown'
    gui_qt_platform = ''
    gui_real_runtime_ok = False
    gui_shim_runtime_ok = False
    gui_smoke_executed = False
    gui_smoke_ok = False
    for record in records:
        failure_kind = str(record.details.get('failure_kind', 'none') or 'none')
        if record.category == 'quality_gate' and not record.ok:
            if failure_kind == 'environment_mismatch':
                environment_failures.append(record.evidence_id)
            elif failure_kind == 'tooling_missing':
                tooling_failures.append(record.evidence_id)
            else:
                command_failures.append(record.evidence_id)
        detail_environment_failures = record.details.get('environment_failures', ())
        if isinstance(detail_environment_failures, list):
            environment_failures.extend(str(item) for item in detail_environment_failures)
        detail_tooling_failures = record.details.get('tooling_failures', ())
        if isinstance(detail_tooling_failures, list):
            tooling_failures.extend(str(item) for item in detail_tooling_failures)
        detail_command_failures = record.details.get('command_failures', ())
        if isinstance(detail_command_failures, list):
            command_failures.extend(str(item) for item in detail_command_failures)
        detail_integrity_errors = record.details.get('integrity_errors', ())
        if isinstance(detail_integrity_errors, list) and detail_integrity_errors:
            integrity_failures.append(record.evidence_id)
            command_failures.append(record.evidence_id)
        executed_gate_results = dict(record.details.get('executed_gate_results', {}) or {})
        nested_gui = executed_gate_results.get('gui_smoke') if isinstance(executed_gate_results, dict) else None
        if isinstance(nested_gui, dict):
            gui_smoke_executed = True
            gui_smoke_ok = gui_smoke_ok or bool(nested_gui.get('ok', False))
            gui_runtime_kind = str(nested_gui.get('gui_runtime_kind', gui_runtime_kind) or gui_runtime_kind)
            gui_qt_platform = str(nested_gui.get('gui_qt_platform', gui_qt_platform) or gui_qt_platform)
            gui_real_runtime_ok = bool(nested_gui.get('gui_real_runtime_ok', gui_real_runtime_ok))
            gui_shim_runtime_ok = bool(nested_gui.get('gui_shim_runtime_ok', gui_shim_runtime_ok))
        if str(record.evidence_id) != 'gui_smoke':
            continue
        gui_smoke_executed = True
        gui_smoke_ok = gui_smoke_ok or bool(record.ok)
        gui_runtime_kind = str(record.details.get('gui_runtime_kind', record.details.get('runtime_kind', gui_runtime_kind)) or gui_runtime_kind)
        gui_qt_platform = str(record.details.get('gui_qt_platform', record.details.get('qt_platform', gui_qt_platform)) or gui_qt_platform)
        gui_real_runtime_ok = bool(record.details.get('gui_real_runtime_ok', record.details.get('real_runtime_ok', gui_real_runtime_ok)))
        gui_shim_runtime_ok = bool(record.details.get('gui_shim_runtime_ok', record.details.get('shim_runtime_ok', gui_shim_runtime_ok)))
    repo_root_path = Path(repo_root)
    environment_status = _evaluate_release_environment(repo_root_path)
    environment_failures.extend(str(item) for item in environment_status['release_environment_failures'])
    artifact_ready = not failed_ids
    environment_ready = not environment_status['release_environment_failures']
    return {
        'artifact_ready': bool(artifact_ready),
        'environment_ready': bool(environment_ready),
        'release_ready': bool(artifact_ready and environment_ready),
        'record_count': len(records),
        'failed_evidence_ids': failed_ids,
        'environment_failures': sorted(dict.fromkeys(environment_failures)),
        'tooling_failures': sorted(dict.fromkeys(tooling_failures)),
        'command_failures': sorted(dict.fromkeys(command_failures)),
        'integrity_failures': sorted(dict.fromkeys(integrity_failures)),
        'executed_gate_ids': list(executed_gate_ids),
        'merged_evidence_files': [_transport_relative(path, repo_root=repo_root_path) for path in merged_files],
        'generated_in_environment': runtime_environment_fingerprint(repo_root_path),
        'release_environment': dict(environment_status['release_environment']),
        'release_environment_failures': list(environment_status['release_environment_failures']),
        'gui_runtime': {
            'runtime_kind': gui_runtime_kind,
            'qt_platform': gui_qt_platform,
            'real_runtime_ok': bool(gui_real_runtime_ok),
            'shim_runtime_ok': bool(gui_shim_runtime_ok),
            'gui_smoke_executed': gui_smoke_executed,
            'gui_smoke_ok': gui_smoke_ok,
        },
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect quality evidence records for explicit quality gates and pre-generated evidence files.')
    parser.add_argument('--out', type=Path, default=REPO_ROOT / 'artifacts' / 'quality_evidence.json', help='Output JSON path.')
    parser.add_argument('--merge', nargs='*', default=(), help='Evidence JSON files to merge. Legacy gate ids are also accepted here and will be executed.')
    parser.add_argument('--gates', nargs='*', default=(), help='Explicit quality gate IDs to execute before merging evidence files.')
    parser.add_argument('--markdown-out', type=Path, default=None, help='Optional markdown path used to render a human-readable evidence view.')
    parser.add_argument('--release-manifest-out', type=Path, default=None, help='Optional release-manifest summary path recording whether every collected evidence item is green.')
    parser.add_argument('gate_ids', nargs='*', help='Legacy positional quality gate IDs to execute and record.')
    args = parser.parse_args()

    merge_paths, gate_ids = _resolve_gate_and_merge_inputs(
        merge_items=tuple(str(item) for item in args.merge),
        gate_items=tuple(str(item) for item in args.gates),
        positional_items=tuple(str(item) for item in args.gate_ids),
    )
    results = execute_quality_gates(gate_ids, repo_root=REPO_ROOT)
    records = [
        QualityEvidenceRecord(
            evidence_id=gate_id,
            category='quality_gate',
            ok=result.ok,
            environment=runtime_environment_fingerprint(REPO_ROOT),
            details=result.summary(),
        )
        for gate_id, result in results.items()
    ]
    for merge_path in merge_paths:
        records.extend(_load_records(merge_path, repo_root=REPO_ROOT))
    record_tuple = tuple(records)
    write_quality_evidence(args.out, record_tuple)
    if args.markdown_out is not None:
        write_quality_evidence_markdown(args.markdown_out, record_tuple)
    if args.release_manifest_out is not None:
        manifest = build_release_manifest(record_tuple, merged_files=merge_paths, executed_gate_ids=gate_ids, repo_root=REPO_ROOT)
        args.release_manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.release_manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
    failed = [record.evidence_id for record in record_tuple if not record.ok]
    if failed:
        for gate_id in failed:
            print(f'quality evidence gate failed: {gate_id}')
        raise SystemExit(1)
    print(f'quality evidence written: {args.out}')
