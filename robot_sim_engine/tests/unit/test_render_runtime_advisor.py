from __future__ import annotations

from robot_sim.application.services.render_runtime_advisor import RenderRuntimeAdvisor
from robot_sim.model.render_runtime import RenderCapabilityState, RenderRuntimeState
from robot_sim.model.render_telemetry import RenderBackendPerformanceTelemetry


def test_render_runtime_advisor_recommends_fallback_for_high_failure_degraded_backend() -> None:
    advisor = RenderRuntimeAdvisor()
    runtime = RenderRuntimeState(
        scene_3d=RenderCapabilityState(capability='scene_3d', status='degraded', backend='pyvistaqt', reason='backend_initialization_failed'),
    )
    perf = (
        RenderBackendPerformanceTelemetry(
            key='scene_3d:pyvistaqt',
            capability='scene_3d',
            backend='pyvistaqt',
            total_spans=10,
            failed_spans=5,
            average_duration_ms=12.0,
            max_duration_ms=18.0,
            last_duration_ms=11.0,
            last_operation='draw',
            last_status='failed',
        ),
    )

    advice = advisor.build_advice(runtime, perf)

    assert advice['severity'] == 'critical'
    assert advice['recommendation_count'] == 1
    assert advice['recommendations'][0]['action'] == 'switch_to_fallback_backend'


def test_render_runtime_advisor_recommends_sampling_reduction_for_high_latency_backend() -> None:
    advisor = RenderRuntimeAdvisor()
    runtime = RenderRuntimeState(
        screenshot=RenderCapabilityState(capability='screenshot', status='available', backend='snapshot_renderer'),
    )
    perf = (
        RenderBackendPerformanceTelemetry(
            key='screenshot:snapshot_renderer',
            capability='screenshot',
            backend='snapshot_renderer',
            total_spans=8,
            succeeded_spans=8,
            average_duration_ms=25.0,
            max_duration_ms=40.0,
            last_duration_ms=30.0,
            last_operation='capture',
            last_status='succeeded',
            duration_percentiles_ms={'p95': 36.0},
            rolling_span_rate_per_sec=10.0,
        ),
    )

    advice = advisor.build_advice(runtime, perf)

    assert advice['severity'] == 'warning'
    assert advice['recommendations'][0]['action'] == 'reduce_sampling_rate'
