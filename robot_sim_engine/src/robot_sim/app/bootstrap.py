from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from robot_sim.app.container import AppContainer, build_container
from robot_sim.app.runtime_paths import resolve_runtime_paths
from robot_sim.app.version_catalog import VersionCatalog, default_version_catalog
from robot_sim.app.runtime_environment import evaluate_startup_environment
from robot_sim.infra.compatibility_usage import record_compatibility_usage
from robot_sim.infra.logging_setup import setup_logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootstrapContext:
    """Canonical bootstrap result for startup callers.

    Args:
        project_root: Repository-style compatibility root retained for callers that still
            need a user-visible project anchor.
        container: Fully built application dependency container.

    Boundary behavior:
        The canonical startup surface is attribute-based access through
        ``BootstrapContext.project_root`` and ``BootstrapContext.container``.
        Iterable/indexed access is retained strictly as a compatibility path for
        legacy callers that still unpack the historical ``(project_root, container)``
        tuple shape.
    """

    project_root: Path
    container: AppContainer

    def __iter__(self) -> Iterator[object]:
        """Yield the historical tuple payload for compatibility destructuring.

        Returns:
            Iterator[object]: Iterator over ``project_root`` then ``container``.

        Raises:
            None: The compatibility surface only reads in-memory state.
        """
        record_compatibility_usage('bootstrap iterable unpacking', detail='iter')
        yield self.project_root
        yield self.container

    def __len__(self) -> int:
        """Return the historical bootstrap tuple length."""
        return 2

    def __getitem__(self, index: int):
        """Expose tuple-style positional access for legacy callers.

        Args:
            index: Positional bootstrap item index.

        Returns:
            object: ``project_root`` for index 0 and ``container`` for index 1.

        Raises:
            IndexError: If ``index`` is outside the supported bootstrap payload.
        """
        record_compatibility_usage('bootstrap iterable unpacking', detail=f'index:{index}')
        if index == 0:
            return self.project_root
        if index == 1:
            return self.container
        raise IndexError(index)

    def as_tuple(self) -> tuple[Path, AppContainer]:
        """Return the compatibility tuple payload.

        Returns:
            tuple[Path, AppContainer]: Historical bootstrap tuple payload.

        Raises:
            None: Pure projection helper.
        """
        record_compatibility_usage('bootstrap iterable unpacking', detail='as_tuple')
        return self.project_root, self.container


def get_project_root() -> Path:
    """Return the compatibility project root used by legacy startup callers.

    Returns:
        Path: Preferred project root for repository-style execution.

    Raises:
        None: Pure path discovery.
    """
    return Path(__file__).resolve().parents[3]


def _log_startup_summary(container: AppContainer, versions: VersionCatalog) -> dict[str, object]:
    """Log and return a startup summary derived from the application container.

    Args:
        container: Fully built application dependency container.
        versions: Version catalog used to project export/session schema versions.

    Returns:
        dict[str, object]: Structured startup summary used for logs and tests.

    Raises:
        None: Failures are contained to defensive logging.
    """
    summary: dict[str, object] = {
        'app_version': versions.app_version,
        'schemas': {
            'export': versions.export_schema_version,
            'session': versions.session_schema_version,
            'benchmark': versions.benchmark_pack_version,
        },
        'capabilities': {},
        'runtime': {},
    }
    try:
        matrix = container.capability_matrix_service.build_matrix(
            solver_registry=container.solver_registry,
            planner_registry=container.planner_registry,
            importer_registry=container.importer_registry,
        ).as_dict()
        plugin_catalog = dict((getattr(container, 'runtime_context', {}) or {}).get('plugin_catalog', {}) or {})
        plugin_counts = dict(plugin_catalog.get('counts', {}) or {})
        summary['capabilities'] = {
            'solvers': len(matrix.get('solvers', [])),
            'planners': len(matrix.get('planners', [])),
            'importers': len(matrix.get('importers', [])),
            'plugin_registrations_enabled': int(plugin_counts.get('enabled', 0)),
        }
        plugin_catalog = dict((getattr(container, 'runtime_context', {}) or {}).get('plugin_catalog', {}) or {})
        plugin_counts = dict(plugin_catalog.get('counts', {}) or {})
        summary['runtime'] = {
            'project_root': str(container.project_root),
            'resource_root': str(container.runtime_paths.resource_root),
            'config_root': str(container.runtime_paths.config_root),
            'export_root': str(container.runtime_paths.export_root),
            'layout_mode': container.runtime_paths.layout_mode,
            'source_layout_available': bool(container.runtime_paths.source_layout_available),
            'config_resolution': container.config_service.describe_resolution(),
            'plugin_policy': container.runtime_feature_policy.as_dict(),
            'plugin_catalog_counts': plugin_counts,
        }
        logger.info('robot-sim startup summary=%s', summary)
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.warning('failed to log startup summary: %s', exc)
    return summary


def bootstrap(*, startup_mode: str | None = None) -> BootstrapContext:
    """Initialize logging and build the application container.

    Args:
        startup_mode: Optional startup environment contract mode. ``gui`` enforces the GUI
            runtime contract, ``release`` enforces the packaged-release contract, and
            ``headless`` records the environment without requiring GUI/build dependencies.
            When omitted the mode is resolved from ``ROBOT_SIM_STARTUP_MODE`` and defaults to
            ``gui`` so the public GUI entrypoint remains fail-closed.

    Returns:
        BootstrapContext: Canonical bootstrap result exposing ``project_root`` and
            ``container`` as named attributes.

    Raises:
        Exception: Propagates logging/configuration/container construction failures.

    Boundary behavior:
        Runtime resource resolution is driven by ``resolve_runtime_paths()`` rather than by a
        repository-layout assumption. Iterable/indexed access remains available only as a
        compatibility surface for historical callers that still unpack bootstrap like a tuple.
    """
    runtime_paths = resolve_runtime_paths()
    setup_logging(runtime_paths.logging_config_path)
    normalized_startup_mode = str(startup_mode or os.environ.get('ROBOT_SIM_STARTUP_MODE', 'gui') or 'gui').strip().lower() or 'gui'
    environment_status = evaluate_startup_environment(runtime_paths, mode=normalized_startup_mode)
    if environment_status.strict and not environment_status.ok:
        report = environment_status.report
        details = '; '.join(report.errors) if report is not None else 'startup environment contract unavailable'
        raise RuntimeError(f'GUI startup environment contract failed: {details}')
    container = build_container(runtime_paths)
    if getattr(container, 'runtime_context', None) is not None:
        container.runtime_context['startup_environment'] = environment_status.summary()
        container.runtime_context['startup_mode'] = normalized_startup_mode
    startup_summary = _log_startup_summary(container, default_version_catalog())
    startup_summary['startup_environment'] = environment_status.summary()
    startup_summary['startup_mode'] = normalized_startup_mode
    if hasattr(container, 'startup_summary'):
        setattr(container, 'startup_summary', startup_summary)
    return BootstrapContext(project_root=runtime_paths.project_root, container=container)
