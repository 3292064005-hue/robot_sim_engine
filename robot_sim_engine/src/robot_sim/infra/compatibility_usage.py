from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Mapping

from robot_sim.app.compatibility_matrix import COMPATIBILITY_MATRIX, CompatibilityEntry, get_compatibility_entry

logger = logging.getLogger(__name__)

_COMPATIBILITY_USAGE_COUNTS: dict[str, int] = {entry.surface: 0 for entry in COMPATIBILITY_MATRIX}
_COMPATIBILITY_USAGE_DETAILS: dict[str, dict[str, int]] = {entry.surface: {} for entry in COMPATIBILITY_MATRIX}
_COMPATIBILITY_USAGE_KEYS: set[tuple[str, str]] = set()


def record_compatibility_usage(surface: str, *, detail: str = '') -> CompatibilityEntry:
    """Record runtime usage of a retained compatibility path.

    Args:
        surface: Registered compatibility-surface identifier.
        detail: Optional usage detail such as an alias mapping or config kind.

    Returns:
        CompatibilityEntry: Registered metadata describing the observed surface.

    Raises:
        KeyError: If ``surface`` is not present in ``COMPATIBILITY_MATRIX``.

    Boundary behavior:
        Total surface counts increment on every observation. Detail counts also increment
        on every observation, while log emission is still de-duplicated per
        ``(surface, detail)`` pair to avoid warning spam during normal workflows.
    """
    normalized_surface = str(surface)
    normalized_detail = str(detail or '')
    entry = get_compatibility_entry(normalized_surface)
    _COMPATIBILITY_USAGE_COUNTS[normalized_surface] = int(_COMPATIBILITY_USAGE_COUNTS.get(normalized_surface, 0)) + 1
    detail_counts = _COMPATIBILITY_USAGE_DETAILS.setdefault(normalized_surface, {})
    if normalized_detail:
        detail_counts[normalized_detail] = int(detail_counts.get(normalized_detail, 0)) + 1
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
    """Return a snapshot of aggregate compatibility usage counts."""
    return dict(_COMPATIBILITY_USAGE_COUNTS)


def compatibility_usage_snapshot() -> dict[str, object]:
    """Return a structured compatibility-usage snapshot.

    Returns:
        dict[str, object]: Aggregate counts and per-surface detail counts suitable for
            evidence artifacts or migration review.
    """
    details: dict[str, dict[str, int]] = {}
    for surface, counts in _COMPATIBILITY_USAGE_DETAILS.items():
        details[str(surface)] = {str(key): int(value) for key, value in sorted(counts.items())}
    return {
        'surface_counts': {str(key): int(value) for key, value in sorted(_COMPATIBILITY_USAGE_COUNTS.items())},
        'detail_counts': details,
    }


def write_compatibility_usage_snapshot(
    path: str | Path,
    *,
    scenario: str = '',
    budget=None,
    violations=(),
) -> Path:
    """Persist a compatibility-usage snapshot to disk.

    Args:
        path: JSON destination.
        scenario: Optional scenario identifier that produced the snapshot.
        budget: Optional compatibility-budget object for the executed scenario.
        violations: Optional iterable of budget-violation strings.

    Returns:
        Path: The written JSON path.
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = compatibility_usage_snapshot()
    payload['scenario'] = str(scenario or '')
    payload['violations'] = [str(item) for item in violations]
    if budget is not None:
        payload['budget'] = {
            'scenario': str(getattr(budget, 'scenario', '') or ''),
            'surface_limits': {str(key): int(value) for key, value in dict(getattr(budget, 'surface_limits', {}) or {}).items()},
        }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    return output


def reset_compatibility_usage_counts() -> None:
    """Reset runtime compatibility usage counters and de-duplication state for tests."""
    for entry in COMPATIBILITY_MATRIX:
        _COMPATIBILITY_USAGE_COUNTS[entry.surface] = 0
        _COMPATIBILITY_USAGE_DETAILS[entry.surface] = {}
    _COMPATIBILITY_USAGE_KEYS.clear()
