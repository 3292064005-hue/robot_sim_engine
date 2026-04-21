from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from robot_sim.model.session_state import SessionState
from robot_sim.application.services.render_runtime_advisor import RenderRuntimeAdvisor
from robot_sim.presentation.state_segments import (
    RenderStateSegmentStore,
    SessionStateSegmentStore,
    TaskStateSegmentStore,
)
from robot_sim.presentation.state_store_api import StateStoreApiMixin
from robot_sim.presentation.state_store_registry import StateSubscriberRegistry
from robot_sim.presentation.state_events import reduce_state_event
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

    The public ``StateStore`` API exposes the canonical GUI state surface. Internally the
    store keeps segment-local subscriber registries so render telemetry can notify only
    render-aware projections instead of forcing every selector subscriber onto the hot
    path. Global subscribers remain supported and continue to observe all segment updates.
    """

    def __init__(self, state: SessionState | None = None, *, render_runtime_advisor: RenderRuntimeAdvisor | None = None) -> None:
        self._state = state or SessionState()
        self._subscriber_registry = StateSubscriberRegistry(segments=_SEGMENT_NAMES)
        self.session_store = SessionStateSegmentStore(self)
        self.task_store = TaskStateSegmentStore(self)
        self.render_store = RenderStateSegmentStore(self, runtime_advisor=render_runtime_advisor)

    @property
    def state(self) -> SessionState:
        """Return the current mutable application session state."""
        return self._state

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
        if emit_current:
            callback(self._state)

        def _unsubscribe() -> None:
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
                ``deepcopy`` preserves the default defensive behavior, ``identity``
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
            default ``deepcopy`` snapshot policy.
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

    def dispatch(self, event: object) -> SessionState:
        """Reduce one canonical presentation-state event and notify affected segments.

        Args:
            event: Structured event dataclass understood by ``reduce_state_event``.

        Returns:
            SessionState: The mutated shared state after reducer application.

        Raises:
            TypeError: If ``event`` is unsupported by the reducer.
        """
        segments = normalize_segments(reduce_state_event(self._state, event))
        return self.notify(segment=segments)

    def replace(self, state: SessionState) -> SessionState:
        """Replace the entire session state and notify every subscriber bucket."""
        self._state = state
        return self.notify()

    def snapshot(self) -> SessionState:
        """Return a deep copy of the current state for serialization or tests."""
        return deepcopy(self._state)

