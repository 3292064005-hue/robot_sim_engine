from __future__ import annotations

from pathlib import Path

from robot_sim.infra.quality_contracts import verify_quality_contract_files, _build_runtime_truth_quality_service


def test_ci_workflow_contains_quality_gates(project_root: Path):
    ci_text = (project_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for marker in [
        "runtime_contracts:",
        "governance_evidence:",
        "unit_regression:",
        "full_validation:",
        "gui_smoke:",
        "python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs",
        "python scripts/verify_compatibility_retirement.py",
        "python scripts/verify_quality_contracts.py",
        "python scripts/verify_quick_quality.py",
        "python scripts/verify_module_governance.py --execute-gates",
        "python scripts/verify_benchmark_matrix.py --execute-gates --execute",
        "python scripts/verify_perf_budget_config.py",
        "pytest tests/unit tests/regression -q",
        "pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q",
        "python scripts/verify_partition_coverage.py --coverage-json coverage.json",
        "python scripts/verify_gui_smoke.py",
        "pytest tests/gui -q",
    ]:
        assert marker in ci_text


def test_precommit_and_gitignore_cover_local_quality_workflow(project_root: Path):
    precommit_text = (project_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    gitignore_text = (project_root / ".gitignore").read_text(encoding="utf-8")
    assert "ruff-check" in precommit_text
    assert "mypy" in precommit_text
    assert "pytest -q" in precommit_text
    assert ".pytest_cache/" in gitignore_text
    assert "__pycache__/" in gitignore_text


def test_checked_in_quality_contract_docs_are_current(project_root: Path):
    assert verify_quality_contract_files(project_root) == []


def test_capability_contract_docs_match_runtime_truth(project_root: Path):
    snapshot = _build_runtime_truth_quality_service(project_root).snapshot()
    capability_doc = (project_root / 'docs' / 'capability_matrix.md').read_text(encoding='utf-8').strip()
    assert capability_doc == snapshot.capability_matrix_markdown.strip()
    assert 'stable_demo_scene_backend_contract' in capability_doc
    assert 'stable_demo_collision_backend_contract' in capability_doc

