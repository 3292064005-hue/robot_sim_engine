from __future__ import annotations

from collections.abc import Callable
from typing import Any

from robot_sim.model.render_runtime import RenderCapabilityState, RenderRuntimeState
from robot_sim.model.render_telemetry import (
    _RENDER_OPERATION_SPAN_LIMIT,
    _RENDER_SAMPLING_COUNTER_LIMIT,
    _RENDER_TELEMETRY_EVENT_LIMIT,
    RenderBackendPerformanceTelemetry,
    RenderOperationSpan,
    RenderSamplingCounter,
    RenderTelemetryEvent,
    append_render_telemetry_event,
    build_render_telemetry_event,
    normalize_render_backend_performance,
    normalize_render_operation_history,
    normalize_render_sampling_history,
    normalize_render_telemetry_history,
)
from robot_sim.presentation.render_telemetry_aggregator import RenderTelemetryAggregator

_RENDER_SEGMENT = 'render'


class RenderTelemetryService:
    """Canonical render-telemetry subsystem for the presentation state layer.

    The service owns render-runtime mutation, bounded telemetry/event histories, and
    backend-performance aggregation. ``RenderStateSegmentStore`` remains the stable
    compatibility façade, but render mutations now flush only the render segment instead
    of routing every telemetry update through the global state-store fan-out path.
    """

    def __init__(
        self,
        parent,
        *,
        telemetry_aggregator: RenderTelemetryAggregator | None = None,
    ) -> None:
        self._parent = parent
        self._telemetry_aggregator = telemetry_aggregator or RenderTelemetryAggregator()

    @property
    def state(self):
        return self._parent.state

    def subscribe_render_runtime(
        self,
        callback: Callable[[RenderRuntimeState], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        """Subscribe to render-runtime updates only.

        Args:
            callback: Render-runtime projection callback.
            emit_current: Whether to emit the current runtime state immediately.

        Returns:
            Callable[[], None]: Unsubscribe function.

        Raises:
            None: Invalid runtime payloads are normalized through ``RenderRuntimeState``.
        """
        return self._parent.subscribe_selector(
            lambda state: RenderRuntimeState.from_mapping(state.render_runtime),
            callback,
            emit_current=emit_current,
            segment=_RENDER_SEGMENT,
            snapshot_strategy='identity',
        )

    def subscribe_render_telemetry(
        self,
        callback: Callable[[tuple[RenderTelemetryEvent, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        """Subscribe to bounded render-telemetry event history."""
        return self._parent.subscribe_selector(
            lambda state: normalize_render_telemetry_history(state.render_telemetry),
            callback,
            emit_current=emit_current,
            segment=_RENDER_SEGMENT,
            snapshot_strategy='identity',
        )

    def subscribe_render_operation_spans(
        self,
        callback: Callable[[tuple[RenderOperationSpan, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        """Subscribe to bounded render-operation spans."""
        return self._parent.subscribe_selector(
            lambda state: normalize_render_operation_history(state.render_operation_spans),
            callback,
            emit_current=emit_current,
            segment=_RENDER_SEGMENT,
            snapshot_strategy='identity',
        )

    def subscribe_render_sampling_counters(
        self,
        callback: Callable[[tuple[RenderSamplingCounter, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        """Subscribe to bounded render sampling counters."""
        return self._parent.subscribe_selector(
            lambda state: normalize_render_sampling_history(state.render_sampling_counters),
            callback,
            emit_current=emit_current,
            segment=_RENDER_SEGMENT,
            snapshot_strategy='identity',
        )

    def subscribe_render_backend_performance(
        self,
        callback: Callable[[tuple[RenderBackendPerformanceTelemetry, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        """Subscribe to backend-specific render performance snapshots."""
        return self._parent.subscribe_selector(
            lambda state: normalize_render_backend_performance(state.render_backend_performance),
            callback,
            emit_current=emit_current,
            segment=_RENDER_SEGMENT,
            snapshot_strategy='identity',
        )

    def patch_render_capability(
        self,
        capability: str,
        state: RenderCapabilityState | dict[str, object],
        *,
        source: str = 'state_store.patch_render_capability',
        metadata: dict[str, object] | None = None,
        emit_telemetry: bool = True,
        telemetry_limit: int = _RENDER_TELEMETRY_EVENT_LIMIT,
        notify: bool = True,
    ):
        """Patch one render capability and optionally emit transition telemetry.

        Args:
            capability: Capability identifier (``scene_3d`` / ``plots`` / ``screenshot``).
            state: Target capability state payload.
            source: Telemetry event source label.
            metadata: Optional event metadata.
            emit_telemetry: Whether capability transitions should append telemetry events.
            telemetry_limit: Maximum retained telemetry history length.
            notify: Whether to flush render subscribers immediately.

        Returns:
            SessionState: The mutated shared session state.

        Raises:
            ValueError: If ``capability`` is unsupported or the payload cannot be normalized.
        """
        previous_runtime = RenderRuntimeState.from_mapping(self.state.render_runtime)
        next_runtime = self._replace_runtime_capability(previous_runtime, capability, state)
        self.state.render_runtime = next_runtime
        if emit_telemetry:
            self._record_render_telemetry(
                previous_runtime,
                next_runtime,
                source=source,
                metadata=metadata,
                telemetry_limit=telemetry_limit,
            )
        return self._parent.notify(segment=_RENDER_SEGMENT) if notify else self.state

    def patch_render_runtime(
        self,
        runtime_state: RenderRuntimeState | dict[str, object],
        *,
        source: str = 'state_store.patch_render_runtime',
        metadata: dict[str, object] | None = None,
        emit_telemetry: bool = True,
        telemetry_limit: int = _RENDER_TELEMETRY_EVENT_LIMIT,
        notify: bool = True,
    ):
        """Replace the aggregate render runtime payload and optionally emit transitions."""
        previous_runtime = RenderRuntimeState.from_mapping(self.state.render_runtime)
        next_runtime = RenderRuntimeState.from_mapping(runtime_state)
        self.state.render_runtime = next_runtime
        if emit_telemetry:
            self._record_render_telemetry(
                previous_runtime,
                next_runtime,
                source=source,
                metadata=metadata,
                telemetry_limit=telemetry_limit,
            )
        return self._parent.notify(segment=_RENDER_SEGMENT) if notify else self.state

    def record_render_operation_span(
        self,
        capability: str,
        operation: str,
        *,
        backend: str = '',
        status: str = 'succeeded',
        duration_ms: float = 0.0,
        sample_count: int = 0,
        source: str = 'state_store.record_render_operation_span',
        error_code: str = '',
        message: str = '',
        metadata: dict[str, object] | None = None,
        started_at=None,
        finished_at=None,
        notify: bool = True,
        span_limit: int = _RENDER_OPERATION_SPAN_LIMIT,
    ):
        """Record one render-operation span and refresh touched backend aggregates.

        Boundary behavior:
            ``notify=False`` batches the mutation without discarding telemetry. Callers may
            later flush via ``StateStore.notify_render()`` or ``StateStore.notify()``.
        """
        sequence = int(getattr(self.state, 'render_operation_sequence', 0) or 0) + 1
        from robot_sim.model.render_telemetry import build_render_operation_span
        span = build_render_operation_span(
            capability,
            operation,
            sequence=sequence,
            backend=backend,
            status=status,
            duration_ms=duration_ms,
            sample_count=sample_count,
            source=source,
            error_code=error_code,
            message=message,
            metadata=dict(metadata or {}),
            started_at=started_at,
            finished_at=finished_at,
        )
        self._telemetry_aggregator.append_operation_span(self.state, span, span_limit=span_limit)
        return self._parent.notify(segment=_RENDER_SEGMENT) if notify else self.state

    def record_render_sampling_counter(
        self,
        capability: str,
        counter_name: str,
        *,
        backend: str = '',
        value: float = 0.0,
        delta: float = 0.0,
        unit: str = 'count',
        source: str = 'state_store.record_render_sampling_counter',
        metadata: dict[str, object] | None = None,
        emitted_at=None,
        notify: bool = True,
        counter_limit: int = _RENDER_SAMPLING_COUNTER_LIMIT,
    ):
        """Record one render sampling counter sample."""
        return self.record_render_sampling_counters(
            [
                {
                    'capability': capability,
                    'counter_name': counter_name,
                    'backend': backend,
                    'value': value,
                    'delta': delta,
                    'unit': unit,
                    'source': source,
                    'metadata': dict(metadata or {}),
                    'emitted_at': emitted_at,
                }
            ],
            notify=notify,
            counter_limit=counter_limit,
        )

    def record_render_sampling_counters(
        self,
        counters,
        *,
        notify: bool = True,
        counter_limit: int = _RENDER_SAMPLING_COUNTER_LIMIT,
    ):
        """Record multiple render sampling counters in one aggregation batch."""
        self._telemetry_aggregator.append_sampling_counters(
            self.state,
            counters,
            counter_limit=counter_limit,
        )
        return self._parent.notify(segment=_RENDER_SEGMENT) if notify else self.state

    def _replace_runtime_capability(
        self,
        runtime_state: RenderRuntimeState,
        capability: str,
        state: RenderCapabilityState | dict[str, object],
    ) -> RenderRuntimeState:
        normalized = str(capability or '').strip()
        if normalized not in {'scene_3d', 'plots', 'screenshot'}:
            raise ValueError(f'unsupported render capability: {capability!r}')
        payload = state if isinstance(state, RenderCapabilityState) else RenderCapabilityState.from_mapping(normalized, state)
        kwargs: dict[str, Any] = {
            'scene_3d': runtime_state.scene_3d,
            'plots': runtime_state.plots,
            'screenshot': runtime_state.screenshot,
        }
        kwargs[normalized] = payload
        return RenderRuntimeState(**kwargs)

    def _record_render_telemetry(
        self,
        previous_runtime: RenderRuntimeState,
        next_runtime: RenderRuntimeState,
        *,
        source: str,
        metadata: dict[str, object] | None = None,
        telemetry_limit: int = _RENDER_TELEMETRY_EVENT_LIMIT,
    ) -> tuple[RenderTelemetryEvent, ...]:
        history = normalize_render_telemetry_history(self.state.render_telemetry)
        sequence = int(getattr(self.state, 'render_telemetry_sequence', 0) or 0)
        emitted: list[RenderTelemetryEvent] = []
        for capability in ('scene_3d', 'plots', 'screenshot'):
            previous = getattr(previous_runtime, capability)
            current = getattr(next_runtime, capability)
            if previous == current:
                continue
            sequence += 1
            event = build_render_telemetry_event(
                capability,
                previous,
                current,
                sequence=sequence,
                source=source,
                metadata=dict(metadata or {}),
            )
            history = append_render_telemetry_event(history, event, limit=telemetry_limit)
            emitted.append(event)
        self.state.render_telemetry = history
        self.state.render_telemetry_sequence = sequence
        return tuple(emitted)
