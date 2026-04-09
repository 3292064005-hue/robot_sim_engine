from __future__ import annotations

from datetime import datetime
from typing import Iterable

from robot_sim.model.render_telemetry import (
    _RENDER_OPERATION_SPAN_LIMIT,
    _RENDER_PERF_ROLLING_WINDOW_SECONDS,
    _RENDER_SAMPLING_COUNTER_LIMIT,
    RenderOperationSpan,
    RenderSamplingCounter,
    append_render_operation_span,
    append_render_sampling_counter,
    build_render_sampling_counter,
    normalize_render_operation_history,
    normalize_render_sampling_history,
    refresh_backend_performance_keys,
)


class RenderTelemetryAggregator:
    """State-store companion that keeps render telemetry aggregation off the mutation hot path.

    The state store owns session mutation and notification semantics. This helper owns
    bounded render telemetry aggregation, selective backend-performance refresh, and
    batch-friendly history updates so the store no longer recomputes every backend on
    each appended span/counter sample.
    """

    def __init__(self, *, rolling_window_seconds: float = _RENDER_PERF_ROLLING_WINDOW_SECONDS) -> None:
        self._rolling_window_seconds = max(1.0, float(rolling_window_seconds or _RENDER_PERF_ROLLING_WINDOW_SECONDS))

    def append_operation_span(self, state, span: RenderOperationSpan, *, span_limit: int = _RENDER_OPERATION_SPAN_LIMIT) -> None:
        """Append one operation span and refresh only affected backend aggregates.

        Args:
            state: Mutable session state receiving the updated histories.
            span: Structured render-operation span to append.
            span_limit: Maximum retained span count.

        Returns:
            None: Mutates ``state`` in place.

        Raises:
            None: Bounded history eviction is handled internally.
        """
        previous = normalize_render_operation_history(state.render_operation_spans)
        next_history = append_render_operation_span(previous, span, limit=span_limit)
        evicted = self._evicted_item(previous, next_history)
        touched_keys = {self._backend_key(span)}
        if evicted is not None:
            touched_keys.add(self._backend_key(evicted))
        state.render_operation_spans = next_history
        state.render_operation_sequence = int(span.sequence)
        state.render_backend_performance = refresh_backend_performance_keys(
            state.render_backend_performance,
            next_history,
            state.render_sampling_counters,
            keys=touched_keys,
            rolling_window_seconds=self._rolling_window_seconds,
        )

    def append_sampling_counter(self, state, counter: RenderSamplingCounter, *, counter_limit: int = _RENDER_SAMPLING_COUNTER_LIMIT) -> None:
        """Append one sampling counter and refresh only affected backend aggregates."""
        self.append_sampling_counters(state, (counter,), counter_limit=counter_limit)

    def append_sampling_counters(
        self,
        state,
        counters: Iterable[RenderSamplingCounter | dict[str, object]],
        *,
        counter_limit: int = _RENDER_SAMPLING_COUNTER_LIMIT,
    ) -> None:
        """Append sampling counters in one batch and refresh touched backends once.

        Args:
            state: Mutable session state receiving the updated histories.
            counters: Structured counters or mapping payloads.
            counter_limit: Maximum retained counter count.

        Returns:
            None: Mutates ``state`` in place.

        Raises:
            None: Unsupported payload shapes are normalized through the telemetry model builder.
        """
        history = normalize_render_sampling_history(state.render_sampling_counters)
        sequence = int(getattr(state, 'render_sampling_sequence', 0) or 0)
        touched_keys: set[str] = set()
        processed_any = False
        for item in counters:
            processed_any = True
            if isinstance(item, RenderSamplingCounter):
                counter = item
            elif isinstance(item, dict):
                sequence += 1
                data = dict(item)
                try:
                    counter = build_render_sampling_counter(
                        str(data.get('capability', '') or ''),
                        str(data.get('counter_name', 'samples') or 'samples'),
                        sequence=sequence,
                        backend=str(data.get('backend', '') or ''),
                        value=float(data.get('value', 0.0) or 0.0),
                        delta=float(data.get('delta', 0.0) or 0.0),
                        unit=str(data.get('unit', 'count') or 'count'),
                        source=str(data.get('source', 'render_telemetry_aggregator.append_sampling_counters') or 'render_telemetry_aggregator.append_sampling_counters'),
                        metadata=dict(data.get('metadata', {}) or {}),
                        emitted_at=data.get('emitted_at') if isinstance(data.get('emitted_at'), datetime) else None,
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(f'invalid render sampling counter payload: {item!r}') from exc
            else:
                raise TypeError('render sampling counters must be RenderSamplingCounter instances or dict payloads')
            next_history = append_render_sampling_counter(history, counter, limit=counter_limit)
            evicted = self._evicted_item(history, next_history)
            touched_keys.add(self._backend_key(counter))
            if evicted is not None:
                touched_keys.add(self._backend_key(evicted))
            history = next_history
            sequence = int(counter.sequence)
        if not processed_any:
            return
        state.render_sampling_counters = history
        state.render_sampling_sequence = sequence
        state.render_backend_performance = refresh_backend_performance_keys(
            state.render_backend_performance,
            state.render_operation_spans,
            history,
            keys=touched_keys,
            rolling_window_seconds=self._rolling_window_seconds,
        )

    @staticmethod
    def _backend_key(item) -> str:
        capability = str(getattr(item, 'capability', '') or '')
        backend = str(getattr(item, 'backend', '') or 'unknown')
        return f'{capability}:{backend}'

    @staticmethod
    def _evicted_item(previous_history: tuple[object, ...], next_history: tuple[object, ...]) -> object | None:
        """Return the oldest item evicted by a bounded append, if any."""
        if len(next_history) <= len(previous_history):
            return previous_history[0] if previous_history else None
        return None
