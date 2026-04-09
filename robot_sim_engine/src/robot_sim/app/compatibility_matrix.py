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


COMPATIBILITY_MATRIX: tuple[CompatibilityEntry, ...] = (
    CompatibilityEntry(
        surface='bootstrap iterable unpacking',
        owner='robot_sim.app.bootstrap.bootstrap',
        compatibility_path='BootstrapContext iterable/indexed compatibility surface for historical unpacking',
        rationale='Older startup callers may still destructure or index the bootstrap result like the historical tuple.',
        removal_target='v0.9',
    ),
    CompatibilityEntry(
        surface='legacy config overrides',
        owner='robot_sim.application.services.config_service.ConfigService',
        compatibility_path='repository-level app.yaml / solver.yaml override opt-in',
        rationale='Ad-hoc local workflows may still rely on repository-side override files.',
        removal_target='v0.9',
    ),
    CompatibilityEntry(
        surface='main window private alias shim',
        owner='robot_sim.presentation.legacy_aliases.MainWindowLegacyAliasMixin',
        compatibility_path='historical *_impl names redirected to public on_* handlers',
        rationale='A small amount of out-of-repo automation still probes removed private names.',
        removal_target='v0.9',
    ),
    CompatibilityEntry(
        surface='worker legacy lifecycle signals',
        owner='robot_sim.application.workers.base.BaseWorker',
        compatibility_path='legacy progress/finished/failed/cancelled signals mirrored from structured events',
        rationale='Existing callbacks and ad-hoc workers still consume the legacy signal surface.',
        removal_target='v0.9',
    ),)

_COMPATIBILITY_BY_SURFACE: dict[str, CompatibilityEntry] = {
    entry.surface: entry for entry in COMPATIBILITY_MATRIX
}


def get_compatibility_entry(surface: str) -> CompatibilityEntry:
    """Return the registered compatibility entry for ``surface``.

    Args:
        surface: Stable compatibility-surface identifier from ``COMPATIBILITY_MATRIX``.

    Returns:
        CompatibilityEntry: Registered compatibility metadata.

    Raises:
        KeyError: If the requested surface is not registered.
    """
    return _COMPATIBILITY_BY_SURFACE[str(surface)]
