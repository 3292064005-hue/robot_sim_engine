from __future__ import annotations

from pathlib import Path

import pytest

from robot_sim.application.services.benchmark_matrix_service import BenchmarkMatrixService


def test_benchmark_matrix_service_loads_checked_in_matrix(project_root: Path) -> None:
    matrix = BenchmarkMatrixService(project_root / 'configs' / 'benchmark_matrix.yaml').load()
    assert matrix.matrix_id == 'v1'
    assert 'urdf_model' in matrix.importer_variants
    assert any(pair.capture_mode == 'live_capture_capability_probe' for pair in matrix.required_pairs)
    assert matrix.target_ids
    assert all(target.startswith('runtime_case:') for target in matrix.target_ids)


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
        '        - kind: runtime_case\n'
        '          selector: runtime_case:yaml_like.clean_scene.ik_planar_smoke.snapshot_capture\n',
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
        '        - kind: runtime_case\n'
        '          selector: runtime_case:urdf_model.obstacle_dense.trajectory_plan_smoke.snapshot_capture\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='benchmark target contract mismatch'):
        BenchmarkMatrixService(path).load()



def test_benchmark_matrix_service_rejects_legacy_pytest_targets(tmp_path: Path) -> None:
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
        '          selector: runtime_case:yaml_like.clean_scene.ik_planar_smoke.snapshot_capture\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='unsupported benchmark execution target kind'):
        BenchmarkMatrixService(path).load()
