from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeVar

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
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.render_telemetry_aggregator import RenderTelemetryAggregator
from robot_sim.presentation.render_telemetry_service import RenderTelemetryService

SelectorValue = TypeVar('SelectorValue')
StateSegment = str
_SCENE_UNSET = object()


class StateStoreProtocol(Protocol):
    """Structural protocol used by segmented stores to mutate the shared session state."""

    @property
    def state(self) -> SessionState: ...

    def notify(self, *, segment: StateSegment | tuple[StateSegment, ...] | None = None, include_global: bool = True) -> SessionState: ...

    def patch(self, *, segment: StateSegment = 'global', **kwargs: Any) -> SessionState: ...

    def subscribe_selector(
        self,
        selector: Callable[[SessionState], SelectorValue],
        callback: Callable[[SelectorValue], None],
        *,
        emit_current: bool = False,
        equality: Callable[[SelectorValue, SelectorValue], bool] | None = None,
        segment: StateSegment = 'global',
        snapshot_strategy: str = 'deepcopy',
        snapshot_factory: Callable[[SelectorValue], object] | None = None,
    ) -> Callable[[], None]: ...


class SessionStateSegmentStore:
    """Session-wide state segment responsible for non-task/non-render projections."""

    def __init__(self, parent: StateStoreProtocol) -> None:
        self._parent = parent

    @property
    def state(self) -> SessionState:
        return self._parent.state

    def patch_scene(
        self,
        scene_summary: dict[str, object],
        *,
        planning_scene: object = _SCENE_UNSET,
        scene_revision: int | None = None,
    ) -> SessionState:
        """Patch planning-scene projection state into the shared session store.

        Args:
            scene_summary: Stable scene summary payload rendered into diagnostics/export.
            planning_scene: Optional canonical planning-scene object. Pass ``None``
                explicitly to clear the current scene authority; omit to leave it unchanged.
            scene_revision: Optional explicit scene revision override.

        Returns:
            SessionState: Updated shared session snapshot.

        Raises:
            None: Pure state mutation wrapper over ``StateStore.patch``.
        """
        kwargs: dict[str, object] = {'scene_summary': dict(scene_summary)}
        if planning_scene is not _SCENE_UNSET:
            kwargs['planning_scene'] = planning_scene
        if scene_revision is not None:
            kwargs['scene_revision'] = int(scene_revision)
        return self._parent.patch(segment='session', **kwargs)

    def patch_capabilities(self, capability_matrix) -> SessionState:
        """Patch capability matrix state from a structured capability object or mapping."""
        payload = capability_matrix.as_dict() if hasattr(capability_matrix, 'as_dict') else dict(capability_matrix)
        return self._parent.patch(segment='session', capability_matrix=payload)


class TaskStateSegmentStore:
    """Task/error/warning segment extracted from the monolithic presentation state store."""

    def __init__(self, parent: StateStoreProtocol) -> None:
        self._parent = parent

    @property
    def state(self) -> SessionState:
        return self._parent.state

    def patch_task(self, snapshot) -> SessionState:
        """Patch the active task snapshot fields."""
        return self._parent.patch(
            segment='task',
            active_task_snapshot=snapshot,
            active_task_id=getattr(snapshot, 'task_id', ''),
            active_task_kind=getattr(snapshot, 'task_kind', ''),
            task_state=getattr(snapshot, 'state', ''),
            task_stop_reason=getattr(snapshot, 'stop_reason', ''),
            task_correlation_id=getattr(snapshot, 'correlation_id', ''),
        )

    def patch_error(self, error_presentation) -> SessionState:
        """Patch the last structured error presentation."""
        return self._parent.patch(
            segment='task',
            last_error=getattr(error_presentation, 'user_message', ''),
            last_error_payload=dict(getattr(error_presentation, 'log_payload', {}) or {}),
            last_error_code=str(getattr(error_presentation, 'error_code', '') or ''),
            last_error_title=str(getattr(error_presentation, 'title', '') or ''),
            last_error_severity=str(getattr(error_presentation, 'severity', '') or ''),
            last_error_hint=str(getattr(error_presentation, 'remediation_hint', '') or ''),
        )

    def patch_warning(self, code: str, message: str) -> SessionState:
        """Patch warning state while preserving prior warning history."""
        codes = tuple(dict.fromkeys((*self.state.active_warning_codes, str(code))))
        warnings = tuple(dict.fromkeys((*self.state.warnings, str(message))))
        return self._parent.patch(segment='task', active_warning_codes=codes, warnings=warnings, last_warning=str(message))


class RenderStateSegmentStore:
    """Compatibility façade over the dedicated render-telemetry subsystem."""

    def __init__(
        self,
        parent: StateStoreProtocol,
        *,
        telemetry_aggregator: RenderTelemetryAggregator | None = None,
        telemetry_service: RenderTelemetryService | None = None,
    ) -> None:
        self._parent = parent
        self._telemetry_service = telemetry_service or RenderTelemetryService(
            parent,
            telemetry_aggregator=telemetry_aggregator,
        )

    @property
    def state(self) -> SessionState:
        return self._parent.state

    @property
    def telemetry_service(self) -> RenderTelemetryService:
        """Return the canonical render telemetry subsystem used by this segment store."""
        return self._telemetry_service

    def subscribe_render_runtime(
        self,
        callback: Callable[[RenderRuntimeState], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        return self._telemetry_service.subscribe_render_runtime(callback, emit_current=emit_current)

    def subscribe_render_telemetry(
        self,
        callback: Callable[[tuple[RenderTelemetryEvent, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        return self._telemetry_service.subscribe_render_telemetry(callback, emit_current=emit_current)

    def subscribe_render_operation_spans(
        self,
        callback: Callable[[tuple[RenderOperationSpan, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        return self._telemetry_service.subscribe_render_operation_spans(callback, emit_current=emit_current)

    def subscribe_render_sampling_counters(
        self,
        callback: Callable[[tuple[RenderSamplingCounter, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        return self._telemetry_service.subscribe_render_sampling_counters(callback, emit_current=emit_current)

    def subscribe_render_backend_performance(
        self,
        callback: Callable[[tuple[RenderBackendPerformanceTelemetry, ...]], None],
        *,
        emit_current: bool = False,
    ) -> Callable[[], None]:
        return self._telemetry_service.subscribe_render_backend_performance(callback, emit_current=emit_current)

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
    ) -> SessionState:
        return self._telemetry_service.record_render_operation_span(
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
    ) -> SessionState:
        return self._telemetry_service.record_render_sampling_counter(
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

    def record_render_sampling_counters(
        self,
        counters,
        *,
        notify: bool = True,
        counter_limit: int = _RENDER_SAMPLING_COUNTER_LIMIT,
    ) -> SessionState:
        return self._telemetry_service.record_render_sampling_counters(
            counters,
            notify=notify,
            counter_limit=counter_limit,
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
    ) -> SessionState:
        return self._telemetry_service.patch_render_capability(
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
    ) -> SessionState:
        return self._telemetry_service.patch_render_runtime(
            runtime_state,
            source=source,
            metadata=metadata,
            emit_telemetry=emit_telemetry,
            telemetry_limit=telemetry_limit,
        )
