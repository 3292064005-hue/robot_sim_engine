from __future__ import annotations

from typing import Callable

from robot_sim.model.render_runtime import RenderCapabilityState, RenderRuntimeState
from robot_sim.model.render_telemetry import (
    _RENDER_OPERATION_SPAN_LIMIT,
    _RENDER_SAMPLING_COUNTER_LIMIT,
    _RENDER_TELEMETRY_EVENT_LIMIT,
    RenderBackendPerformanceTelemetry,
    RenderOperationSpan,
    RenderSamplingCounter,
    RenderTelemetryEvent,
)


_SCENE_UNSET = object()


class StateStoreApiMixin:
    """Compatibility API surface split out from ``StateStore`` to keep the core store small."""

    def subscribe_render_runtime(
        self,
        callback: Callable[[RenderRuntimeState], None],
        *,
        emit_current: bool = False,
    ):
        return self.render_store.subscribe_render_runtime(callback, emit_current=emit_current)

    def subscribe_render_telemetry(
        self,
        callback: Callable[[tuple[RenderTelemetryEvent, ...]], None],
        *,
        emit_current: bool = False,
    ):
        return self.render_store.subscribe_render_telemetry(callback, emit_current=emit_current)

    def subscribe_render_operation_spans(
        self,
        callback: Callable[[tuple[RenderOperationSpan, ...]], None],
        *,
        emit_current: bool = False,
    ):
        return self.render_store.subscribe_render_operation_spans(callback, emit_current=emit_current)

    def subscribe_render_sampling_counters(
        self,
        callback: Callable[[tuple[RenderSamplingCounter, ...]], None],
        *,
        emit_current: bool = False,
    ):
        return self.render_store.subscribe_render_sampling_counters(callback, emit_current=emit_current)

    def subscribe_render_backend_performance(
        self,
        callback: Callable[[tuple[RenderBackendPerformanceTelemetry, ...]], None],
        *,
        emit_current: bool = False,
    ):
        return self.render_store.subscribe_render_backend_performance(callback, emit_current=emit_current)

    def patch_task(self, snapshot):
        return self.task_store.patch_task(snapshot)

    def patch_error(self, error_presentation):
        return self.task_store.patch_error(error_presentation)

    def patch_warning(self, code: str, message: str):
        return self.task_store.patch_warning(code, message)

    def patch_scene(self, scene_summary: dict[str, object], *, planning_scene: object = _SCENE_UNSET, scene_revision: int | None = None):
        return self.session_store.patch_scene(scene_summary, planning_scene=planning_scene, scene_revision=scene_revision)

    def patch_capabilities(self, capability_matrix):
        return self.session_store.patch_capabilities(capability_matrix)

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
        return self.render_store.record_render_operation_span(
            capability,
            operation,
            backend=backend,
            status=status,
            duration_ms=duration_ms,
            sample_count=sample_count,
            source=source,
            error_code=error_code,
            message=message,
            metadata=metadata,
            started_at=started_at,
            finished_at=finished_at,
            notify=notify,
            span_limit=span_limit,
        )

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
        return self.render_store.record_render_sampling_counter(
            capability,
            counter_name,
            backend=backend,
            value=value,
            delta=delta,
            unit=unit,
            source=source,
            metadata=metadata,
            emitted_at=emitted_at,
            notify=notify,
            counter_limit=counter_limit,
        )

    def record_render_sampling_counters(self, counters, *, notify: bool = True, counter_limit: int = _RENDER_SAMPLING_COUNTER_LIMIT):
        return self.render_store.record_render_sampling_counters(counters, notify=notify, counter_limit=counter_limit)

    def patch_render_capability(
        self,
        capability: str,
        state: RenderCapabilityState | dict[str, object],
        *,
        source: str = 'state_store.patch_render_capability',
        metadata: dict[str, object] | None = None,
        emit_telemetry: bool = True,
        telemetry_limit: int = _RENDER_TELEMETRY_EVENT_LIMIT,
    ):
        return self.render_store.patch_render_capability(
            capability,
            state,
            source=source,
            metadata=metadata,
            emit_telemetry=emit_telemetry,
            telemetry_limit=telemetry_limit,
        )

    def patch_render_runtime(
        self,
        runtime_state: RenderRuntimeState | dict[str, object],
        *,
        source: str = 'state_store.patch_render_runtime',
        metadata: dict[str, object] | None = None,
        emit_telemetry: bool = True,
        telemetry_limit: int = _RENDER_TELEMETRY_EVENT_LIMIT,
    ):
        return self.render_store.patch_render_runtime(
            runtime_state,
            source=source,
            metadata=metadata,
            emit_telemetry=emit_telemetry,
            telemetry_limit=telemetry_limit,
        )
