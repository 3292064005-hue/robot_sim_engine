from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from robot_sim.model.session_state import SessionState
<<<<<<< HEAD
from robot_sim.presentation.state_segments import (
    RenderStateSegmentStore,
    SessionStateSegmentStore,
    TaskStateSegmentStore,
)
from robot_sim.presentation.state_store_api import StateStoreApiMixin
from robot_sim.presentation.state_store_registry import StateSubscriberRegistry
from robot_sim.presentation.state_store_support import (
    GLOBAL_SEGMENT as _GLOBAL_SEGMENT,
    RENDER_SEGMENT as _RENDER_SEGMENT,
    SelectorSnapshot,
    SelectorValue,
    SEGMENT_NAMES as _SEGMENT_NAMES,
    SNAPSHOT_DEEPCOPY as _SNAPSHOT_DEEPCOPY,
    StateSegment,
    StateSubscriber,
    collect_subscribers,
    normalize_segment_name,
    normalize_segments,
    resolve_selector_snapshot_builder,
)




class StateStore(StateStoreApiMixin):
    """Observable mutable state container for the GUI layer.

    The public ``StateStore`` API remains intact for compatibility. Internally the store
    now keeps segment-local subscriber registries so render telemetry can notify only
    render-aware projections instead of forcing every selector subscriber onto the hot
    path. Global subscribers remain supported and continue to observe all segment updates.
    """

    def __init__(self, state: SessionState | None = None) -> None:
        self._state = state or SessionState()
        self._subscriber_registry = StateSubscriberRegistry(segments=_SEGMENT_NAMES)
        self.session_store = SessionStateSegmentStore(self)
        self.task_store = TaskStateSegmentStore(self)
        self.render_store = RenderStateSegmentStore(self)
=======


StateSubscriber = Callable[[SessionState], None]


class StateStore:
    """Observable mutable state container for the GUI layer."""

    def __init__(self, state: SessionState | None = None) -> None:
        self._state = state or SessionState()
        self._subscribers: list[StateSubscriber] = []
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    @property
    def state(self) -> SessionState:
        """Return the current mutable application session state."""
        return self._state

<<<<<<< HEAD
    @property
    def session(self) -> SessionStateSegmentStore:
        """Return the session-state segment store."""
        return self.session_store

    @property
    def task(self) -> TaskStateSegmentStore:
        """Return the task/error segment store."""
        return self.task_store

    @property
    def render(self) -> RenderStateSegmentStore:
        """Return the render/runtime/telemetry segment store."""
        return self.render_store

    def subscribe(
        self,
        callback: StateSubscriber,
        *,
        emit_current: bool = False,
        segment: StateSegment = _GLOBAL_SEGMENT,
    ) -> Callable[[], None]:
        """Register a state subscriber.

        Args:
            callback: Callback invoked whenever the subscribed state segment changes.
            emit_current: Whether to emit the current state immediately.
            segment: Segment name that should drive this subscriber. ``global`` remains
                the backward-compatible default and is notified for every segment flush.

        Returns:
            Callable that unsubscribes the callback.

        Raises:
            ValueError: If ``segment`` is unsupported.
        """
        normalized_segment = self._subscriber_registry.subscribe(callback, segment=segment)
=======
    def subscribe(self, callback: StateSubscriber, *, emit_current: bool = False) -> Callable[[], None]:
        """Register a state subscriber.

        Args:
            callback: Callback invoked whenever the state changes.
            emit_current: Whether to emit the current state immediately.

        Returns:
            Callable that unsubscribes the callback.
        """
        self._subscribers.append(callback)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        if emit_current:
            callback(self._state)

        def _unsubscribe() -> None:
<<<<<<< HEAD
            self.unsubscribe(callback, segment=normalized_segment)

        return _unsubscribe

    def subscribe_selector(
        self,
        selector: Callable[[SessionState], SelectorValue],
        callback: Callable[[SelectorValue], None],
        *,
        emit_current: bool = False,
        equality: Callable[[SelectorValue, SelectorValue], bool] | None = None,
        segment: StateSegment = _GLOBAL_SEGMENT,
        snapshot_strategy: str = _SNAPSHOT_DEEPCOPY,
        snapshot_factory: SelectorSnapshot | None = None,
    ) -> Callable[[], None]:
        """Register a subscriber for a typed session-state slice.

        Args:
            selector: Function extracting the subscribed state slice.
            callback: Callback invoked when the selected value changes.
            emit_current: Whether to emit the current selected value immediately.
            equality: Optional comparator used to suppress duplicate emissions.
            segment: Segment name driving the selector. Render telemetry selectors should
                register under ``render`` so unrelated state patches do not fan out into
                render diagnostics observers.
            snapshot_strategy: Snapshot policy used to persist the last selected value.
                ``deepcopy`` preserves the historical defensive behavior, ``identity``
                reuses the selected immutable payload directly, and ``custom`` delegates
                to ``snapshot_factory``.
            snapshot_factory: Optional custom snapshot builder used when
                ``snapshot_strategy='custom'``.

        Returns:
            Callable that unsubscribes the selector callback.

        Raises:
            ValueError: If ``segment`` or ``snapshot_strategy`` is unsupported, or when
                ``custom`` is requested without a ``snapshot_factory``.

        Boundary behavior:
            Render telemetry selectors may opt into ``identity`` snapshots because they
            already project frozen dataclasses / tuples. Other selectors keep the
            historical ``deepcopy`` default for compatibility.
        """
        sentinel = object()
        last_value: object = sentinel
        snapshot_builder = resolve_selector_snapshot_builder(
            snapshot_strategy=snapshot_strategy,
            snapshot_factory=snapshot_factory,
        )

        def _subscriber(state: SessionState) -> None:
            nonlocal last_value
            selected = selector(state)
            if last_value is not sentinel:
                matches = equality(selected, last_value) if callable(equality) else (selected == last_value)
                if matches:
                    return
            last_value = snapshot_builder(selected)
            callback(selected)

        return self.subscribe(_subscriber, emit_current=emit_current, segment=segment)

    def unsubscribe(self, callback: StateSubscriber, *, segment: StateSegment | None = None) -> None:
        """Remove a previously registered subscriber.

        Args:
            callback: Subscriber callback to remove.
            segment: Optional specific segment. When omitted the callback is removed from
                every segment registry.

        Returns:
            None: Mutates the internal subscriber registry.

        Raises:
            ValueError: If ``segment`` is unsupported.
        """
        self._subscriber_registry.unsubscribe(callback, segment=segment)

    def notify(
        self,
        *,
        segment: StateSegment | tuple[StateSegment, ...] | None = None,
        include_global: bool = True,
    ) -> SessionState:
        """Notify subscribers and return the current state.

        Args:
            segment: Optional segment or segment tuple to notify. ``None`` flushes every
                registered segment. Segment-scoped notifications always include the global
                subscriber list unless ``include_global`` is set to ``False``.
            include_global: Whether the ``global`` subscriber bucket should be included when
                a specific segment is flushed.

        Returns:
            SessionState: The current mutable state object.

        Raises:
            ValueError: If ``segment`` contains an unsupported segment name.
        """
        return self._subscriber_registry.notify(
            self._state,
            segment=segment,
            include_global=include_global,
        )

    def notify_render(self, *, include_global: bool = True) -> SessionState:
        """Flush only render-local subscribers plus optional global observers.

        Args:
            include_global: Whether to notify global subscribers alongside render-local
                subscribers.

        Returns:
            SessionState: The current mutable state object.

        Raises:
            None: Unsupported segment names are impossible through this helper.
        """
        return self.notify(segment=_RENDER_SEGMENT, include_global=include_global)

    def patch(self, *, segment: StateSegment = _GLOBAL_SEGMENT, **kwargs: Any) -> SessionState:
        """Patch arbitrary session-state fields and notify subscribers.

        Args:
            segment: Segment whose subscribers should be notified after the patch. The
                default keeps the historical global behavior for direct ``patch(...)``
                callers, while segmented stores pass ``session``/``task`` explicitly.
            **kwargs: Session-state fields to update.

        Returns:
            SessionState: The mutated shared state.

        Raises:
            ValueError: If ``segment`` is unsupported.
        """
        for key, value in kwargs.items():
            setattr(self._state, key, value)
        return self.notify(segment=segment)

    def replace(self, state: SessionState) -> SessionState:
        """Replace the entire session state and notify every subscriber bucket."""
=======
            self.unsubscribe(callback)

        return _unsubscribe

    def unsubscribe(self, callback: StateSubscriber) -> None:
        """Remove a previously registered subscriber."""
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass

    def notify(self) -> SessionState:
        """Notify subscribers and return the current state."""
        for subscriber in tuple(self._subscribers):
            subscriber(self._state)
        return self._state

    def patch(self, **kwargs: Any) -> SessionState:
        """Patch arbitrary session state fields and notify subscribers."""
        for key, value in kwargs.items():
            setattr(self._state, key, value)
        return self.notify()

    def patch_task(self, snapshot) -> SessionState:
        """Patch the active task snapshot fields."""
        return self.patch(
            active_task_snapshot=snapshot,
            active_task_id=getattr(snapshot, 'task_id', ''),
            active_task_kind=getattr(snapshot, 'task_kind', ''),
            task_state=getattr(snapshot, 'state', ''),
            task_stop_reason=getattr(snapshot, 'stop_reason', ''),
            task_correlation_id=getattr(snapshot, 'correlation_id', ''),
        )

    def patch_error(self, error_presentation) -> SessionState:
        """Patch the last structured error presentation."""
        return self.patch(
            last_error=getattr(error_presentation, 'user_message', ''),
            last_error_payload=dict(getattr(error_presentation, 'log_payload', {}) or {}),
            last_error_code=str(getattr(error_presentation, 'error_code', '') or ''),
            last_error_title=str(getattr(error_presentation, 'title', '') or ''),
            last_error_severity=str(getattr(error_presentation, 'severity', '') or ''),
            last_error_hint=str(getattr(error_presentation, 'remediation_hint', '') or ''),
        )

    def patch_warning(self, code: str, message: str) -> SessionState:
        """Patch warning state while preserving prior warning history."""
        codes = tuple(dict.fromkeys((*self._state.active_warning_codes, str(code))))
        warnings = tuple(dict.fromkeys((*self._state.warnings, str(message))))
        return self.patch(active_warning_codes=codes, warnings=warnings, last_warning=str(message))

    def patch_scene(self, scene_summary: dict[str, object], *, planning_scene: object | None = None, scene_revision: int | None = None) -> SessionState:
        """Patch planning scene projection state."""
        kwargs: dict[str, object] = {'scene_summary': dict(scene_summary)}
        if planning_scene is not None:
            kwargs['planning_scene'] = planning_scene
        if scene_revision is not None:
            kwargs['scene_revision'] = int(scene_revision)
        return self.patch(**kwargs)

    def patch_capabilities(self, capability_matrix) -> SessionState:
        """Patch capability matrix state from a structured capability object."""
        payload = capability_matrix.as_dict() if hasattr(capability_matrix, 'as_dict') else dict(capability_matrix)
        return self.patch(capability_matrix=payload)

    def replace(self, state: SessionState) -> SessionState:
        """Replace the entire session state and notify subscribers."""
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        self._state = state
        return self.notify()

    def snapshot(self) -> SessionState:
        """Return a deep copy of the current state for serialization or tests."""
        return deepcopy(self._state)
<<<<<<< HEAD

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
