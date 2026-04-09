from __future__ import annotations

from datetime import timezone

from robot_sim.model.render_telemetry import (
    RenderBackendPerformanceTelemetry,
    RenderOperationSpan,
    RenderSamplingCounter,
    RenderTelemetryEvent,
)

SEVERITY_LABEL = {
    'nominal': '正常',
    'warning': '警告',
    'critical': '严重',
}
CAPABILITY_LABEL = {
    'scene_3d': '3D 视图',
    'plots': '曲线面板',
    'screenshot': '截图能力',
}
EVENT_LABEL = {
    'degraded': '降级',
    'unsupported': '不可用',
    'recovered': '恢复',
    'backend_switched': '后端切换',
    'details_updated': '细节更新',
    'fallback_restored': '恢复到降级模式',
    'state_changed': '状态变化',
    'state_refreshed': '状态刷新',
}
SPAN_STATUS_LABEL = {
    'succeeded': '成功',
    'failed': '失败',
    'cancelled': '取消',
}


def format_timestamp_from_datetime(value) -> str:
    """Return a compact UTC diagnostics timestamp."""
    return value.astimezone(timezone.utc).strftime('%H:%M:%S')


def format_event_summary(event: RenderTelemetryEvent) -> str:
    """Return the short-form render event summary string."""
    capability = CAPABILITY_LABEL.get(event.capability, event.capability)
    event_label = EVENT_LABEL.get(event.event_kind, event.event_kind)
    severity = SEVERITY_LABEL.get(event.severity, event.severity)
    return f'#{event.sequence} [{severity}] {capability}: {event_label}'


def format_event_detail(event: RenderTelemetryEvent) -> str:
    """Return the long-form render event detail string."""
    parts = [
        f'#{event.sequence}',
        format_timestamp_from_datetime(event.emitted_at),
        CAPABILITY_LABEL.get(event.capability, event.capability),
        EVENT_LABEL.get(event.event_kind, event.event_kind),
        f"{event.previous_status or '-'} -> {event.status}",
    ]
    if event.backend:
        parts.append(f'backend={event.backend}')
    if event.reason:
        parts.append(f'reason={event.reason}')
    if event.error_code:
        parts.append(f'code={event.error_code}')
    if event.source:
        parts.append(f'source={event.source}')
    if event.message:
        parts.append(f'msg={event.message}')
    return ' | '.join(parts)


def format_span_summary(span: RenderOperationSpan) -> str:
    """Return the short-form render span summary string."""
    capability = CAPABILITY_LABEL.get(span.capability, span.capability)
    status = SPAN_STATUS_LABEL.get(span.status, span.status)
    return f'#{span.sequence} [{status}] {capability}: {span.operation} {span.duration_ms:.2f} ms'


def format_span_detail(span: RenderOperationSpan) -> str:
    """Return the long-form render span detail string."""
    parts = [
        f'#{span.sequence}',
        format_timestamp_from_datetime(span.finished_at),
        CAPABILITY_LABEL.get(span.capability, span.capability),
        span.operation,
        f'status={span.status}',
        f'duration_ms={span.duration_ms:.2f}',
    ]
    if span.backend:
        parts.append(f'backend={span.backend}')
    if span.sample_count:
        parts.append(f'samples={span.sample_count}')
    if span.error_code:
        parts.append(f'code={span.error_code}')
    if span.source:
        parts.append(f'source={span.source}')
    if span.message:
        parts.append(f'msg={span.message}')
    return ' | '.join(parts)


def format_counter_summary(counter: RenderSamplingCounter) -> str:
    """Return the short-form render counter summary string."""
    capability = CAPABILITY_LABEL.get(counter.capability, counter.capability)
    return f'#{counter.sequence} {capability}: {counter.counter_name}={counter.value:g} {counter.unit}'


def format_counter_detail(counter: RenderSamplingCounter) -> str:
    """Return the long-form render counter detail string."""
    parts = [
        f'#{counter.sequence}',
        format_timestamp_from_datetime(counter.emitted_at),
        CAPABILITY_LABEL.get(counter.capability, counter.capability),
        f'{counter.counter_name}={counter.value:g}',
        f'unit={counter.unit}',
    ]
    if counter.delta:
        parts.append(f'delta={counter.delta:g}')
    if counter.backend:
        parts.append(f'backend={counter.backend}')
    if counter.source:
        parts.append(f'source={counter.source}')
    return ' | '.join(parts)


def format_backend_summary(item: RenderBackendPerformanceTelemetry) -> str:
    """Return the short-form backend performance summary string."""
    capability = CAPABILITY_LABEL.get(item.capability, item.capability)
    backend = item.backend or 'unknown'
    return f'{capability}/{backend}: {item.total_spans} spans, avg={item.average_duration_ms:.2f} ms, max={item.max_duration_ms:.2f} ms'


def format_backend_detail(item: RenderBackendPerformanceTelemetry) -> str:
    """Return the long-form backend performance detail string."""
    parts = [
        format_backend_summary(item),
        f'status={item.last_status or "-"}',
    ]
    if item.last_operation:
        parts.append(f'last_op={item.last_operation}')
    if item.span_sample_total:
        parts.append(f'span_samples={item.span_sample_total}')
    if item.sampling_totals:
        formatted = ', '.join(
            f'{name}={value:g} {item.sampling_units.get(name, "")}'.strip()
            for name, value in sorted(item.sampling_totals.items())
        )
        parts.append(f'counters=[{formatted}]')
    if item.live_counters:
        live_formatted = ', '.join(
            f'{name}={value:g} {item.live_counter_units.get(name, "")}'.strip()
            for name, value in sorted(item.live_counters.items())
        )
        parts.append(f'live=[{live_formatted}]')
    if item.latency_buckets:
        bucket_formatted = ', '.join(f'{name}:{count}' for name, count in sorted(item.latency_buckets.items()))
        parts.append(f'latency_buckets=[{bucket_formatted}]')
    if item.duration_percentiles_ms:
        percentile_formatted = ', '.join(f'{name}={value:.2f}ms' for name, value in sorted(item.duration_percentiles_ms.items()))
        parts.append(f'percentiles=[{percentile_formatted}]')
    if item.rolling_duration_percentiles_ms:
        rolling_percentiles = ', '.join(f'{name}={value:.2f}ms' for name, value in sorted(item.rolling_duration_percentiles_ms.items()))
        parts.append(f'rolling_percentiles=[{rolling_percentiles}]')
    if item.rolling_span_count or item.rolling_counter_count:
        parts.append(
            'rolling='
            + f'window={item.rolling_window_seconds:.0f}s observed={item.rolling_observed_seconds:.2f}s spans={item.rolling_span_count} counters={item.rolling_counter_count} '
            + f'span_rate={item.rolling_span_rate_per_sec:.2f}/s counter_rate={item.rolling_counter_rate_per_sec:.2f}/s sample_tp={item.rolling_sample_throughput_per_sec:.2f}/s'
        )
    if item.rolling_counter_throughput:
        throughput_formatted = ', '.join(
            f'{name}={value:.2f}/{item.rolling_counter_units.get(name, "")}'.rstrip('/')
            for name, value in sorted(item.rolling_counter_throughput.items())
        )
        parts.append(f'throughput=[{throughput_formatted}]')
    return ' | '.join(parts)
