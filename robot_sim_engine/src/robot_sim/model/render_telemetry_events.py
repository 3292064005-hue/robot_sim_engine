from __future__ import annotations

from datetime import datetime
from typing import Mapping

from robot_sim.model.render_runtime import RenderCapabilityState
from robot_sim.model.render_telemetry_records import (
    _RENDER_OPERATION_SPAN_LIMIT,
    _RENDER_SAMPLING_COUNTER_LIMIT,
    _RENDER_TELEMETRY_EVENT_LIMIT,
    RenderOperationSpan,
    RenderSamplingCounter,
    RenderTelemetryEvent,
    _SEVERITY_BY_STATUS,
    _coerce_datetime,
    normalize_render_operation_history,
    normalize_render_sampling_history,
    normalize_render_telemetry_history,
)

def _classify_event_kind(previous: RenderCapabilityState, current: RenderCapabilityState) -> str:
    if previous.status == current.status:
        if previous.backend != current.backend:
            return 'backend_switched'
        if previous.reason != current.reason or previous.error_code != current.error_code or previous.message != current.message:
            return 'details_updated'
        return 'state_refreshed'
    if current.status == 'available' and previous.status in {'degraded', 'unsupported'}:
        return 'recovered'
    if current.status == 'degraded' and previous.status == 'available':
        return 'degraded'
    if current.status == 'unsupported':
        return 'unsupported'
    if current.status == 'degraded' and previous.status == 'unsupported':
        return 'fallback_restored'
    return 'state_changed'


def build_render_telemetry_event(
    capability: str,
    previous: RenderCapabilityState,
    current: RenderCapabilityState,
    *,
    sequence: int,
    source: str,
    metadata: Mapping[str, object] | None = None,
) -> RenderTelemetryEvent:
    """Create a structured transition event for a render capability update."""
    merged_metadata = dict(previous.metadata)
    merged_metadata.update(current.metadata)
    merged_metadata.update(dict(metadata or {}))
    return RenderTelemetryEvent(
        sequence=int(sequence),
        capability=str(capability or current.capability),
        event_kind=_classify_event_kind(previous, current),
        severity=_SEVERITY_BY_STATUS.get(current.status, 'warning'),
        status=current.status,
        previous_status=previous.status,
        backend=current.backend,
        reason=current.reason,
        error_code=current.error_code,
        message=current.message,
        source=str(source or ''),
        metadata=merged_metadata,
    )


def build_render_operation_span(
    capability: str,
    operation: str,
    *,
    sequence: int,
    backend: str = '',
    status: str = 'succeeded',
    duration_ms: float = 0.0,
    sample_count: int = 0,
    source: str = '',
    error_code: str = '',
    message: str = '',
    metadata: Mapping[str, object] | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> RenderOperationSpan:
    """Build a structured render-operation span.

    Boundary behavior:
        ``finished_at`` earlier than ``started_at`` is normalized during dataclass validation.
    """
    return RenderOperationSpan(
        sequence=int(sequence),
        capability=str(capability or ''),
        operation=str(operation or 'render_operation'),
        backend=str(backend or ''),
        status=str(status or 'succeeded'),
        duration_ms=float(duration_ms or 0.0),
        sample_count=int(sample_count or 0),
        source=str(source or ''),
        error_code=str(error_code or ''),
        message=str(message or ''),
        metadata=dict(metadata or {}),
        started_at=_coerce_datetime(started_at),
        finished_at=_coerce_datetime(finished_at),
    )


def build_render_sampling_counter(
    capability: str,
    counter_name: str,
    *,
    sequence: int,
    backend: str = '',
    value: float = 0.0,
    delta: float = 0.0,
    unit: str = 'count',
    source: str = '',
    metadata: Mapping[str, object] | None = None,
    emitted_at: datetime | None = None,
) -> RenderSamplingCounter:
    """Build a structured render sampling-counter sample."""
    return RenderSamplingCounter(
        sequence=int(sequence),
        capability=str(capability or ''),
        counter_name=str(counter_name or 'samples'),
        backend=str(backend or ''),
        value=float(value or 0.0),
        delta=float(delta or 0.0),
        unit=str(unit or 'count'),
        source=str(source or ''),
        metadata=dict(metadata or {}),
        emitted_at=_coerce_datetime(emitted_at),
    )


def append_render_telemetry_event(
    history: tuple[RenderTelemetryEvent, ...] | list[object] | None,
    event: RenderTelemetryEvent,
    *,
    limit: int = _RENDER_TELEMETRY_EVENT_LIMIT,
) -> tuple[RenderTelemetryEvent, ...]:
    """Append a transition event to the bounded render telemetry history."""
    normalized = normalize_render_telemetry_history(history)
    bounded_limit = max(1, int(limit or _RENDER_TELEMETRY_EVENT_LIMIT))
    return (*normalized, event)[-bounded_limit:]


def append_render_operation_span(
    history: tuple[RenderOperationSpan, ...] | list[object] | None,
    span: RenderOperationSpan,
    *,
    limit: int = _RENDER_OPERATION_SPAN_LIMIT,
) -> tuple[RenderOperationSpan, ...]:
    """Append an operation span to the bounded render-operation history."""
    normalized = normalize_render_operation_history(history)
    bounded_limit = max(1, int(limit or _RENDER_OPERATION_SPAN_LIMIT))
    return (*normalized, span)[-bounded_limit:]


def append_render_sampling_counter(
    history: tuple[RenderSamplingCounter, ...] | list[object] | None,
    counter: RenderSamplingCounter,
    *,
    limit: int = _RENDER_SAMPLING_COUNTER_LIMIT,
) -> tuple[RenderSamplingCounter, ...]:
    """Append a sampling counter sample to the bounded render sampling history."""
    normalized = normalize_render_sampling_history(history)
    bounded_limit = max(1, int(limit or _RENDER_SAMPLING_COUNTER_LIMIT))
    return (*normalized, counter)[-bounded_limit:]
