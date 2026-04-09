from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from robot_sim.presentation.render_telemetry_formatters import CAPABILITY_LABEL


def build_timeline_entries(
    event_entries: tuple[object, ...],
    span_entries: tuple[object, ...],
    counter_entries: tuple[object, ...],
    *,
    recent_limit: int,
) -> tuple[dict[str, Any], ...]:
    """Build the unified diagnostics timeline from typed stream projections.

    Args:
        event_entries: Render event projections with sequence/severity/summary/detail/timestamp fields.
        span_entries: Render span projections with sequence/status/summary/detail/timestamp fields.
        counter_entries: Render counter projections with sequence/summary/detail/timestamp fields.
        recent_limit: Maximum number of timeline entries to retain.

    Returns:
        tuple[dict[str, Any], ...]: Most recent unified timeline payloads.
    """
    items: list[dict[str, Any]] = []
    for entry in event_entries:
        items.append(
            {
                'sequence': int(getattr(entry, 'sequence')),
                'category': 'event',
                'severity': str(getattr(entry, 'severity')),
                'summary_text': str(getattr(entry, 'summary_text')),
                'detail_text': '[EVENT] ' + str(getattr(entry, 'detail_text')),
                'timestamp_text': str(getattr(entry, 'timestamp_text')),
            }
        )
    for entry in span_entries:
        status = str(getattr(entry, 'status'))
        severity = 'critical' if status == 'failed' else ('warning' if status == 'cancelled' else 'nominal')
        items.append(
            {
                'sequence': int(getattr(entry, 'sequence')),
                'category': 'span',
                'severity': severity,
                'summary_text': str(getattr(entry, 'summary_text')),
                'detail_text': '[SPAN] ' + str(getattr(entry, 'detail_text')),
                'timestamp_text': str(getattr(entry, 'timestamp_text')),
            }
        )
    for entry in counter_entries:
        items.append(
            {
                'sequence': int(getattr(entry, 'sequence')),
                'category': 'counter',
                'severity': 'nominal',
                'summary_text': str(getattr(entry, 'summary_text')),
                'detail_text': '[COUNTER] ' + str(getattr(entry, 'detail_text')),
                'timestamp_text': str(getattr(entry, 'timestamp_text')),
            }
        )
    bounded_limit = max(1, int(recent_limit or 8))
    return tuple(sorted(items, key=lambda item: (str(item['timestamp_text']), int(item['sequence'])), reverse=True)[:bounded_limit])


def build_backend_summary_strings(
    backend_entries: tuple[object, ...],
    normalized_backend_perf: Iterable[object],
) -> tuple[str, str, str, str, str]:
    """Build diagnostics summary strings for backend performance aggregates.

    Args:
        backend_entries: Typed backend entry projections with ``summary_text``.
        normalized_backend_perf: Canonical backend performance telemetry records.

    Returns:
        tuple[str, str, str, str, str]: Summary, latency, percentile, rolling-window, and
        live-counter strings.
    """
    items = tuple(normalized_backend_perf)
    backend_summary = 'Backend 性能：暂无数据' if not backend_entries else '; '.join(str(getattr(entry, 'summary_text')) for entry in backend_entries)
    backend_latency_summary = 'Latency buckets：暂无数据' if not items else '; '.join(
        f"{CAPABILITY_LABEL.get(item.capability, item.capability)}/{item.backend or 'unknown'}: " + ', '.join(f'{name}:{count}' for name, count in sorted(item.latency_buckets.items()))
        for item in items
    )
    backend_percentile_summary = 'Percentiles：暂无数据' if not items else '; '.join(
        f"{CAPABILITY_LABEL.get(item.capability, item.capability)}/{item.backend or 'unknown'}: " + ', '.join(f'{name}={value:.2f}ms' for name, value in sorted(item.duration_percentiles_ms.items()))
        for item in items
    )
    backend_rolling_summary = 'Rolling window：暂无数据' if not items else '; '.join(
        f"{CAPABILITY_LABEL.get(item.capability, item.capability)}/{item.backend or 'unknown'}: window={item.rolling_window_seconds:.0f}s observed={item.rolling_observed_seconds:.2f}s span_rate={item.rolling_span_rate_per_sec:.2f}/s counter_rate={item.rolling_counter_rate_per_sec:.2f}/s sample_tp={item.rolling_sample_throughput_per_sec:.2f}/s"
        for item in items
    )
    backend_live_counter_summary = 'Live counters：暂无数据' if not items else '; '.join(
        f"{CAPABILITY_LABEL.get(item.capability, item.capability)}/{item.backend or 'unknown'}: " + ', '.join(
            f'{name}={value:g} {item.live_counter_units.get(name, "")}'.strip()
            for name, value in sorted(item.live_counters.items())
        )
        for item in items
    )
    return (
        backend_summary,
        backend_latency_summary,
        backend_percentile_summary,
        backend_rolling_summary,
        backend_live_counter_summary,
    )
