from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
<<<<<<< HEAD
from robot_sim.application.services.perf_budget_service import PerfBudgetService
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig


<<<<<<< HEAD
def test_ik_smoke_produces_stable_elapsed_statistics(planar_spec, project_root):
    req = IKRequest(spec=planar_spec, target=Pose(p=np.array([1.3, 0.2, 0.0]), R=np.eye(3)), q0=planar_spec.home_q.copy(), config=IKConfig())
    use_case = RunIKUseCase(DefaultSolverRegistry())
    budget_service = PerfBudgetService.from_repo_root(project_root)
    sampling_plan = budget_service.sampling_plan('ik_planar_smoke', profile='ci')

    for _ in range(sampling_plan['warmup_runs']):
        result = use_case.execute(req)
        assert result.elapsed_ms >= 0.0

    samples = []
    for _ in range(sampling_plan['measured_runs']):
        result = use_case.execute(req)
        assert result.elapsed_ms >= 0.0
        samples.append(float(result.elapsed_ms))

    metrics = {
        'median_elapsed_ms': float(np.median(samples)),
        'p95_elapsed_ms': float(np.percentile(samples, 95)),
        'max_single_elapsed_ms': float(max(samples)),
    }
    eval_result = budget_service.evaluate_metrics('ik_planar_smoke', metrics, profile='ci')
    assert eval_result.passed, eval_result.violations
=======
def test_ik_smoke_produces_elapsed_ms(planar_spec):
    req = IKRequest(spec=planar_spec, target=Pose(p=np.array([1.3, 0.2, 0.0]), R=np.eye(3)), q0=planar_spec.home_q.copy(), config=IKConfig())
    result = RunIKUseCase(DefaultSolverRegistry()).execute(req)
    assert result.elapsed_ms >= 0.0
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
