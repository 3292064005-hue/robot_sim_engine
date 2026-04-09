from __future__ import annotations

from datetime import datetime
from typing import Mapping

from robot_sim.model.render_telemetry_records import (
    RenderBackendPerformanceTelemetry,
    RenderOperationSpan,
    RenderSamplingCounter,
    _RENDER_PERF_ROLLING_WINDOW_SECONDS,
    normalize_render_backend_performance,
    normalize_render_operation_history,
    normalize_render_sampling_history,
    utc_now,
)


def backend_performance_key(capability: str, backend: str) -> str:
    return f"{str(capability or '')}:{str(backend or 'unknown')}"


def latency_bucket_label(duration_ms: float) -> str:
    value = max(0.0, float(duration_ms or 0.0))
    if value <= 1.0:
        return 'le_1ms'
    if value <= 5.0:
        return 'le_5ms'
    if value <= 16.0:
        return 'le_16ms'
    if value <= 33.0:
        return 'le_33ms'
    if value <= 100.0:
        return 'le_100ms'
    return 'gt_100ms'


def _safe_rate(count: float, seconds: float) -> float:
    return float(count) / float(seconds) if seconds > 0.0 else 0.0


def _compute_percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(max(0.0, float(v)) for v in values)

    def _percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * p
        lower = int(rank)
        upper = min(lower + 1, len(ordered) - 1)
        weight = rank - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        'p50': _percentile(0.50),
        'p90': _percentile(0.90),
        'p95': _percentile(0.95),
        'p99': _percentile(0.99),
    }


def _window_seconds(latest: datetime | None, timestamps: list[datetime], configured_window_seconds: float) -> float:
    if latest is None or not timestamps:
        return 0.0
    earliest = min(timestamps)
    observed = max(0.0, (latest - earliest).total_seconds())
    if observed <= 0.0:
        return min(max(1.0, configured_window_seconds), configured_window_seconds)
    return min(observed, configured_window_seconds)


def _build_backend_performance_entry(
    key: str,
    spans: tuple[RenderOperationSpan, ...],
    counters: tuple[RenderSamplingCounter, ...],
    *,
    rolling_window_seconds: float,
) -> RenderBackendPerformanceTelemetry:
    """Build one backend-performance snapshot from normalized histories."""
    capability, backend = key.split(':', 1)
    backend_spans = tuple(span for span in spans if backend_performance_key(span.capability, span.backend) == key)
    backend_counters = tuple(counter for counter in counters if backend_performance_key(counter.capability, counter.backend) == key)
    total_spans = len(backend_spans)
    succeeded_spans = sum(1 for span in backend_spans if span.status == 'succeeded')
    failed_spans = sum(1 for span in backend_spans if span.status == 'failed')
    cancelled_spans = sum(1 for span in backend_spans if span.status == 'cancelled')
    durations = [float(span.duration_ms) for span in backend_spans]
    total_duration_ms = sum(durations)
    latest_span = max(backend_spans, key=lambda span: span.finished_at, default=None)
    latest_counter = max(backend_counters, key=lambda counter: counter.emitted_at, default=None)
    latest_timestamp = max(
        [item for item in [latest_span.finished_at if latest_span else None, latest_counter.emitted_at if latest_counter else None] if item is not None],
        default=None,
    )

    sampling_totals: dict[str, float] = {}
    sampling_maxima: dict[str, float] = {}
    sampling_units: dict[str, str] = {}
    live_counters: dict[str, float] = {}
    live_counter_units: dict[str, str] = {}
    for counter in backend_counters:
        sampling_totals[counter.counter_name] = sampling_totals.get(counter.counter_name, 0.0) + float(counter.value)
        sampling_maxima[counter.counter_name] = max(sampling_maxima.get(counter.counter_name, float(counter.value)), float(counter.value))
        sampling_units[counter.counter_name] = counter.unit
        live_counters[counter.counter_name] = float(counter.value)
        live_counter_units[counter.counter_name] = counter.unit

    latency_buckets: dict[str, int] = {}
    for span in backend_spans:
        label = latency_bucket_label(span.duration_ms)
        latency_buckets[label] = int(latency_buckets.get(label, 0)) + 1
    percentiles = _compute_percentiles(durations)

    rolling_boundary = None if latest_timestamp is None else latest_timestamp.timestamp() - rolling_window_seconds
    rolling_spans = tuple(span for span in backend_spans if rolling_boundary is None or span.finished_at.timestamp() >= rolling_boundary)
    rolling_counters = tuple(counter for counter in backend_counters if rolling_boundary is None or counter.emitted_at.timestamp() >= rolling_boundary)
    observed_seconds = _window_seconds(
        latest_timestamp,
        [item.finished_at for item in rolling_spans] + [item.emitted_at for item in rolling_counters],
        rolling_window_seconds,
    )
    rolling_counter_totals: dict[str, float] = {}
    rolling_counter_units: dict[str, str] = {}
    for counter in rolling_counters:
        increment = abs(float(counter.delta)) if float(counter.delta) != 0.0 else float(counter.value)
        rolling_counter_totals[counter.counter_name] = rolling_counter_totals.get(counter.counter_name, 0.0) + increment
        rolling_counter_units[counter.counter_name] = counter.unit
    rolling_counter_throughput = {
        name: _safe_rate(total, observed_seconds) for name, total in rolling_counter_totals.items()
    }
    rolling_percentiles = _compute_percentiles([float(span.duration_ms) for span in rolling_spans])
    rolling_span_samples = sum(int(span.sample_count) for span in rolling_spans)
    return RenderBackendPerformanceTelemetry(
        key=key,
        capability=capability,
        backend=backend,
        total_spans=total_spans,
        succeeded_spans=succeeded_spans,
        failed_spans=failed_spans,
        cancelled_spans=cancelled_spans,
        total_duration_ms=total_duration_ms,
        average_duration_ms=(total_duration_ms / total_spans) if total_spans > 0 else 0.0,
        max_duration_ms=max(durations) if durations else 0.0,
        last_duration_ms=float(latest_span.duration_ms) if latest_span is not None else 0.0,
        last_operation=latest_span.operation if latest_span is not None else '',
        last_source=(latest_span.source if latest_span is not None else (latest_counter.source if latest_counter is not None else '')),
        last_status=latest_span.status if latest_span is not None else '',
        last_error_code=latest_span.error_code if latest_span is not None else '',
        span_sample_total=sum(int(span.sample_count) for span in backend_spans),
        sampling_totals=sampling_totals,
        sampling_maxima=sampling_maxima,
        sampling_units=sampling_units,
        latency_buckets=latency_buckets,
        duration_percentiles_ms=percentiles,
        rolling_duration_percentiles_ms=rolling_percentiles,
        rolling_window_seconds=rolling_window_seconds,
        rolling_observed_seconds=observed_seconds,
        rolling_span_count=len(rolling_spans),
        rolling_counter_count=len(rolling_counters),
        rolling_span_rate_per_sec=_safe_rate(len(rolling_spans), observed_seconds),
        rolling_counter_rate_per_sec=_safe_rate(len(rolling_counters), observed_seconds),
        rolling_sample_throughput_per_sec=_safe_rate(rolling_span_samples, observed_seconds),
        rolling_counter_throughput=rolling_counter_throughput,
        rolling_counter_units=rolling_counter_units,
        live_counters=live_counters,
        live_counter_units=live_counter_units,
        last_updated=latest_timestamp or utc_now(),
    )


def refresh_backend_performance_keys(
    history: tuple[RenderBackendPerformanceTelemetry, ...] | list[object] | Mapping[str, object] | None,
    operation_history: tuple[RenderOperationSpan, ...] | list[object] | None,
    counter_history: tuple[RenderSamplingCounter, ...] | list[object] | None,
    *,
    keys: set[str] | tuple[str, ...] | list[str],
    rolling_window_seconds: float = _RENDER_PERF_ROLLING_WINDOW_SECONDS,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    """Refresh only selected backend-performance entries from bounded histories."""
    spans = normalize_render_operation_history(operation_history)
    counters = normalize_render_sampling_history(counter_history)
    window_size = max(1.0, float(rolling_window_seconds or _RENDER_PERF_ROLLING_WINDOW_SECONDS))
    touched = {str(key) for key in keys if str(key)}
    table = {item.key: item for item in normalize_render_backend_performance(history)}
    present_keys = {
        backend_performance_key(span.capability, span.backend) for span in spans
    } | {
        backend_performance_key(counter.capability, counter.backend) for counter in counters
    }
    for key in touched:
        if key not in present_keys:
            table.pop(key, None)
            continue
        table[key] = _build_backend_performance_entry(key, spans, counters, rolling_window_seconds=window_size)
    return normalize_render_backend_performance(table)


def rebuild_backend_performance(
    operation_history: tuple[RenderOperationSpan, ...] | list[object] | None,
    counter_history: tuple[RenderSamplingCounter, ...] | list[object] | None,
    *,
    rolling_window_seconds: float = _RENDER_PERF_ROLLING_WINDOW_SECONDS,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    """Rebuild backend-specific performance telemetry from bounded span and counter histories."""
    spans = normalize_render_operation_history(operation_history)
    counters = normalize_render_sampling_history(counter_history)
    window_size = max(1.0, float(rolling_window_seconds or _RENDER_PERF_ROLLING_WINDOW_SECONDS))
    keys = {
        backend_performance_key(span.capability, span.backend) for span in spans
    } | {
        backend_performance_key(counter.capability, counter.backend) for counter in counters
    }
    entries = {
        key: _build_backend_performance_entry(key, spans, counters, rolling_window_seconds=window_size)
        for key in sorted(keys)
    }
    return normalize_render_backend_performance(entries)


def merge_backend_performance_from_span(
    history: tuple[RenderBackendPerformanceTelemetry, ...] | list[object] | Mapping[str, object] | None,
    span: RenderOperationSpan,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    """Compatibility wrapper that preserves the API while recomputing aggregates from a single span."""
    key = backend_performance_key(span.capability, span.backend)
    current = {item.key: item for item in normalize_render_backend_performance(history)}.get(
        key,
        RenderBackendPerformanceTelemetry(key=key, capability=span.capability, backend=span.backend),
    )
    total_spans = current.total_spans + 1
    total_duration = current.total_duration_ms + float(span.duration_ms)
    updated = RenderBackendPerformanceTelemetry(
        key=key,
        capability=span.capability,
        backend=span.backend,
        total_spans=total_spans,
        succeeded_spans=current.succeeded_spans + (1 if span.status == 'succeeded' else 0),
        failed_spans=current.failed_spans + (1 if span.status == 'failed' else 0),
        cancelled_spans=current.cancelled_spans + (1 if span.status == 'cancelled' else 0),
        total_duration_ms=total_duration,
        average_duration_ms=(total_duration / total_spans) if total_spans > 0 else 0.0,
        max_duration_ms=max(current.max_duration_ms, float(span.duration_ms)),
        last_duration_ms=float(span.duration_ms),
        last_operation=span.operation,
        last_source=span.source,
        last_status=span.status,
        last_error_code=span.error_code,
        span_sample_total=current.span_sample_total + int(span.sample_count),
        sampling_totals=dict(current.sampling_totals),
        sampling_maxima=dict(current.sampling_maxima),
        sampling_units=dict(current.sampling_units),
        latency_buckets={
            **dict(current.latency_buckets),
            latency_bucket_label(span.duration_ms): int(dict(current.latency_buckets).get(latency_bucket_label(span.duration_ms), 0)) + 1,
        },
        duration_percentiles_ms=dict(current.duration_percentiles_ms),
        rolling_duration_percentiles_ms=dict(current.rolling_duration_percentiles_ms),
        rolling_window_seconds=current.rolling_window_seconds,
        rolling_observed_seconds=current.rolling_observed_seconds,
        rolling_span_count=current.rolling_span_count + 1,
        rolling_counter_count=current.rolling_counter_count,
        rolling_span_rate_per_sec=current.rolling_span_rate_per_sec,
        rolling_counter_rate_per_sec=current.rolling_counter_rate_per_sec,
        rolling_sample_throughput_per_sec=current.rolling_sample_throughput_per_sec,
        rolling_counter_throughput=dict(current.rolling_counter_throughput),
        rolling_counter_units=dict(current.rolling_counter_units),
        live_counters=dict(current.live_counters),
        live_counter_units=dict(current.live_counter_units),
        last_updated=span.finished_at,
    )
    table = {item.key: item for item in normalize_render_backend_performance(history)}
    table[key] = updated
    return normalize_render_backend_performance(table)


def merge_backend_performance_from_counter(
    history: tuple[RenderBackendPerformanceTelemetry, ...] | list[object] | Mapping[str, object] | None,
    counter: RenderSamplingCounter,
) -> tuple[RenderBackendPerformanceTelemetry, ...]:
    """Compatibility wrapper that preserves the API while applying an incremental counter sample."""
    key = backend_performance_key(counter.capability, counter.backend)
    current = {item.key: item for item in normalize_render_backend_performance(history)}.get(
        key,
        RenderBackendPerformanceTelemetry(key=key, capability=counter.capability, backend=counter.backend),
    )
    totals = dict(current.sampling_totals)
    totals[counter.counter_name] = totals.get(counter.counter_name, 0.0) + float(counter.value)
    maxima = dict(current.sampling_maxima)
    maxima[counter.counter_name] = max(maxima.get(counter.counter_name, float(counter.value)), float(counter.value))
    units = dict(current.sampling_units)
    units[counter.counter_name] = counter.unit
    live_counters = dict(current.live_counters)
    live_counters[counter.counter_name] = float(counter.value)
    live_counter_units = dict(current.live_counter_units)
    live_counter_units[counter.counter_name] = counter.unit
    rolling_counter_throughput = dict(current.rolling_counter_throughput)
    increment = abs(float(counter.delta)) if float(counter.delta) != 0.0 else float(counter.value)
    rolling_counter_throughput[counter.counter_name] = rolling_counter_throughput.get(counter.counter_name, 0.0) + increment
    rolling_counter_units = dict(current.rolling_counter_units)
    rolling_counter_units[counter.counter_name] = counter.unit
    updated = RenderBackendPerformanceTelemetry(
        key=key,
        capability=counter.capability,
        backend=counter.backend,
        total_spans=current.total_spans,
        succeeded_spans=current.succeeded_spans,
        failed_spans=current.failed_spans,
        cancelled_spans=current.cancelled_spans,
        total_duration_ms=current.total_duration_ms,
        average_duration_ms=current.average_duration_ms,
        max_duration_ms=current.max_duration_ms,
        last_duration_ms=current.last_duration_ms,
        last_operation=current.last_operation,
        last_source=counter.source or current.last_source,
        last_status=current.last_status,
        last_error_code=current.last_error_code,
        span_sample_total=current.span_sample_total,
        sampling_totals=totals,
        sampling_maxima=maxima,
        sampling_units=units,
        latency_buckets=dict(current.latency_buckets),
        duration_percentiles_ms=dict(current.duration_percentiles_ms),
        rolling_duration_percentiles_ms=dict(current.rolling_duration_percentiles_ms),
        rolling_window_seconds=current.rolling_window_seconds,
        rolling_observed_seconds=current.rolling_observed_seconds,
        rolling_span_count=current.rolling_span_count,
        rolling_counter_count=current.rolling_counter_count + 1,
        rolling_span_rate_per_sec=current.rolling_span_rate_per_sec,
        rolling_counter_rate_per_sec=current.rolling_counter_rate_per_sec,
        rolling_sample_throughput_per_sec=current.rolling_sample_throughput_per_sec,
        rolling_counter_throughput=rolling_counter_throughput,
        rolling_counter_units=rolling_counter_units,
        live_counters=live_counters,
        live_counter_units=live_counter_units,
        last_updated=counter.emitted_at,
    )
    table = {item.key: item for item in normalize_render_backend_performance(history)}
    table[key] = updated
    return normalize_render_backend_performance(table)
