from __future__ import annotations

import json

from robot_sim.application.services.export_service import ExportService
from robot_sim.domain.enums import AppExecutionState
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.render_telemetry import RenderBackendPerformanceTelemetry, RenderOperationSpan, RenderSamplingCounter, RenderTelemetryEvent
from robot_sim.model.session_state import SessionState


def test_export_service_persists_task_and_state_fields(tmp_path):
    service = ExportService(tmp_path)
    state = SessionState(
        playback=PlaybackState(frame_idx=2, total_frames=10, speed_multiplier=1.5, loop_enabled=True),
        app_state=AppExecutionState.PLAYING,
        active_task_id='task-123',
        active_task_kind='playback',
        scene_revision=5,
        warnings=('warn-a',),
        last_warning='warn-a',
        render_telemetry=(
            RenderTelemetryEvent(
                sequence=1,
                capability='scene_3d',
                event_kind='degraded',
                severity='warning',
                status='degraded',
                previous_status='available',
                backend='pyvistaqt',
                reason='backend_initialization_failed',
                source='ui_runtime_scan',
                message='backend degraded',
            ),
        ),
        render_telemetry_sequence=1,
        render_operation_spans=(
            RenderOperationSpan(
                sequence=1,
                capability='screenshot',
                operation='capture_from_snapshot',
                backend='snapshot_renderer',
                status='succeeded',
                duration_ms=10.5,
                sample_count=9,
                source='scene_capture_worker',
            ),
        ),
        render_operation_sequence=1,
        render_sampling_counters=(
            RenderSamplingCounter(
                sequence=1,
                capability='screenshot',
                counter_name='drawable_samples',
                backend='snapshot_renderer',
                value=9,
                unit='samples',
                source='scene_capture_worker',
            ),
        ),
        render_sampling_sequence=1,
        render_runtime_advice={
            'severity': 'warning',
            'recommendation_count': 1,
            'recommendations': [{'capability': 'scene_3d', 'action': 'switch_to_fallback_backend'}],
        },
        render_backend_performance=(
            RenderBackendPerformanceTelemetry(
                key='screenshot:snapshot_renderer',
                capability='screenshot',
                backend='snapshot_renderer',
                total_spans=1,
                succeeded_spans=1,
                average_duration_ms=10.5,
                max_duration_ms=10.5,
                last_duration_ms=10.5,
                last_operation='capture_from_snapshot',
                last_status='succeeded',
                span_sample_total=9,
                sampling_totals={'drawable_samples': 9.0},
                sampling_maxima={'drawable_samples': 9.0},
                sampling_units={'drawable_samples': 'samples'},
                latency_buckets={'le_16ms': 1},
                duration_percentiles_ms={'p50': 10.5, 'p95': 10.5},
                rolling_duration_percentiles_ms={'p50': 10.5},
                rolling_window_seconds=60.0,
                rolling_observed_seconds=1.0,
                rolling_span_count=1,
                rolling_counter_count=1,
                rolling_span_rate_per_sec=1.0,
                rolling_counter_rate_per_sec=1.0,
                rolling_sample_throughput_per_sec=9.0,
                rolling_counter_throughput={'drawable_samples': 9.0},
                rolling_counter_units={'drawable_samples': 'samples'},
                live_counters={'drawable_samples': 9.0},
                live_counter_units={'drawable_samples': 'samples'},
            ),
        ),
    )
    path = service.save_session('session.json', state)
    payload = json.loads(path.read_text(encoding='utf-8'))

    assert payload['app_state'] == 'playing'
    assert payload['active_task_id'] == 'task-123'
    assert payload['scene_revision'] == 5
    assert payload['warnings'] == ['warn-a']
    assert payload['render_telemetry']['event_count'] == 1
    assert payload['render_telemetry']['events'][0]['capability'] == 'scene_3d'
    assert payload['render_telemetry']['operation_span_count'] == 1
    assert payload['render_telemetry']['operation_spans'][0]['operation'] == 'capture_from_snapshot'
    assert payload['render_telemetry']['sampling_counter_count'] == 1
    assert payload['render_telemetry']['sampling_counters'][0]['counter_name'] == 'drawable_samples'
    assert payload['render_telemetry']['backend_count'] == 1
    assert payload['render_telemetry']['backend_performance'][0]['backend'] == 'snapshot_renderer'
    assert payload['render_telemetry']['backend_performance'][0]['latency_buckets']['le_16ms'] == 1
    assert payload['render_telemetry']['backend_performance'][0]['duration_percentiles_ms']['p50'] == 10.5
    assert payload['render_telemetry']['backend_performance'][0]['rolling_counter_throughput']['drawable_samples'] == 9.0
    assert payload['render_telemetry']['backend_performance'][0]['live_counters']['drawable_samples'] == 9.0
    assert payload['render_runtime_advice']['recommendation_count'] == 1
    assert payload['render_telemetry']['runtime_advice']['recommendations'][0]['action'] == 'switch_to_fallback_backend'
    assert payload['manifest']['producer_version']
