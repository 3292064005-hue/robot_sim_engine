from __future__ import annotations

from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.request_builders import build_execution_graph_descriptor
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.solver_config import IKConfig


def test_benchmark_service_runs_default_cases(planar_spec):
    service = BenchmarkService(RunIKUseCase(DefaultSolverRegistry()))
    report = service.run(planar_spec, IKConfig(position_only=True, retry_count=1))
    assert report['num_cases'] >= 5
    assert 0.0 <= report['success_rate'] <= 1.0
    names = {case['name'] for case in report['cases']}
    assert 'unreachable_far' in names



def test_benchmark_service_threads_execution_graph_into_cases_and_report(planar_spec):
    service = BenchmarkService(RunIKUseCase(DefaultSolverRegistry()))
    execution_graph = build_execution_graph_descriptor(
        planar_spec,
        {
            'descriptor_id': 'bench_scope',
            'target_links': [planar_spec.runtime_link_names[-1]],
        },
    )
    report = service.run(planar_spec, IKConfig(position_only=True, retry_count=1), execution_graph=execution_graph)
    assert report['metadata']['execution_graph']['descriptor_id'] == 'bench_scope'
    assert report['metadata']['execution_scope']['descriptor_id'] == 'bench_scope'
    assert report['metadata']['execution_graph'] == report['metadata']['execution_scope']
    assert report['cases']
    for case in report['cases']:
        assert case['metadata']['execution_graph']['descriptor_id'] == 'bench_scope'
        assert case['metadata']['execution_scope']['descriptor_id'] == 'bench_scope'
        assert case['metadata']['execution_graph'] == case['metadata']['execution_scope']
