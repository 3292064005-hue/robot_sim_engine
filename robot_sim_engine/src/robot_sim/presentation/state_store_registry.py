from __future__ import annotations

import logging

from robot_sim.model.session_state import SessionState
from robot_sim.presentation.state_store_support import StateSegment, StateSubscriber, collect_subscribers, normalize_segment_name, normalize_segments

_LOG = logging.getLogger(__name__)
_HANDLED_NOTIFY_ERRORS = (
    AttributeError,
    LookupError,
    RuntimeError,
    TypeError,
    ValueError,
    OSError,
    ArithmeticError,
    AssertionError,
)


class StateSubscriberRegistry:
    """Own per-segment state-store subscribers and notification policy."""

    def __init__(self, *, segments: tuple[StateSegment, ...]) -> None:
        self._subscribers: dict[StateSegment, list[StateSubscriber]] = {segment: [] for segment in segments}

    def subscribe(self, callback: StateSubscriber, *, segment: StateSegment) -> StateSegment:
        normalized = normalize_segment_name(segment)
        self._subscribers[normalized].append(callback)
        return normalized

    def unsubscribe(self, callback: StateSubscriber, *, segment: StateSegment | None = None) -> None:
        for name in normalize_segments(segment):
            try:
                self._subscribers[name].remove(callback)
            except ValueError:
                continue

    def notify(
        self,
        state: SessionState,
        *,
        segment: StateSegment | tuple[StateSegment, ...] | None = None,
        include_global: bool = True,
    ) -> SessionState:
        segment_names = normalize_segments(segment)
        callbacks = collect_subscribers(self._subscribers, segments=segment_names, include_global=include_global)
        for subscriber in callbacks:
            try:
                subscriber(state)
            except _HANDLED_NOTIFY_ERRORS:
                _LOG.exception('state-store subscriber failed during notify', extra={'segments': segment_names})
        return state
