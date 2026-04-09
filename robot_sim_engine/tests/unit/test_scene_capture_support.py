from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from robot_sim.domain.errors import ExportRobotError
from robot_sim.presentation.coordinators.scene_capture_support import build_capture_telemetry, build_failed_capture_error


def test_build_capture_telemetry_returns_serializable_bundle():
    telemetry = build_capture_telemetry(
        path=Path('scene.png'),
        telemetry_source='test',
        sample_count=4,
        counters=({'counter_name': 'drawable_samples', 'value': 4.0},),
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        duration_ms=12.5,
        status='succeeded',
        message='ok',
        correlation_id='cid-1',
    )
    payload = telemetry.as_dict()
    assert payload['operation_span']['source'] == 'test'
    assert payload['sampling_counters'][0]['counter_name'] == 'drawable_samples'


def test_build_failed_capture_error_preserves_export_robot_error_metadata():
    source = ExportRobotError('boom', error_code='capture_failed', metadata={'origin': 'unit'})
    telemetry = {'operation_span': {'status': 'failed'}}
    wrapped = build_failed_capture_error(source, telemetry=telemetry)
    assert wrapped.error_code == 'capture_failed'
    assert wrapped.metadata['origin'] == 'unit'
    assert wrapped.metadata['telemetry'] == telemetry
