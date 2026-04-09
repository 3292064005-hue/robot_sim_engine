from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompatibilityEntry:
    """Enumerated compatibility path retained for forward migration control."""

    surface: str
    owner: str
    compatibility_path: str
    rationale: str
    removal_target: str


COMPATIBILITY_MATRIX: tuple[CompatibilityEntry, ...] = ()

_COMPATIBILITY_BY_SURFACE: dict[str, CompatibilityEntry] = {}


def get_compatibility_entry(surface: str) -> CompatibilityEntry:
    """Return the registered compatibility entry for ``surface``."""
    raise KeyError(str(surface))
