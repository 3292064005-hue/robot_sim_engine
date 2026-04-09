from __future__ import annotations

from copy import deepcopy
from typing import Callable, TypeVar

StateSegment = str
StateSubscriber = Callable[[object], None]
SelectorValue = TypeVar("SelectorValue")
SelectorSnapshot = Callable[[SelectorValue], object]

GLOBAL_SEGMENT = 'global'
SESSION_SEGMENT = 'session'
TASK_SEGMENT = 'task'
RENDER_SEGMENT = 'render'
SEGMENT_NAMES: tuple[StateSegment, ...] = (
    GLOBAL_SEGMENT,
    SESSION_SEGMENT,
    TASK_SEGMENT,
    RENDER_SEGMENT,
)

SNAPSHOT_DEEPCOPY = 'deepcopy'
SNAPSHOT_IDENTITY = 'identity'
SNAPSHOT_CUSTOM = 'custom'
SELECTOR_SNAPSHOT_STRATEGIES = (
    SNAPSHOT_DEEPCOPY,
    SNAPSHOT_IDENTITY,
    SNAPSHOT_CUSTOM,
)


def resolve_selector_snapshot_builder(
    *,
    snapshot_strategy: str,
    snapshot_factory: SelectorSnapshot | None,
) -> SelectorSnapshot:
    """Return the snapshot builder used by selector subscriptions.

    Args:
        snapshot_strategy: Snapshot strategy name.
        snapshot_factory: Optional custom snapshot builder.

    Returns:
        SelectorSnapshot: Callable that produces the persisted comparison snapshot.

    Raises:
        ValueError: If the strategy is unsupported or ``custom`` is requested without
            a snapshot factory.
    """
    normalized = str(snapshot_strategy or SNAPSHOT_DEEPCOPY).strip().lower() or SNAPSHOT_DEEPCOPY
    if normalized not in SELECTOR_SNAPSHOT_STRATEGIES:
        raise ValueError(f'unsupported selector snapshot strategy: {snapshot_strategy!r}')
    if normalized == SNAPSHOT_IDENTITY:
        return lambda value: value
    if normalized == SNAPSHOT_CUSTOM:
        if snapshot_factory is None:
            raise ValueError("snapshot_factory is required when snapshot_strategy='custom'")
        return snapshot_factory
    return lambda value: deepcopy(value)


def normalize_segment_name(segment: StateSegment) -> StateSegment:
    """Normalize and validate a single state-store segment name."""
    normalized = str(segment or GLOBAL_SEGMENT).strip().lower() or GLOBAL_SEGMENT
    if normalized not in SEGMENT_NAMES:
        raise ValueError(f'unsupported state-store segment: {segment!r}')
    return normalized


def normalize_segments(segment: StateSegment | tuple[StateSegment, ...] | None) -> tuple[StateSegment, ...]:
    """Normalize a segment selector into the canonical ordered segment tuple."""
    if segment is None:
        return tuple(name for name in SEGMENT_NAMES if name != GLOBAL_SEGMENT)
    if isinstance(segment, tuple):
        return tuple(dict.fromkeys(normalize_segment_name(item) for item in segment))
    return (normalize_segment_name(segment),)


def collect_subscribers(
    subscriber_registry: dict[StateSegment, list[StateSubscriber]],
    *,
    segments: tuple[StateSegment, ...],
    include_global: bool,
) -> tuple[StateSubscriber, ...]:
    """Collect ordered, de-duplicated subscribers for the selected segments."""
    ordered: list[StateSubscriber] = []
    seen_callbacks: set[int] = set()
    segment_order: list[StateSegment] = []
    if include_global:
        segment_order.append(GLOBAL_SEGMENT)
    segment_order.extend(name for name in segments if name != GLOBAL_SEGMENT)
    for name in segment_order:
        for callback in tuple(subscriber_registry[name]):
            identity = id(callback)
            if identity in seen_callbacks:
                continue
            seen_callbacks.add(identity)
            ordered.append(callback)
    return tuple(ordered)
