from __future__ import annotations

from typing import Mapping

from robot_sim.model.render_telemetry_primitives import (
    RenderOperationSpan,
    RenderSamplingCounter,
    RenderTelemetryEvent,
    _ALLOWED_SPAN_STATUSES,
    _SEVERITY_BY_STATUS,
    _RENDER_OPERATION_SPAN_LIMIT,
    _RENDER_PERF_ROLLING_WINDOW_SECONDS,
    _RENDER_SAMPLING_COUNTER_LIMIT,
    _RENDER_TELEMETRY_EVENT_LIMIT,
    _coerce_datetime,
    normalize_render_operation_history,
    normalize_render_sampling_history,
    normalize_render_telemetry_history,
    utc_now,
)
from robot_sim.model.render_telemetry_backend_record import RenderBackendPerformanceTelemetry


def normalize_render_backend_performance(
    payload: tuple[RenderBackendPerformanceTelemetry, ...] | list[object] | Mapping[str, object] | None,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    """Normalize backend performance snapshots into a deterministic immutable tuple."""
    if payload is None:
        items: list[object] = []
    elif isinstance(payload, Mapping):
        items = list(payload.values())
    else:
        items = list(payload)
    normalized = tuple(RenderBackendPerformanceTelemetry.from_mapping(item) for item in items)
    return tuple(sorted(normalized, key=lambda item: item.key))

__all__ = [
    'RenderBackendPerformanceTelemetry',
    'RenderOperationSpan',
    'RenderSamplingCounter',
    'RenderTelemetryEvent',
    '_ALLOWED_SPAN_STATUSES',
    '_SEVERITY_BY_STATUS',
    '_RENDER_OPERATION_SPAN_LIMIT',
    '_RENDER_PERF_ROLLING_WINDOW_SECONDS',
    '_RENDER_SAMPLING_COUNTER_LIMIT',
    '_RENDER_TELEMETRY_EVENT_LIMIT',
    '_coerce_datetime',
    'normalize_render_backend_performance',
    'normalize_render_operation_history',
    'normalize_render_sampling_history',
    'normalize_render_telemetry_history',
    'utc_now',
]
