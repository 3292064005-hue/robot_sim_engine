from __future__ import annotations

import logging
from typing import Mapping

from robot_sim.app.compatibility_matrix import COMPATIBILITY_MATRIX, CompatibilityEntry, get_compatibility_entry

logger = logging.getLogger(__name__)

_COMPATIBILITY_USAGE_COUNTS: dict[str, int] = {
    entry.surface: 0 for entry in COMPATIBILITY_MATRIX
}
_COMPATIBILITY_USAGE_KEYS: set[tuple[str, str]] = set()


def record_compatibility_usage(surface: str, *, detail: str = '') -> CompatibilityEntry:
    """Record runtime usage of a retained compatibility path.

    Args:
        surface: Registered compatibility-surface identifier.
        detail: Optional de-duplication detail, such as the alias name or config kind.

    Returns:
        CompatibilityEntry: Registered metadata for the surface that was observed.

    Raises:
        KeyError: If ``surface`` is not present in ``COMPATIBILITY_MATRIX``.

    Boundary behavior:
        The in-memory usage counter increments on every observation, while log emission is
        de-duplicated per ``(surface, detail)`` pair to avoid flooding normal workflows.
    """
    normalized_surface = str(surface)
    entry = get_compatibility_entry(normalized_surface)
    normalized_detail = str(detail or '')
    _COMPATIBILITY_USAGE_COUNTS[normalized_surface] = int(_COMPATIBILITY_USAGE_COUNTS.get(normalized_surface, 0)) + 1
    dedupe_key = (normalized_surface, normalized_detail)
    if dedupe_key not in _COMPATIBILITY_USAGE_KEYS:
        _COMPATIBILITY_USAGE_KEYS.add(dedupe_key)
        suffix = f' detail={normalized_detail}' if normalized_detail else ''
        logger.warning(
            'compatibility surface used: %s owner=%s removal_target=%s%s',
            entry.surface,
            entry.owner,
            entry.removal_target,
            suffix,
        )
    return entry


def compatibility_usage_counts() -> Mapping[str, int]:
    """Return a snapshot of in-memory compatibility usage counts."""
    return dict(_COMPATIBILITY_USAGE_COUNTS)


def reset_compatibility_usage_counts() -> None:
    """Reset runtime compatibility usage counters and de-duplication state for tests."""
    for entry in COMPATIBILITY_MATRIX:
        _COMPATIBILITY_USAGE_COUNTS[entry.surface] = 0
    _COMPATIBILITY_USAGE_KEYS.clear()
