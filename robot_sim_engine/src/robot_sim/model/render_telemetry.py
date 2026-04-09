from __future__ import annotations

from robot_sim.model.render_telemetry_records import (
    RenderBackendPerformanceTelemetry,
    RenderOperationSpan,
    RenderSamplingCounter,
    RenderTelemetryEvent,
    _RENDER_OPERATION_SPAN_LIMIT,
    _RENDER_PERF_ROLLING_WINDOW_SECONDS,
    _RENDER_SAMPLING_COUNTER_LIMIT,
    _RENDER_TELEMETRY_EVENT_LIMIT,
    normalize_render_backend_performance,
    normalize_render_operation_history,
    normalize_render_sampling_history,
    normalize_render_telemetry_history,
    utc_now,
)
from robot_sim.model.render_telemetry_events import (
    append_render_operation_span,
    append_render_sampling_counter,
    append_render_telemetry_event,
    build_render_operation_span,
    build_render_sampling_counter,
    build_render_telemetry_event,
)
from robot_sim.model.render_telemetry_backend_performance import (
    backend_performance_key as _backend_performance_key_impl,
    latency_bucket_label as _latency_bucket_label_impl,
    merge_backend_performance_from_counter as _merge_backend_performance_from_counter_impl,
    merge_backend_performance_from_span as _merge_backend_performance_from_span_impl,
    rebuild_backend_performance as _rebuild_backend_performance_impl,
    refresh_backend_performance_keys as _refresh_backend_performance_keys_impl,
)


def _backend_performance_key(capability: str, backend: str) -> str:
    return _backend_performance_key_impl(capability, backend)


def _latency_bucket_label(duration_ms: float) -> str:
    return _latency_bucket_label_impl(duration_ms)


def refresh_backend_performance_keys(
    history: tuple[RenderBackendPerformanceTelemetry, ...] | list[object] | dict[str, object] | None,
    operation_history: tuple[RenderOperationSpan, ...] | list[object] | None,
    counter_history: tuple[RenderSamplingCounter, ...] | list[object] | None,
    *,
    keys: set[str] | tuple[str, ...] | list[str],
    rolling_window_seconds: float = _RENDER_PERF_ROLLING_WINDOW_SECONDS,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    return _refresh_backend_performance_keys_impl(
        history,
        operation_history,
        counter_history,
        keys=keys,
        rolling_window_seconds=rolling_window_seconds,
    )


def rebuild_backend_performance(
    operation_history: tuple[RenderOperationSpan, ...] | list[object] | None,
    counter_history: tuple[RenderSamplingCounter, ...] | list[object] | None,
    *,
    rolling_window_seconds: float = _RENDER_PERF_ROLLING_WINDOW_SECONDS,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    return _rebuild_backend_performance_impl(
        operation_history,
        counter_history,
        rolling_window_seconds=rolling_window_seconds,
    )


def merge_backend_performance_from_span(
    history: tuple[RenderBackendPerformanceTelemetry, ...] | list[object] | dict[str, object] | None,
    span: RenderOperationSpan,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    return _merge_backend_performance_from_span_impl(history, span)


def merge_backend_performance_from_counter(
    history: tuple[RenderBackendPerformanceTelemetry, ...] | list[object] | dict[str, object] | None,
    counter: RenderSamplingCounter,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    return _merge_backend_performance_from_counter_impl(history, counter)


__all__ = [
    'RenderBackendPerformanceTelemetry',
    'RenderOperationSpan',
    'RenderSamplingCounter',
    'RenderTelemetryEvent',
    '_RENDER_OPERATION_SPAN_LIMIT',
    '_RENDER_SAMPLING_COUNTER_LIMIT',
    '_RENDER_TELEMETRY_EVENT_LIMIT',
    'append_render_operation_span',
    'append_render_sampling_counter',
    'append_render_telemetry_event',
    'build_render_operation_span',
    'build_render_sampling_counter',
    'build_render_telemetry_event',
    'merge_backend_performance_from_counter',
    'merge_backend_performance_from_span',
    'rebuild_backend_performance',
    'normalize_render_backend_performance',
    'normalize_render_operation_history',
    'normalize_render_sampling_history',
    'normalize_render_telemetry_history',
]
