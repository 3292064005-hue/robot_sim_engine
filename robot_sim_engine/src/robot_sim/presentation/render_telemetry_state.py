from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from robot_sim.model.render_telemetry import (
    RenderBackendPerformanceTelemetry,
    RenderOperationSpan,
    RenderSamplingCounter,
    RenderTelemetryEvent,
    normalize_render_backend_performance,
    normalize_render_operation_history,
    normalize_render_sampling_history,
    normalize_render_telemetry_history,
)
from robot_sim.presentation.render_telemetry_formatters import (
    format_backend_detail,
    format_backend_summary,
    format_counter_detail,
    format_counter_summary,
    format_event_detail,
    format_event_summary,
    format_span_detail,
    format_span_summary,
    format_timestamp_from_datetime,
)
from robot_sim.presentation.render_telemetry_projection_helpers import (
    build_backend_summary_strings,
    build_timeline_entries,
)


@dataclass(frozen=True)
class RenderTelemetryEntryView:
    """Typed diagnostics projection for a single render-state transition event."""

    sequence: int
    capability: str
    severity: str
    summary_text: str
    detail_text: str
    timestamp_text: str
    source: str


@dataclass(frozen=True)
class RenderOperationSpanView:
    """Typed diagnostics projection for a single render operation span."""

    sequence: int
    capability: str
    status: str
    summary_text: str
    detail_text: str
    timestamp_text: str
    operation: str
    backend: str


@dataclass(frozen=True)
class RenderSamplingCounterView:
    """Typed diagnostics projection for a single render sampling counter sample."""

    sequence: int
    capability: str
    summary_text: str
    detail_text: str
    timestamp_text: str
    counter_name: str
    backend: str


@dataclass(frozen=True)
class RenderBackendPerformanceView:
    """Typed diagnostics projection for a backend-specific render performance snapshot."""

    key: str
    capability: str
    backend: str
    summary_text: str
    detail_text: str


@dataclass(frozen=True)
class RenderTimelineEntryView:
    """Typed diagnostics projection for a unified render diagnostics timeline entry."""

    sequence: int
    category: str
    severity: str
    summary_text: str
    detail_text: str
    timestamp_text: str


@dataclass(frozen=True)
class RenderTelemetryLogSection:
    """Structured diagnostics log section consumed by the diagnostics panel."""

    section_id: str
    title: str
    body_text: str
    entry_count: int


@dataclass(frozen=True)
class RenderTelemetryPanelState:
    """Typed diagnostics-panel state for render telemetry streams and aggregates."""

    event_count: int
    latest_summary: str
    latest_detail: str
    latest_severity: str
    recent_entries: tuple[RenderTelemetryEntryView, ...]
    span_count: int
    latest_span_summary: str
    latest_span_detail: str
    recent_spans: tuple[RenderOperationSpanView, ...]
    counter_count: int
    latest_counter_summary: str
    latest_counter_detail: str
    recent_counters: tuple[RenderSamplingCounterView, ...]
    backend_count: int
    backend_summary: str
    backend_latency_summary: str
    backend_percentile_summary: str
    backend_rolling_summary: str
    backend_live_counter_summary: str
    backend_entries: tuple[RenderBackendPerformanceView, ...]
    timeline_summary: str
    timeline_entries: tuple[RenderTimelineEntryView, ...]

    @property
    def metric_payload(self) -> dict[str, str]:
        """Return the compact diagnostics key/value projection consumed by the widget shell."""
        return {
            'render_event_count': str(self.event_count),
            'render_latest_event': self.latest_summary,
            'render_latest_severity': self.latest_severity,
            'render_span_count': str(self.span_count),
            'render_latest_span': self.latest_span_summary,
            'render_counter_count': str(self.counter_count),
            'render_latest_counter': self.latest_counter_summary,
            'render_backend_perf': self.backend_summary,
            'render_latency_buckets': self.backend_latency_summary,
            'render_percentiles': self.backend_percentile_summary,
            'render_rolling_window': self.backend_rolling_summary,
            'render_live_counters': self.backend_live_counter_summary,
            'render_timeline_summary': self.timeline_summary,
        }

    @property
    def recent_log_text(self) -> str:
        return '\n'.join(entry.detail_text for entry in self.recent_entries)

    @property
    def log_sections(self) -> tuple[RenderTelemetryLogSection, ...]:
        """Return structured diagnostics sections for the widget surface."""
        return (
            RenderTelemetryLogSection('events', 'Render Telemetry', self.recent_log_text, len(self.recent_entries)),
            RenderTelemetryLogSection('spans', 'Render Operation Spans', self.recent_span_log_text, len(self.recent_spans)),
            RenderTelemetryLogSection('counters', 'Render Sampling Counters', self.recent_counter_log_text, len(self.recent_counters)),
            RenderTelemetryLogSection('backend_performance', 'Backend Performance Telemetry', self.backend_performance_log_text, len(self.backend_entries)),
            RenderTelemetryLogSection('timeline', 'Diagnostics Timeline', self.timeline_log_text, len(self.timeline_entries)),
        )

    @property
    def events_text(self) -> str:
        """Compatibility alias for the telemetry event log text."""
        return self.recent_log_text

    @property
    def recent_span_log_text(self) -> str:
        return '\n'.join(entry.detail_text for entry in self.recent_spans)

    @property
    def spans_text(self) -> str:
        """Compatibility alias for the render-operation span log text."""
        return self.recent_span_log_text

    @property
    def recent_counter_log_text(self) -> str:
        return '\n'.join(entry.detail_text for entry in self.recent_counters)

    @property
    def counters_text(self) -> str:
        """Compatibility alias for the sampling-counter log text."""
        return self.recent_counter_log_text

    @property
    def backend_performance_log_text(self) -> str:
        return '\n'.join(entry.detail_text for entry in self.backend_entries)

    @property
    def backend_perf_text(self) -> str:
        """Compatibility alias for backend-performance log text."""
        return self.backend_performance_log_text

    @property
    def timeline_log_text(self) -> str:
        return '\n'.join(entry.detail_text for entry in self.timeline_entries)

    @property
    def timeline_text(self) -> str:
        """Compatibility alias for diagnostics timeline log text."""
        return self.timeline_log_text






def build_render_telemetry_panel_state(
    events: Iterable[RenderTelemetryEvent] | tuple[RenderTelemetryEvent, ...] | list[object],
    *,
    operation_spans: Iterable[RenderOperationSpan] | tuple[RenderOperationSpan, ...] | list[object] = (),
    sampling_counters: Iterable[RenderSamplingCounter] | tuple[RenderSamplingCounter, ...] | list[object] = (),
    backend_performance: Iterable[RenderBackendPerformanceTelemetry] | tuple[RenderBackendPerformanceTelemetry, ...] | list[object] = (),
    recent_limit: int = 8,
) -> RenderTelemetryPanelState:
    """Project render telemetry streams into diagnostics-panel state.

    Args:
        events: Render runtime transition events.
        operation_spans: Bounded render operation spans.
        sampling_counters: Bounded render sampling counters.
        backend_performance: Backend-specific aggregate performance telemetry.
        recent_limit: Maximum number of recent items shown per stream.

    Returns:
        RenderTelemetryPanelState: Typed diagnostics view model.
    """
    normalized_events = normalize_render_telemetry_history(tuple(events))
    normalized_spans = normalize_render_operation_history(tuple(operation_spans))
    normalized_counters = normalize_render_sampling_history(tuple(sampling_counters))
    normalized_backend_perf = normalize_render_backend_performance(tuple(backend_performance))
    bounded_limit = max(1, int(recent_limit or 8))

    recent_events = normalized_events[-bounded_limit:]
    event_entries = tuple(
        RenderTelemetryEntryView(
            sequence=event.sequence,
            capability=event.capability,
            severity=event.severity,
            summary_text=format_event_summary(event),
            detail_text=format_event_detail(event),
            timestamp_text=format_timestamp_from_datetime(event.emitted_at),
            source=event.source,
        )
        for event in reversed(recent_events)
    )

    recent_spans = normalized_spans[-bounded_limit:]
    span_entries = tuple(
        RenderOperationSpanView(
            sequence=span.sequence,
            capability=span.capability,
            status=span.status,
            summary_text=format_span_summary(span),
            detail_text=format_span_detail(span),
            timestamp_text=format_timestamp_from_datetime(span.finished_at),
            operation=span.operation,
            backend=span.backend,
        )
        for span in reversed(recent_spans)
    )

    recent_counters = normalized_counters[-bounded_limit:]
    counter_entries = tuple(
        RenderSamplingCounterView(
            sequence=counter.sequence,
            capability=counter.capability,
            summary_text=format_counter_summary(counter),
            detail_text=format_counter_detail(counter),
            timestamp_text=format_timestamp_from_datetime(counter.emitted_at),
            counter_name=counter.counter_name,
            backend=counter.backend,
        )
        for counter in reversed(recent_counters)
    )

    backend_entries = tuple(
        RenderBackendPerformanceView(
            key=item.key,
            capability=item.capability,
            backend=item.backend,
            summary_text=format_backend_summary(item),
            detail_text=format_backend_detail(item),
        )
        for item in normalized_backend_perf
    )

    latest_event = normalized_events[-1] if normalized_events else None
    latest_span = normalized_spans[-1] if normalized_spans else None
    latest_counter = normalized_counters[-1] if normalized_counters else None
    backend_summary, backend_latency_summary, backend_percentile_summary, backend_rolling_summary, backend_live_counter_summary = build_backend_summary_strings(
        backend_entries,
        normalized_backend_perf,
    )
    timeline_entries = tuple(
        RenderTimelineEntryView(**payload)
        for payload in build_timeline_entries(event_entries, span_entries, counter_entries, recent_limit=bounded_limit)
    )
    timeline_summary = 'Diagnostics timeline：暂无数据' if not timeline_entries else f'Diagnostics timeline：{len(timeline_entries)} 条最近事件（最新：{timeline_entries[0].summary_text}）'

    return RenderTelemetryPanelState(
        event_count=len(normalized_events),
        latest_summary='Render telemetry：暂无事件' if latest_event is None else format_event_summary(latest_event),
        latest_detail='-' if latest_event is None else format_event_detail(latest_event),
        latest_severity='nominal' if latest_event is None else latest_event.severity,
        recent_entries=event_entries,
        span_count=len(normalized_spans),
        latest_span_summary='Render spans：暂无数据' if latest_span is None else format_span_summary(latest_span),
        latest_span_detail='-' if latest_span is None else format_span_detail(latest_span),
        recent_spans=span_entries,
        counter_count=len(normalized_counters),
        latest_counter_summary='Sampling counters：暂无数据' if latest_counter is None else format_counter_summary(latest_counter),
        latest_counter_detail='-' if latest_counter is None else format_counter_detail(latest_counter),
        recent_counters=counter_entries,
        backend_count=len(backend_entries),
        backend_summary=backend_summary,
        backend_latency_summary=backend_latency_summary,
        backend_percentile_summary=backend_percentile_summary,
        backend_rolling_summary=backend_rolling_summary,
        backend_live_counter_summary=backend_live_counter_summary,
        backend_entries=backend_entries,
        timeline_summary=timeline_summary,
        timeline_entries=timeline_entries,
    )
