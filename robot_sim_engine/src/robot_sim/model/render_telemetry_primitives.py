from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping

from robot_sim.model.render_runtime import RenderCapabilityState

_RENDER_TELEMETRY_EVENT_LIMIT = 64
_RENDER_OPERATION_SPAN_LIMIT = 64
_RENDER_SAMPLING_COUNTER_LIMIT = 128
_RENDER_PERF_ROLLING_WINDOW_SECONDS = 60.0
_SEVERITY_BY_STATUS = {
    'available': 'nominal',
    'degraded': 'warning',
    'unsupported': 'critical',
}
_ALLOWED_SPAN_STATUSES = frozenset({'succeeded', 'failed', 'cancelled'})


def utc_now() -> datetime:
    """Return the current UTC timestamp used across render telemetry models."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RenderTelemetryEvent:
    """Structured render-state transition event.

    Args:
        sequence: Monotonic event sequence assigned by the state store.
        capability: Stable capability identifier such as ``scene_3d``.
        event_kind: High-level transition classification.
        severity: Severity derived from the resulting capability status.
        status: Resulting capability status.
        previous_status: Prior capability status before the transition.
        backend: Backend identifier active for the resulting state.
        reason: Structured transition reason.
        error_code: Optional stable error code.
        message: User-facing message for diagnostics.
        source: Mutation source such as ``ui_runtime_scan``.
        metadata: Structured auxiliary payload.
        emitted_at: UTC timestamp when the event was emitted.
    """

    sequence: int
    capability: str
    event_kind: str
    severity: str
    status: str
    previous_status: str = ''
    backend: str = ''
    reason: str = ''
    error_code: str = ''
    message: str = ''
    source: str = ''
    metadata: dict[str, object] = field(default_factory=dict)
    emitted_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'sequence', int(self.sequence))
        object.__setattr__(self, 'capability', str(self.capability or ''))
        object.__setattr__(self, 'event_kind', str(self.event_kind or 'state_changed'))
        object.__setattr__(self, 'severity', str(self.severity or 'warning'))
        object.__setattr__(self, 'status', str(self.status or 'available'))
        object.__setattr__(self, 'previous_status', str(self.previous_status or ''))
        object.__setattr__(self, 'backend', str(self.backend or ''))
        object.__setattr__(self, 'reason', str(self.reason or ''))
        object.__setattr__(self, 'error_code', str(self.error_code or ''))
        object.__setattr__(self, 'message', str(self.message or ''))
        object.__setattr__(self, 'source', str(self.source or ''))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        object.__setattr__(self, 'emitted_at', _coerce_datetime(self.emitted_at))

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the telemetry event."""
        return {
            'sequence': int(self.sequence),
            'capability': self.capability,
            'event_kind': self.event_kind,
            'severity': self.severity,
            'status': self.status,
            'previous_status': self.previous_status,
            'backend': self.backend,
            'reason': self.reason,
            'error_code': self.error_code,
            'message': self.message,
            'source': self.source,
            'metadata': dict(self.metadata),
            'emitted_at': self.emitted_at.isoformat(),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | 'RenderTelemetryEvent' | None) -> 'RenderTelemetryEvent':
        """Build an event from a mapping payload or existing instance."""
        if isinstance(payload, cls):
            return payload
        data = dict(payload or {})
        return cls(
            sequence=int(data.get('sequence', 0) or 0),
            capability=str(data.get('capability', '') or ''),
            event_kind=str(data.get('event_kind', 'state_changed') or 'state_changed'),
            severity=str(data.get('severity', 'warning') or 'warning'),
            status=str(data.get('status', 'available') or 'available'),
            previous_status=str(data.get('previous_status', '') or ''),
            backend=str(data.get('backend', '') or ''),
            reason=str(data.get('reason', '') or ''),
            error_code=str(data.get('error_code', '') or ''),
            message=str(data.get('message', '') or ''),
            source=str(data.get('source', '') or ''),
            metadata=dict(data.get('metadata', {}) or {}),
            emitted_at=_coerce_datetime(data.get('emitted_at')),
        )


@dataclass(frozen=True)
class RenderOperationSpan:
    """Structured render-operation span for performance tracing.

    Args:
        sequence: Monotonic span sequence assigned by the state store.
        capability: Stable capability identifier.
        operation: Logical operation name such as ``runtime_probe``.
        backend: Backend identifier used by the operation.
        status: Span terminal state: ``succeeded``, ``failed`` or ``cancelled``.
        duration_ms: Elapsed time in milliseconds.
        sample_count: Optional processed sample count attached to the span.
        source: Span source such as ``scene_capture_worker``.
        error_code: Stable machine-readable error code when available.
        message: Human-readable span summary.
        metadata: Structured auxiliary payload.
        started_at: UTC span start timestamp.
        finished_at: UTC span end timestamp.
    """

    sequence: int
    capability: str
    operation: str
    backend: str = ''
    status: str = 'succeeded'
    duration_ms: float = 0.0
    sample_count: int = 0
    source: str = ''
    error_code: str = ''
    message: str = ''
    metadata: dict[str, object] = field(default_factory=dict)
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'sequence', int(self.sequence))
        object.__setattr__(self, 'capability', str(self.capability or ''))
        object.__setattr__(self, 'operation', str(self.operation or 'render_operation'))
        object.__setattr__(self, 'backend', str(self.backend or ''))
        normalized_status = str(self.status or 'succeeded')
        if normalized_status not in _ALLOWED_SPAN_STATUSES:
            raise ValueError(f'unsupported render operation span status: {self.status!r}')
        object.__setattr__(self, 'status', normalized_status)
        object.__setattr__(self, 'duration_ms', max(0.0, float(self.duration_ms or 0.0)))
        object.__setattr__(self, 'sample_count', max(0, int(self.sample_count or 0)))
        object.__setattr__(self, 'source', str(self.source or ''))
        object.__setattr__(self, 'error_code', str(self.error_code or ''))
        object.__setattr__(self, 'message', str(self.message or ''))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        start = _coerce_datetime(self.started_at)
        finish = _coerce_datetime(self.finished_at)
        if finish < start:
            finish = start
        object.__setattr__(self, 'started_at', start)
        object.__setattr__(self, 'finished_at', finish)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the span."""
        return {
            'sequence': int(self.sequence),
            'capability': self.capability,
            'operation': self.operation,
            'backend': self.backend,
            'status': self.status,
            'duration_ms': float(self.duration_ms),
            'sample_count': int(self.sample_count),
            'source': self.source,
            'error_code': self.error_code,
            'message': self.message,
            'metadata': dict(self.metadata),
            'started_at': self.started_at.isoformat(),
            'finished_at': self.finished_at.isoformat(),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | 'RenderOperationSpan' | None) -> 'RenderOperationSpan':
        """Build a span from a mapping payload or existing span instance."""
        if isinstance(payload, cls):
            return payload
        data = dict(payload or {})
        return cls(
            sequence=int(data.get('sequence', 0) or 0),
            capability=str(data.get('capability', '') or ''),
            operation=str(data.get('operation', 'render_operation') or 'render_operation'),
            backend=str(data.get('backend', '') or ''),
            status=str(data.get('status', 'succeeded') or 'succeeded'),
            duration_ms=float(data.get('duration_ms', 0.0) or 0.0),
            sample_count=int(data.get('sample_count', 0) or 0),
            source=str(data.get('source', '') or ''),
            error_code=str(data.get('error_code', '') or ''),
            message=str(data.get('message', '') or ''),
            metadata=dict(data.get('metadata', {}) or {}),
            started_at=_coerce_datetime(data.get('started_at')),
            finished_at=_coerce_datetime(data.get('finished_at')),
        )


@dataclass(frozen=True)
class RenderSamplingCounter:
    """Structured render sampling counter sample.

    Args:
        sequence: Monotonic counter sequence assigned by the state store.
        capability: Stable capability identifier.
        counter_name: Counter identifier such as ``trajectory_points``.
        backend: Backend identifier associated with the sample.
        value: Sampled counter value.
        delta: Optional incremental delta relative to the previous sample.
        unit: Sample unit such as ``points`` or ``pixels``.
        source: Origin of the sample.
        metadata: Structured auxiliary payload.
        emitted_at: UTC timestamp when the sample was recorded.
    """

    sequence: int
    capability: str
    counter_name: str
    backend: str = ''
    value: float = 0.0
    delta: float = 0.0
    unit: str = 'count'
    source: str = ''
    metadata: dict[str, object] = field(default_factory=dict)
    emitted_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'sequence', int(self.sequence))
        object.__setattr__(self, 'capability', str(self.capability or ''))
        object.__setattr__(self, 'counter_name', str(self.counter_name or 'samples'))
        object.__setattr__(self, 'backend', str(self.backend or ''))
        object.__setattr__(self, 'value', float(self.value or 0.0))
        object.__setattr__(self, 'delta', float(self.delta or 0.0))
        object.__setattr__(self, 'unit', str(self.unit or 'count'))
        object.__setattr__(self, 'source', str(self.source or ''))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        object.__setattr__(self, 'emitted_at', _coerce_datetime(self.emitted_at))

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the sampling counter."""
        return {
            'sequence': int(self.sequence),
            'capability': self.capability,
            'counter_name': self.counter_name,
            'backend': self.backend,
            'value': float(self.value),
            'delta': float(self.delta),
            'unit': self.unit,
            'source': self.source,
            'metadata': dict(self.metadata),
            'emitted_at': self.emitted_at.isoformat(),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | 'RenderSamplingCounter' | None) -> 'RenderSamplingCounter':
        """Build a sampling counter sample from a mapping payload or existing instance."""
        if isinstance(payload, cls):
            return payload
        data = dict(payload or {})
        return cls(
            sequence=int(data.get('sequence', 0) or 0),
            capability=str(data.get('capability', '') or ''),
            counter_name=str(data.get('counter_name', 'samples') or 'samples'),
            backend=str(data.get('backend', '') or ''),
            value=float(data.get('value', 0.0) or 0.0),
            delta=float(data.get('delta', 0.0) or 0.0),
            unit=str(data.get('unit', 'count') or 'count'),
            source=str(data.get('source', '') or ''),
            metadata=dict(data.get('metadata', {}) or {}),
            emitted_at=_coerce_datetime(data.get('emitted_at')),
        )


def _coerce_datetime(value: object) -> datetime:

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value != '':
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            dt = utc_now()
    else:
        dt = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_render_telemetry_history(
    payload: tuple[RenderTelemetryEvent, ...] | list[object] | None,
) -> tuple[RenderTelemetryEvent, ...]:
    """Normalize render-state transition history into immutable structured events."""
    return tuple(RenderTelemetryEvent.from_mapping(item) for item in (payload or ()))


def normalize_render_operation_history(
    payload: tuple[RenderOperationSpan, ...] | list[object] | None,
) -> tuple[RenderOperationSpan, ...]:
    """Normalize render-operation span history into immutable structured spans."""
    return tuple(RenderOperationSpan.from_mapping(item) for item in (payload or ()))


def normalize_render_sampling_history(
    payload: tuple[RenderSamplingCounter, ...] | list[object] | None,
) -> tuple[RenderSamplingCounter, ...]:
    """Normalize render sampling-counter history into immutable structured samples."""
    return tuple(RenderSamplingCounter.from_mapping(item) for item in (payload or ()))


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
