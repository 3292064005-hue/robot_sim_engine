from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

from robot_sim.model.render_telemetry_primitives import (
    _RENDER_PERF_ROLLING_WINDOW_SECONDS,
    _coerce_datetime,
    utc_now,
)

@dataclass(frozen=True)
class RenderBackendPerformanceTelemetry:
    """Aggregate backend-specific render performance snapshot.

    Args:
        key: Stable ``<capability>:<backend>`` key.
        capability: Capability covered by the backend snapshot.
        backend: Backend identifier.
        total_spans: Number of recorded spans for the backend.
        succeeded_spans: Number of successful spans.
        failed_spans: Number of failed spans.
        cancelled_spans: Number of cancelled spans.
        total_duration_ms: Sum of all recorded durations.
        average_duration_ms: Mean span duration.
        max_duration_ms: Maximum observed span duration.
        last_duration_ms: Most recently recorded span duration.
        last_operation: Most recent operation name.
        last_source: Most recent source.
        last_status: Most recent span status.
        last_error_code: Most recent error code.
        span_sample_total: Sum of ``sample_count`` across spans.
        sampling_totals: Running totals per counter name.
        sampling_maxima: Maximum observed values per counter name.
        sampling_units: Unit lookup per counter name.
        latency_buckets: Histogram bucket counts keyed by latency bucket label.
        duration_percentiles_ms: Aggregate span duration percentiles keyed by percentile label.
        rolling_duration_percentiles_ms: Rolling-window span duration percentiles keyed by percentile label.
        rolling_window_seconds: Configured rolling-window size used for rate/throughput aggregation.
        rolling_observed_seconds: Actual observed duration represented inside the active rolling window.
        rolling_span_count: Number of spans inside the active rolling window.
        rolling_counter_count: Number of counter samples inside the active rolling window.
        rolling_span_rate_per_sec: Backend-specific span rate inside the rolling window.
        rolling_counter_rate_per_sec: Backend-specific counter-sample rate inside the rolling window.
        rolling_sample_throughput_per_sec: Processed span sample throughput inside the rolling window.
        rolling_counter_throughput: Counter-specific throughput keyed by counter name.
        rolling_counter_units: Unit lookup for rolling counter throughput values.
        live_counters: Latest sampled counter values keyed by counter name.
        live_counter_units: Unit lookup for the latest live counters.
        last_updated: UTC timestamp of the most recent update.
    """

    key: str
    capability: str
    backend: str
    total_spans: int = 0
    succeeded_spans: int = 0
    failed_spans: int = 0
    cancelled_spans: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    last_duration_ms: float = 0.0
    last_operation: str = ''
    last_source: str = ''
    last_status: str = ''
    last_error_code: str = ''
    span_sample_total: int = 0
    sampling_totals: dict[str, float] = field(default_factory=dict)
    sampling_maxima: dict[str, float] = field(default_factory=dict)
    sampling_units: dict[str, str] = field(default_factory=dict)
    latency_buckets: dict[str, int] = field(default_factory=dict)
    duration_percentiles_ms: dict[str, float] = field(default_factory=dict)
    rolling_duration_percentiles_ms: dict[str, float] = field(default_factory=dict)
    rolling_window_seconds: float = _RENDER_PERF_ROLLING_WINDOW_SECONDS
    rolling_observed_seconds: float = 0.0
    rolling_span_count: int = 0
    rolling_counter_count: int = 0
    rolling_span_rate_per_sec: float = 0.0
    rolling_counter_rate_per_sec: float = 0.0
    rolling_sample_throughput_per_sec: float = 0.0
    rolling_counter_throughput: dict[str, float] = field(default_factory=dict)
    rolling_counter_units: dict[str, str] = field(default_factory=dict)
    live_counters: dict[str, float] = field(default_factory=dict)
    live_counter_units: dict[str, str] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'key', str(self.key or _backend_performance_key(self.capability, self.backend)))
        object.__setattr__(self, 'capability', str(self.capability or ''))
        object.__setattr__(self, 'backend', str(self.backend or ''))
        object.__setattr__(self, 'total_spans', max(0, int(self.total_spans or 0)))
        object.__setattr__(self, 'succeeded_spans', max(0, int(self.succeeded_spans or 0)))
        object.__setattr__(self, 'failed_spans', max(0, int(self.failed_spans or 0)))
        object.__setattr__(self, 'cancelled_spans', max(0, int(self.cancelled_spans or 0)))
        object.__setattr__(self, 'total_duration_ms', max(0.0, float(self.total_duration_ms or 0.0)))
        object.__setattr__(self, 'average_duration_ms', max(0.0, float(self.average_duration_ms or 0.0)))
        object.__setattr__(self, 'max_duration_ms', max(0.0, float(self.max_duration_ms or 0.0)))
        object.__setattr__(self, 'last_duration_ms', max(0.0, float(self.last_duration_ms or 0.0)))
        object.__setattr__(self, 'last_operation', str(self.last_operation or ''))
        object.__setattr__(self, 'last_source', str(self.last_source or ''))
        object.__setattr__(self, 'last_status', str(self.last_status or ''))
        object.__setattr__(self, 'last_error_code', str(self.last_error_code or ''))
        object.__setattr__(self, 'span_sample_total', max(0, int(self.span_sample_total or 0)))
        object.__setattr__(self, 'sampling_totals', {str(k): float(v) for k, v in dict(self.sampling_totals or {}).items()})
        object.__setattr__(self, 'sampling_maxima', {str(k): float(v) for k, v in dict(self.sampling_maxima or {}).items()})
        object.__setattr__(self, 'sampling_units', {str(k): str(v) for k, v in dict(self.sampling_units or {}).items()})
        object.__setattr__(self, 'latency_buckets', {str(k): max(0, int(v)) for k, v in dict(self.latency_buckets or {}).items()})
        object.__setattr__(self, 'duration_percentiles_ms', {str(k): max(0.0, float(v)) for k, v in dict(self.duration_percentiles_ms or {}).items()})
        object.__setattr__(self, 'rolling_duration_percentiles_ms', {str(k): max(0.0, float(v)) for k, v in dict(self.rolling_duration_percentiles_ms or {}).items()})
        object.__setattr__(self, 'rolling_window_seconds', max(0.0, float(self.rolling_window_seconds or _RENDER_PERF_ROLLING_WINDOW_SECONDS)))
        object.__setattr__(self, 'rolling_observed_seconds', max(0.0, float(self.rolling_observed_seconds or 0.0)))
        object.__setattr__(self, 'rolling_span_count', max(0, int(self.rolling_span_count or 0)))
        object.__setattr__(self, 'rolling_counter_count', max(0, int(self.rolling_counter_count or 0)))
        object.__setattr__(self, 'rolling_span_rate_per_sec', max(0.0, float(self.rolling_span_rate_per_sec or 0.0)))
        object.__setattr__(self, 'rolling_counter_rate_per_sec', max(0.0, float(self.rolling_counter_rate_per_sec or 0.0)))
        object.__setattr__(self, 'rolling_sample_throughput_per_sec', max(0.0, float(self.rolling_sample_throughput_per_sec or 0.0)))
        object.__setattr__(self, 'rolling_counter_throughput', {str(k): max(0.0, float(v)) for k, v in dict(self.rolling_counter_throughput or {}).items()})
        object.__setattr__(self, 'rolling_counter_units', {str(k): str(v) for k, v in dict(self.rolling_counter_units or {}).items()})
        object.__setattr__(self, 'live_counters', {str(k): float(v) for k, v in dict(self.live_counters or {}).items()})
        object.__setattr__(self, 'live_counter_units', {str(k): str(v) for k, v in dict(self.live_counter_units or {}).items()})
        object.__setattr__(self, 'last_updated', _coerce_datetime(self.last_updated))

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of backend performance telemetry."""
        return {
            'key': self.key,
            'capability': self.capability,
            'backend': self.backend,
            'total_spans': int(self.total_spans),
            'succeeded_spans': int(self.succeeded_spans),
            'failed_spans': int(self.failed_spans),
            'cancelled_spans': int(self.cancelled_spans),
            'total_duration_ms': float(self.total_duration_ms),
            'average_duration_ms': float(self.average_duration_ms),
            'max_duration_ms': float(self.max_duration_ms),
            'last_duration_ms': float(self.last_duration_ms),
            'last_operation': self.last_operation,
            'last_source': self.last_source,
            'last_status': self.last_status,
            'last_error_code': self.last_error_code,
            'span_sample_total': int(self.span_sample_total),
            'sampling_totals': dict(self.sampling_totals),
            'sampling_maxima': dict(self.sampling_maxima),
            'sampling_units': dict(self.sampling_units),
            'latency_buckets': dict(self.latency_buckets),
            'duration_percentiles_ms': dict(self.duration_percentiles_ms),
            'rolling_duration_percentiles_ms': dict(self.rolling_duration_percentiles_ms),
            'rolling_window_seconds': float(self.rolling_window_seconds),
            'rolling_observed_seconds': float(self.rolling_observed_seconds),
            'rolling_span_count': int(self.rolling_span_count),
            'rolling_counter_count': int(self.rolling_counter_count),
            'rolling_span_rate_per_sec': float(self.rolling_span_rate_per_sec),
            'rolling_counter_rate_per_sec': float(self.rolling_counter_rate_per_sec),
            'rolling_sample_throughput_per_sec': float(self.rolling_sample_throughput_per_sec),
            'rolling_counter_throughput': dict(self.rolling_counter_throughput),
            'rolling_counter_units': dict(self.rolling_counter_units),
            'live_counters': dict(self.live_counters),
            'live_counter_units': dict(self.live_counter_units),
            'last_updated': self.last_updated.isoformat(),
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object] | 'RenderBackendPerformanceTelemetry' | None,
    ) -> 'RenderBackendPerformanceTelemetry':
        """Build a backend performance snapshot from a mapping payload or existing instance."""
        if isinstance(payload, cls):
            return payload
        data = dict(payload or {})
        capability = str(data.get('capability', '') or '')
        backend = str(data.get('backend', '') or '')
        return cls(
            key=str(data.get('key', '') or _backend_performance_key(capability, backend)),
            capability=capability,
            backend=backend,
            total_spans=int(data.get('total_spans', 0) or 0),
            succeeded_spans=int(data.get('succeeded_spans', 0) or 0),
            failed_spans=int(data.get('failed_spans', 0) or 0),
            cancelled_spans=int(data.get('cancelled_spans', 0) or 0),
            total_duration_ms=float(data.get('total_duration_ms', 0.0) or 0.0),
            average_duration_ms=float(data.get('average_duration_ms', 0.0) or 0.0),
            max_duration_ms=float(data.get('max_duration_ms', 0.0) or 0.0),
            last_duration_ms=float(data.get('last_duration_ms', 0.0) or 0.0),
            last_operation=str(data.get('last_operation', '') or ''),
            last_source=str(data.get('last_source', '') or ''),
            last_status=str(data.get('last_status', '') or ''),
            last_error_code=str(data.get('last_error_code', '') or ''),
            span_sample_total=int(data.get('span_sample_total', 0) or 0),
            sampling_totals={str(k): float(v) for k, v in dict(data.get('sampling_totals', {}) or {}).items()},
            sampling_maxima={str(k): float(v) for k, v in dict(data.get('sampling_maxima', {}) or {}).items()},
            sampling_units={str(k): str(v) for k, v in dict(data.get('sampling_units', {}) or {}).items()},
            latency_buckets={str(k): int(v) for k, v in dict(data.get('latency_buckets', {}) or {}).items()},
            duration_percentiles_ms={str(k): float(v) for k, v in dict(data.get('duration_percentiles_ms', {}) or {}).items()},
            rolling_duration_percentiles_ms={str(k): float(v) for k, v in dict(data.get('rolling_duration_percentiles_ms', {}) or {}).items()},
            rolling_window_seconds=float(data.get('rolling_window_seconds', _RENDER_PERF_ROLLING_WINDOW_SECONDS) or _RENDER_PERF_ROLLING_WINDOW_SECONDS),
            rolling_observed_seconds=float(data.get('rolling_observed_seconds', 0.0) or 0.0),
            rolling_span_count=int(data.get('rolling_span_count', 0) or 0),
            rolling_counter_count=int(data.get('rolling_counter_count', 0) or 0),
            rolling_span_rate_per_sec=float(data.get('rolling_span_rate_per_sec', 0.0) or 0.0),
            rolling_counter_rate_per_sec=float(data.get('rolling_counter_rate_per_sec', 0.0) or 0.0),
            rolling_sample_throughput_per_sec=float(data.get('rolling_sample_throughput_per_sec', 0.0) or 0.0),
            rolling_counter_throughput={str(k): float(v) for k, v in dict(data.get('rolling_counter_throughput', {}) or {}).items()},
            rolling_counter_units={str(k): str(v) for k, v in dict(data.get('rolling_counter_units', {}) or {}).items()},
            live_counters={str(k): float(v) for k, v in dict(data.get('live_counters', {}) or {}).items()},
            live_counter_units={str(k): str(v) for k, v in dict(data.get('live_counter_units', {}) or {}).items()},
            last_updated=_coerce_datetime(data.get('last_updated')),
        )


