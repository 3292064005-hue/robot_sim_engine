from __future__ import annotations

from pathlib import Path

import pytest

from robot_sim.application.services.benchmark_matrix_service import BenchmarkMatrixService


def test_benchmark_matrix_service_loads_checked_in_matrix(project_root: Path) -> None:
    matrix = BenchmarkMatrixService(project_root / 'configs' / 'benchmark_matrix.yaml').load()
    assert matrix.matrix_id == 'v1'
    assert 'urdf_model' in matrix.importer_variants
    assert any(pair.capture_mode == 'live_capture_capability_probe' for pair in matrix.required_pairs)
    assert matrix.pytest_targets
    assert all(target.startswith('tests/') for target in matrix.pytest_targets)


def test_benchmark_matrix_service_rejects_unknown_pair_reference(tmp_path: Path) -> None:
    path = tmp_path / 'benchmark_matrix.yaml'
    path.write_text(
        'benchmark_matrix:\n'
        '  matrix_id: v1\n'
        '  runtime_surfaces: [headless_runtime]\n'
        '  importer_variants: [yaml_like]\n'
        '  scene_variants: [clean_scene]\n'
        '  solver_suites: [ik_planar_smoke]\n'
        '  capture_modes: [snapshot_capture]\n'
        '  required_quality_gates: [quick_quality]\n'
        '  required_pairs:\n'
        '    - runtime_surface: headless_runtime\n'
        '      importer_variant: urdf_model\n'
        '      scene_variant: clean_scene\n'
        '      solver_suite: ik_planar_smoke\n'
        '      capture_mode: snapshot_capture\n'
        '      execution_targets:\n'
        '        - kind: pytest\n'
        '          selector: tests/performance/test_ik_smoke.py::test_ik_smoke_produces_stable_elapsed_statistics\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='unknown importer_variant'):
        BenchmarkMatrixService(path).load()


def test_benchmark_matrix_service_requires_execution_targets(tmp_path: Path) -> None:
    path = tmp_path / 'benchmark_matrix.yaml'
    path.write_text(
        'benchmark_matrix:\n'
        '  matrix_id: v1\n'
        '  runtime_surfaces: [headless_runtime]\n'
        '  importer_variants: [yaml_like]\n'
        '  scene_variants: [clean_scene]\n'
        '  solver_suites: [ik_planar_smoke]\n'
        '  capture_modes: [snapshot_capture]\n'
        '  required_quality_gates: [quick_quality]\n'
        '  required_pairs:\n'
        '    - runtime_surface: headless_runtime\n'
        '      importer_variant: yaml_like\n'
        '      scene_variant: clean_scene\n'
        '      solver_suite: ik_planar_smoke\n'
        '      capture_mode: snapshot_capture\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='execution_targets'):
        BenchmarkMatrixService(path).load()


def test_benchmark_matrix_service_rejects_selector_contract_mismatch(tmp_path: Path) -> None:
    path = tmp_path / 'benchmark_matrix.yaml'
    path.write_text(
        'benchmark_matrix:\n'
        '  matrix_id: v1\n'
        '  runtime_surfaces: [headless_runtime]\n'
        '  importer_variants: [yaml_like]\n'
        '  scene_variants: [clean_scene]\n'
        '  solver_suites: [ik_planar_smoke]\n'
        '  capture_modes: [snapshot_capture]\n'
        '  required_quality_gates: [quick_quality]\n'
        '  required_pairs:\n'
        '    - runtime_surface: headless_runtime\n'
        '      importer_variant: yaml_like\n'
        '      scene_variant: clean_scene\n'
        '      solver_suite: ik_planar_smoke\n'
        '      capture_mode: snapshot_capture\n'
        '      execution_targets:\n'
        '        - kind: pytest\n'
        '          selector: tests/integration/test_import_robot_into_scene_pipeline.py::test_imported_robot_bundle_can_seed_planning_scene\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='benchmark target contract mismatch'):
        BenchmarkMatrixService(path).load()
