from __future__ import annotations

from pathlib import Path
import tempfile
import numpy as np

from robot_sim.application.services.perf_budget_service import PerfBudgetService
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.kinematics.jacobian_solver import JacobianSolver
from robot_sim.render.screenshot_service import ScreenshotService


def _samples(fn, warmup_runs: int, measured_runs: int) -> list[float]:
    for _ in range(warmup_runs):
        fn()
    samples = []
    for _ in range(measured_runs):
        samples.append(float(fn()))
    return samples


def test_fk_smoke_produces_stable_elapsed_statistics(planar_spec, project_root):
    solver = ForwardKinematicsSolver()
    budget_service = PerfBudgetService.from_repo_root(project_root)
    sampling = budget_service.sampling_plan('fk_planar_smoke', profile='ci')

    def _run() -> float:
        return float(solver.solve(planar_spec, planar_spec.home_q.copy()).metadata.get('elapsed_ms', 0.0) or 0.0)

    # measure manually because FKResult doesn't carry timings
    import time
    def _timed() -> float:
        start = time.perf_counter()
        solver.solve(planar_spec, planar_spec.home_q.copy())
        return (time.perf_counter() - start) * 1000.0

    samples = _samples(_timed, sampling['warmup_runs'], sampling['measured_runs'])
    metrics = {
        'median_elapsed_ms': float(np.median(samples)),
        'p95_elapsed_ms': float(np.percentile(samples, 95)),
        'max_single_elapsed_ms': float(max(samples)),
    }
    result = budget_service.evaluate_metrics('fk_planar_smoke', metrics, profile='ci')
    assert result.passed, result.violations


def test_jacobian_smoke_produces_stable_elapsed_statistics(planar_spec, project_root):
    solver = JacobianSolver()
    budget_service = PerfBudgetService.from_repo_root(project_root)
    sampling = budget_service.sampling_plan('jacobian_planar_smoke', profile='ci')
    import time
    def _timed() -> float:
        start = time.perf_counter()
        solver.geometric(planar_spec, planar_spec.home_q.copy())
        return (time.perf_counter() - start) * 1000.0

    samples = _samples(_timed, sampling['warmup_runs'], sampling['measured_runs'])
    metrics = {
        'median_elapsed_ms': float(np.median(samples)),
        'p95_elapsed_ms': float(np.percentile(samples, 95)),
        'max_single_elapsed_ms': float(max(samples)),
    }
    result = budget_service.evaluate_metrics('jacobian_planar_smoke', metrics, profile='ci')
    assert result.passed, result.violations


def test_snapshot_capture_smoke_produces_stable_elapsed_statistics(project_root):
    service = ScreenshotService()
    budget_service = PerfBudgetService.from_repo_root(project_root)
    sampling = budget_service.sampling_plan('snapshot_capture_smoke', profile='ci')
    snapshot = {
        'title': 'Perf Snapshot',
        'overlay_text': 'perf',
        'robot_points': np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float),
        'trajectory_points': np.array([[0.0, 0.0, 0.0], [0.8, 0.1, 0.0]], dtype=float),
        'target_axes_visible': False,
    }
    import time
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        counter = {'i': 0}
        def _timed() -> float:
            counter['i'] += 1
            target = tmpdir / f'capture_{counter["i"]}.png'
            start = time.perf_counter()
            service.capture_from_snapshot(snapshot, target)
            return (time.perf_counter() - start) * 1000.0
        samples = _samples(_timed, sampling['warmup_runs'], sampling['measured_runs'])
    metrics = {
        'median_elapsed_ms': float(np.median(samples)),
        'p95_elapsed_ms': float(np.percentile(samples, 95)),
        'max_single_elapsed_ms': float(max(samples)),
    }
    result = budget_service.evaluate_metrics('snapshot_capture_smoke', metrics, profile='ci')
    assert result.passed, result.violations
