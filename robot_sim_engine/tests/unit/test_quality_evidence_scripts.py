from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from robot_sim.infra.quality_evidence import QualityEvidenceRecord, runtime_environment_fingerprint

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _evidence_environment(root: Path) -> dict[str, str]:
    return runtime_environment_fingerprint(root)


def test_collect_quality_evidence_resolves_legacy_merge_gate_ids(tmp_path: Path) -> None:
    mod = _load_script_module('collect_quality_evidence_mod', 'scripts/collect_quality_evidence.py')
    evidence_file = tmp_path / 'evidence.json'
    evidence_file.write_text('[]', encoding='utf-8')
    merge_paths, gate_ids = mod._resolve_gate_and_merge_inputs(
        merge_items=(str(evidence_file), 'runtime_contracts'),
        gate_items=('performance_smoke',),
        positional_items=('compatibility_budget',),
    )
    assert merge_paths == (evidence_file,)
    assert gate_ids == ('performance_smoke', 'compatibility_budget', 'runtime_contracts')


def test_collect_quality_evidence_rejects_unknown_merge_entries() -> None:
    mod = _load_script_module('collect_quality_evidence_mod_invalid', 'scripts/collect_quality_evidence.py')
    try:
        mod._resolve_gate_and_merge_inputs(merge_items=('missing.json',), gate_items=(), positional_items=())
    except FileNotFoundError as exc:
        assert 'expected evidence file or known quality gate id' in str(exc)
    else:
        raise AssertionError('FileNotFoundError expected for unknown merge entry')


def test_release_manifest_marks_environment_and_tooling_failures(tmp_path: Path) -> None:
    mod = _load_script_module('collect_quality_evidence_manifest', 'scripts/collect_quality_evidence.py')
    repo_root = tmp_path / 'repo'
    (repo_root / 'configs').mkdir(parents=True)
    (repo_root / 'configs' / 'release_environment.yaml').write_text(
        """release_environment:
  release:
    platform_system: Linux
    os_id: ubuntu
    os_version_id: '22.04'
    python_major: 3
    python_minor: 10
    requires_build: true
  gui:
    platform_system: Linux
    os_id: ubuntu
    os_version_id: '22.04'
    python_major: 3
    python_minor: 10
    requires_build: true
    pyside_min_version: '6.5'
""",
        encoding='utf-8',
    )
    records = (
        QualityEvidenceRecord('runtime_contracts', 'quality_gate', False, environment=_evidence_environment(repo_root), details={'failure_kind': 'environment_mismatch'}),
        QualityEvidenceRecord('module_governance', 'governance', False, environment=_evidence_environment(repo_root), details={'environment_failures': ['gui_smoke']}),
        QualityEvidenceRecord('benchmark_matrix', 'benchmark_matrix', False, environment=_evidence_environment(repo_root), details={'tooling_failures': ['quick_quality']}),
    )
    manifest = mod.build_release_manifest(
        records,
        merged_files=(Path('artifacts/module_governance_evidence.json'),),
        executed_gate_ids=('runtime_contracts',),
        repo_root=repo_root,
    )
    assert manifest['artifact_ready'] is False
    assert manifest['environment_ready'] is False
    assert manifest['release_ready'] is False
    assert manifest['failed_evidence_ids'] == ['runtime_contracts', 'module_governance', 'benchmark_matrix']
    assert 'gui_smoke' in manifest['environment_failures']
    assert 'runtime_contracts' in manifest['environment_failures']
    assert manifest['tooling_failures'] == ['quick_quality']
    assert manifest['release_environment_failures'] == ['release_environment.release', 'release_environment.gui']
    assert manifest['generated_in_environment']['repo_root'] == str(repo_root.resolve())


def test_benchmark_evidence_skipped_targets_do_not_report_success() -> None:
    mod = _load_script_module('verify_benchmark_matrix_mod', 'scripts/verify_benchmark_matrix.py')
    matrix = SimpleNamespace(matrix_id='bench', required_quality_gates=('gui_smoke',), pytest_targets=('tests/unit',), required_pairs=())
    details = mod.build_benchmark_evidence_details(
        matrix=matrix,
        executed_gate_results={'gui_smoke': {'ok': False, 'failure_kind': 'environment_mismatch'}},
        execute_gates_requested=True,
        execute_requested=True,
        gate_ok=False,
        target_ok=None,
        executed_pytest_command=[],
    )
    assert details['pytest_targets_executed'] is False
    assert details['pytest_targets_status'] == 'skipped_due_to_failed_gates'
    assert details['pytest_targets_ok'] is None
    assert details['pytest_targets_failure_kind'] == 'gates_failed'
    assert details['command_failures'] == []


def test_collect_quality_evidence_marks_module_governance_without_executed_gates_invalid(tmp_path: Path) -> None:
    mod = _load_script_module('collect_quality_evidence_integrity_governance', 'scripts/collect_quality_evidence.py')
    evidence_file = tmp_path / 'module_governance.json'
    payload = [
        {
            'evidence_id': 'module_governance',
            'category': 'governance',
            'ok': True,
            'environment': _evidence_environment(REPO_ROOT),
            'details': {
                'required_gates': ['gui_smoke'],
                'executed_gate_results': {},
                'executed_gates': {},
            },
        }
    ]
    evidence_file.write_text(json.dumps(payload), encoding='utf-8')
    records = mod._load_records(evidence_file, repo_root=REPO_ROOT)
    assert len(records) == 1
    record = records[0]
    assert record.ok is False
    assert 'integrity_errors' in record.details
    assert any('generated with --execute-gates' in item for item in record.details['integrity_errors'])


def test_collect_quality_evidence_marks_inconsistent_benchmark_evidence_invalid(tmp_path: Path) -> None:
    mod = _load_script_module('collect_quality_evidence_integrity_benchmark', 'scripts/collect_quality_evidence.py')
    evidence_file = tmp_path / 'benchmark_matrix.json'
    payload = [
        {
            'evidence_id': 'benchmark_matrix',
            'category': 'benchmark_matrix',
            'ok': True,
            'environment': _evidence_environment(REPO_ROOT),
            'details': {
                'execute_gates_requested': True,
                'execute_requested': True,
                'required_quality_gates': ['gui_smoke'],
                'executed_gate_results': {'gui_smoke': {'ok': False, 'failure_kind': 'environment_mismatch'}},
                'pytest_targets_executed': False,
                'pytest_targets_ok': True,
                'pytest_targets_status': 'passed',
            },
        }
    ]
    evidence_file.write_text(json.dumps(payload), encoding='utf-8')
    records = mod._load_records(evidence_file, repo_root=REPO_ROOT)
    record = records[0]
    assert record.ok is False
    assert any('cannot mark pytest targets ok' in item for item in record.details['integrity_errors'])


def test_release_manifest_rejects_empty_record_sets() -> None:
    mod = _load_script_module('collect_quality_evidence_empty_manifest', 'scripts/collect_quality_evidence.py')
    manifest = mod.build_release_manifest((), merged_files=(), executed_gate_ids=())
    assert manifest['record_count'] == 0
    assert manifest['artifact_ready'] is False
    assert manifest['release_ready'] is False
    assert manifest['failed_evidence_ids'] == ['quality_evidence_collection']
    assert manifest['integrity_failures'] == ['quality_evidence_collection']


def test_release_manifest_tracks_gui_runtime_classification() -> None:
    mod = _load_script_module('collect_quality_evidence_gui_runtime_manifest', 'scripts/collect_quality_evidence.py')
    records = (
        QualityEvidenceRecord(
            'gui_smoke',
            'quality_gate',
            True,
            environment=_evidence_environment(REPO_ROOT),
            details={
                'gui_runtime_kind': 'test_shim',
                'gui_qt_platform': 'offscreen',
                'gui_real_runtime_ok': False,
                'gui_shim_runtime_ok': True,
            },
        ),
    )
    manifest = mod.build_release_manifest(records, merged_files=(), executed_gate_ids=('gui_smoke',), repo_root=REPO_ROOT)
    assert manifest['gui_runtime']['runtime_kind'] == 'test_shim'
    assert manifest['gui_runtime']['qt_platform'] == 'offscreen'
    assert manifest['gui_runtime']['real_runtime_ok'] is False
    assert manifest['gui_runtime']['shim_runtime_ok'] is True
    assert manifest['gui_runtime']['gui_smoke_executed'] is True


def test_collect_quality_evidence_marks_stale_nested_gui_smoke_schema_invalid(tmp_path: Path) -> None:
    mod = _load_script_module('collect_quality_evidence_integrity_nested_gui', 'scripts/collect_quality_evidence.py')
    evidence_file = tmp_path / 'module_governance.json'
    payload = [
        {
            'evidence_id': 'module_governance',
            'category': 'governance',
            'ok': True,
            'environment': _evidence_environment(REPO_ROOT),
            'details': {
                'execute_gates_requested': True,
                'required_gates': ['gui_smoke'],
                'executed_gate_results': {
                    'gui_smoke': {
                        'ok': True,
                        'gate_id': 'gui_smoke',
                        'failure_kind': 'none',
                    }
                },
                'executed_gates': {'gui_smoke': True},
            },
        }
    ]
    evidence_file.write_text(json.dumps(payload), encoding='utf-8')
    records = mod._load_records(evidence_file, repo_root=REPO_ROOT)
    record = records[0]
    assert record.ok is False
    assert any('must preserve gui_smoke field' in item for item in record.details['integrity_errors'])


def test_collect_quality_evidence_rejects_mixed_source_tree_provenance(tmp_path: Path) -> None:
    mod = _load_script_module('collect_quality_evidence_integrity_provenance', 'scripts/collect_quality_evidence.py')
    foreign_root = tmp_path / 'foreign'
    foreign_root.mkdir()
    (foreign_root / 'README.md').write_text('foreign', encoding='utf-8')
    evidence_file = tmp_path / 'module_governance.json'
    payload = [
        {
            'evidence_id': 'module_governance',
            'category': 'governance',
            'ok': True,
            'environment': _evidence_environment(foreign_root),
            'details': {
                'execute_gates_requested': False,
                'required_gates': [],
                'executed_gate_results': {},
                'executed_gates': {},
            },
        }
    ]
    evidence_file.write_text(json.dumps(payload), encoding='utf-8')
    records = mod._load_records(evidence_file, repo_root=REPO_ROOT)
    record = records[0]
    assert record.ok is False
    assert any('provenance drifted' in item for item in record.details['integrity_errors'])




def test_collect_quality_evidence_accepts_relocated_evidence_when_source_tree_matches(tmp_path: Path) -> None:
    import shutil

    mod = _load_script_module('collect_quality_evidence_integrity_relocated', 'scripts/collect_quality_evidence.py')
    clone_root = tmp_path / 'clone'
    shutil.copytree(REPO_ROOT, clone_root)
    evidence_file = tmp_path / 'module_governance.json'
    payload = [
        {
            'evidence_id': 'module_governance',
            'category': 'governance',
            'ok': True,
            'environment': _evidence_environment(REPO_ROOT),
            'details': {
                'execute_gates_requested': False,
                'required_gates': [],
                'executed_gate_results': {},
                'executed_gates': {},
            },
        }
    ]
    evidence_file.write_text(json.dumps(payload), encoding='utf-8')
    records = mod._load_records(evidence_file, repo_root=clone_root)
    assert records[0].ok is True
    assert 'integrity_errors' not in records[0].details


def test_release_manifest_records_relative_merged_evidence_files(tmp_path: Path) -> None:
    mod = _load_script_module('collect_quality_evidence_manifest_relative_paths', 'scripts/collect_quality_evidence.py')
    repo_root = tmp_path / 'repo'
    (repo_root / 'configs').mkdir(parents=True)
    (repo_root / 'artifacts').mkdir(parents=True)
    (repo_root / 'configs' / 'release_environment.yaml').write_text(
        """release_environment:
  release:
    platform_system: Linux
    os_id: ubuntu
    os_version_id: '22.04'
    python_major: 3
    python_minor: 10
    requires_build: true
  gui:
    platform_system: Linux
    os_id: ubuntu
    os_version_id: '22.04'
    python_major: 3
    python_minor: 10
    requires_build: true
    pyside_min_version: '6.5'
""",
        encoding='utf-8',
    )
    records = (QualityEvidenceRecord('runtime_contracts', 'quality_gate', True, environment=_evidence_environment(repo_root), details={}),)
    manifest = mod.build_release_manifest(
        records,
        merged_files=(repo_root / 'artifacts' / 'module_governance_evidence.json',),
        executed_gate_ids=(),
        repo_root=repo_root,
    )
    assert manifest['merged_evidence_files'] == ['artifacts/module_governance_evidence.json']


def test_release_manifest_tracks_nested_gui_runtime_classification() -> None:
    mod = _load_script_module('collect_quality_evidence_nested_gui_manifest', 'scripts/collect_quality_evidence.py')
    records = (
        QualityEvidenceRecord(
            'module_governance',
            'governance',
            True,
            environment=_evidence_environment(REPO_ROOT),
            details={
                'executed_gate_results': {
                    'gui_smoke': {
                        'ok': True,
                        'gui_runtime_kind': 'test_shim',
                        'gui_qt_platform': 'offscreen',
                        'gui_real_runtime_ok': False,
                        'gui_shim_runtime_ok': True,
                    }
                }
            },
        ),
    )
    manifest = mod.build_release_manifest(records, merged_files=(), executed_gate_ids=(), repo_root=REPO_ROOT)
    assert manifest['gui_runtime']['runtime_kind'] == 'test_shim'
    assert manifest['gui_runtime']['qt_platform'] == 'offscreen'
    assert manifest['gui_runtime']['real_runtime_ok'] is False
    assert manifest['gui_runtime']['shim_runtime_ok'] is True
    assert manifest['gui_runtime']['gui_smoke_executed'] is True
    assert manifest['gui_runtime']['gui_smoke_ok'] is True
