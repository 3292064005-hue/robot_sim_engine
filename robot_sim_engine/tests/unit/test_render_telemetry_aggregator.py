from __future__ import annotations

from robot_sim.model.render_telemetry import build_render_operation_span
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.render_telemetry_aggregator import RenderTelemetryAggregator


def test_render_telemetry_aggregator_refreshes_only_touched_backends() -> None:
    state = SessionState()
    aggregator = RenderTelemetryAggregator()
    aggregator.append_operation_span(
        state,
        build_render_operation_span(
            'screenshot',
            'capture_a',
            sequence=1,
            backend='snapshot_renderer',
            duration_ms=10.0,
            sample_count=5,
            source='worker',
        ),
    )
    first = tuple(state.render_backend_performance)
    aggregator.append_sampling_counters(
        state,
        [
            {'capability': 'plots', 'counter_name': 'draw_calls', 'backend': 'pyqtgraph', 'value': 7.0, 'unit': 'calls', 'source': 'worker'},
            {'capability': 'plots', 'counter_name': 'vertices', 'backend': 'pyqtgraph', 'value': 21.0, 'unit': 'vertices', 'source': 'worker'},
        ],
    )
    assert len(first) == 1
    assert len(state.render_backend_performance) == 2
    snapshot = {item.key: item for item in state.render_backend_performance}
    assert snapshot['screenshot:snapshot_renderer'].total_spans == 1
    assert snapshot['plots:pyqtgraph'].live_counters['vertices'] == 21.0


def test_render_telemetry_aggregator_batches_counter_refresh_once() -> None:
    state = SessionState()
    aggregator = RenderTelemetryAggregator()
    aggregator.append_sampling_counters(
        state,
        [
            {'capability': 'screenshot', 'counter_name': 'drawable_samples', 'backend': 'snapshot_renderer', 'value': 11.0, 'unit': 'samples', 'source': 'worker'},
            {'capability': 'screenshot', 'counter_name': 'canvas_pixels', 'backend': 'snapshot_renderer', 'value': 307200.0, 'unit': 'pixels', 'source': 'worker'},
        ],
    )
    perf = state.render_backend_performance[0]
    assert perf.sampling_totals['drawable_samples'] == 11.0
    assert perf.live_counters['canvas_pixels'] == 307200.0


def test_render_telemetry_aggregator_rejects_invalid_counter_payload() -> None:
    state = SessionState()
    aggregator = RenderTelemetryAggregator()
    try:
        aggregator.append_sampling_counters(state, [None])
    except TypeError as exc:
        assert 'RenderSamplingCounter instances or dict payloads' in str(exc)
    else:
        raise AssertionError('TypeError expected for invalid counter payload type')


def test_render_telemetry_aggregator_empty_batch_is_noop() -> None:
    state = SessionState()
    aggregator = RenderTelemetryAggregator()
    aggregator.append_sampling_counters(state, [])
    assert state.render_sampling_counters == ()
    assert state.render_backend_performance == ()
