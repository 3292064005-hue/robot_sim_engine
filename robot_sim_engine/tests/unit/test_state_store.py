from __future__ import annotations

from robot_sim.model.session_state import SessionState
from robot_sim.presentation import state_store as state_store_module
from robot_sim.presentation.state_store import StateStore


def test_state_store_supports_subscription_and_snapshot():
    store = StateStore(SessionState())
    seen = []
    unsubscribe = store.subscribe(lambda state: seen.append((state.is_busy, state.busy_reason)), emit_current=True)
    store.patch(is_busy=True, busy_reason='ik')
    snap = store.snapshot()
    unsubscribe()
    store.patch(is_busy=False, busy_reason='')

    assert seen[0] == (False, '')
    assert seen[1] == (True, 'ik')
    assert snap.is_busy is True
    assert snap.busy_reason == 'ik'



def test_state_store_patches_render_runtime_capabilities():
    store = StateStore(SessionState())
    store.patch_render_capability('scene_3d', {
        'status': 'degraded',
        'backend': 'pyvistaqt',
        'reason': 'backend_initialization_failed',
        'error_code': 'render_initialization_failed',
        'message': '3D backend initialization failed.',
    })
    snap = store.snapshot()
    assert snap.render_runtime.scene_3d.status == 'degraded'
    assert snap.render_runtime.scene_3d.backend == 'pyvistaqt'
    assert 'scene_3d' in snap.render_runtime.degraded_capabilities


def test_state_store_subscribe_selector_emits_only_on_slice_change():
    store = StateStore(SessionState())
    seen = []
    unsubscribe = store.subscribe_selector(lambda state: state.is_busy, lambda value: seen.append(value), emit_current=True)
    store.patch(busy_reason='ik')
    store.patch(is_busy=True)
    store.patch(active_task_kind='ik')
    unsubscribe()
    assert seen == [False, True]


def test_state_store_records_render_telemetry_on_capability_transition():
    store = StateStore(SessionState())
    store.patch_render_capability(
        'scene_3d',
        {
            'status': 'degraded',
            'backend': 'pyvistaqt',
            'reason': 'backend_initialization_failed',
            'error_code': 'render_initialization_failed',
            'message': '3D backend initialization failed.',
        },
        source='ui_runtime_scan',
    )
    snap = store.snapshot()
    assert snap.render_telemetry_sequence == 1
    assert len(snap.render_telemetry) == 1
    event = snap.render_telemetry[0]
    assert event.capability == 'scene_3d'
    assert event.event_kind == 'degraded'
    assert event.source == 'ui_runtime_scan'
    assert event.status == 'degraded'


def test_state_store_render_telemetry_selector_suppresses_duplicate_history_emits():
    store = StateStore(SessionState())
    seen = []
    unsubscribe = store.subscribe_render_telemetry(lambda events: seen.append(tuple(events)), emit_current=True)
    store.patch_render_capability('scene_3d', {'status': 'degraded', 'backend': 'pyvistaqt'}, source='ui_runtime_scan')
    store.patch_render_capability('scene_3d', {'status': 'degraded', 'backend': 'pyvistaqt'}, source='ui_runtime_scan')
    unsubscribe()
    assert len(seen) == 2
    assert seen[-1][-1].capability == 'scene_3d'



def test_state_store_records_render_operation_spans_and_backend_perf():
    store = StateStore(SessionState())
    store.record_render_operation_span(
        'screenshot',
        'capture_from_snapshot',
        backend='snapshot_renderer',
        duration_ms=12.5,
        sample_count=9,
        source='scene_capture_worker',
        message='capture completed',
    )
    snap = store.snapshot()
    assert snap.render_operation_sequence == 1
    assert len(snap.render_operation_spans) == 1
    span = snap.render_operation_spans[0]
    assert span.operation == 'capture_from_snapshot'
    assert span.backend == 'snapshot_renderer'
    assert len(snap.render_backend_performance) == 1
    perf = snap.render_backend_performance[0]
    assert perf.total_spans == 1
    assert perf.average_duration_ms == 12.5
    assert perf.span_sample_total == 9
    assert perf.latency_buckets['le_16ms'] == 1
    assert perf.duration_percentiles_ms['p50'] == 12.5
    assert perf.rolling_span_count == 1
    assert perf.rolling_span_rate_per_sec > 0.0



def test_state_store_records_sampling_counters_and_updates_backend_perf():
    store = StateStore(SessionState())
    store.record_render_sampling_counters(
        [
            {'capability': 'screenshot', 'counter_name': 'drawable_samples', 'backend': 'snapshot_renderer', 'value': 11, 'unit': 'samples', 'source': 'scene_capture_worker'},
            {'capability': 'screenshot', 'counter_name': 'canvas_pixels', 'backend': 'snapshot_renderer', 'value': 307200, 'unit': 'pixels', 'source': 'scene_capture_worker'},
        ]
    )
    snap = store.snapshot()
    assert snap.render_sampling_sequence == 2
    assert len(snap.render_sampling_counters) == 2
    perf = snap.render_backend_performance[0]
    assert perf.sampling_totals['drawable_samples'] == 11.0
    assert perf.sampling_units['canvas_pixels'] == 'pixels'
    assert perf.live_counters['canvas_pixels'] == 307200.0
    assert perf.live_counter_units['drawable_samples'] == 'samples'


def test_state_store_rebuilds_backend_percentiles_and_throughput_from_histories():
    store = StateStore(SessionState())
    store.record_render_operation_span('screenshot', 'capture_a', backend='snapshot_renderer', duration_ms=10.0, sample_count=5, source='worker', notify=False)
    store.record_render_operation_span('screenshot', 'capture_b', backend='snapshot_renderer', duration_ms=30.0, sample_count=7, source='worker', notify=False)
    store.record_render_sampling_counter('screenshot', 'drawable_samples', backend='snapshot_renderer', value=12.0, unit='samples', source='worker', notify=False)
    store.record_render_sampling_counter('screenshot', 'canvas_pixels', backend='snapshot_renderer', value=307200.0, unit='pixels', source='worker', notify=False)
    snap = store.notify()
    perf = snap.render_backend_performance[0]
    assert perf.duration_percentiles_ms['p95'] >= perf.duration_percentiles_ms['p50']
    assert perf.rolling_duration_percentiles_ms['p50'] >= 10.0
    assert perf.rolling_counter_rate_per_sec > 0.0
    assert perf.rolling_counter_throughput['drawable_samples'] > 0.0
    assert perf.rolling_counter_units['drawable_samples'] == 'samples'






def test_state_store_refreshes_render_runtime_advice_from_span_and_sampling_updates():
    store = StateStore(SessionState())
    store.patch_render_runtime({
        'screenshot': {'status': 'available', 'backend': 'snapshot_renderer'}
    }, emit_telemetry=False)

    store.record_render_operation_span(
        'screenshot',
        'capture_frame',
        backend='snapshot_renderer',
        duration_ms=40.0,
        sample_count=12,
        source='scene_capture_worker',
        notify=False,
    )
    store.record_render_sampling_counter(
        'screenshot',
        'drawable_samples',
        backend='snapshot_renderer',
        value=12.0,
        unit='samples',
        source='scene_capture_worker',
        notify=False,
    )

    snap = store.notify()

    assert snap.render_runtime_advice['recommendation_count'] >= 1
    assert snap.render_runtime_advice['recommendations'][0]['capability'] == 'screenshot'
    assert snap.render_runtime_advice['recommendations'][0]['action'] in {'reduce_sampling_rate', 'throttle_render_updates'}

def test_state_store_selector_identity_snapshot_strategy_skips_deepcopy(monkeypatch):
    store = StateStore(SessionState())
    seen = []

    def fail_deepcopy(_value):
        raise AssertionError('deepcopy should not be used for identity snapshot selectors')

    monkeypatch.setattr(state_store_module, 'deepcopy', fail_deepcopy)
    unsubscribe = store.subscribe_selector(
        lambda state: tuple(state.render_telemetry),
        lambda value: seen.append(tuple(value)),
        emit_current=True,
        segment='render',
        snapshot_strategy='identity',
    )
    store.patch_render_capability('scene_3d', {'status': 'degraded', 'backend': 'pyvistaqt'}, source='ui_runtime_scan')
    unsubscribe()

    assert len(seen) == 2
    assert seen[-1][-1].capability == 'scene_3d'
