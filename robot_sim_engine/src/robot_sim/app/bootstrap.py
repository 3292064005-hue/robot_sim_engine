from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from robot_sim.app.container import AppContainer, build_container
from robot_sim.app.runtime_paths import resolve_runtime_paths
from robot_sim.app.version_catalog import VersionCatalog, default_version_catalog
from robot_sim.app.runtime_environment import evaluate_startup_environment
from robot_sim.infra.logging_setup import setup_logging
from robot_sim.model.runtime_snapshots import PluginCatalogSnapshot, RuntimeContextSnapshot, StartupSummarySnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootstrapContext:
    """Canonical bootstrap result for startup callers.

    Args:
        project_root: Canonical runtime project root exposed to startup callers.
        container: Fully built application dependency container.

    Boundary behavior:
        The bootstrap surface is attribute-based only. Callers must consume
        ``BootstrapContext.project_root`` and ``BootstrapContext.container`` directly.
    """

    project_root: Path
    container: AppContainer


def get_project_root() -> Path:
    """Return the canonical project root used by source-tree startup callers.

    Returns:
        Path: Preferred project root for repository-style execution.

    Raises:
        None: Pure path discovery.
    """
    return Path(__file__).resolve().parents[3]


def _log_startup_summary(container: AppContainer, versions: VersionCatalog) -> StartupSummarySnapshot:
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
        bootstrap_bundle = container.bootstrap_bundle
        matrix = bootstrap_bundle.services.capability_matrix_service.build_matrix(
            solver_registry=bootstrap_bundle.registries.solver_registry,
            planner_registry=bootstrap_bundle.registries.planner_registry,
            importer_registry=bootstrap_bundle.registries.importer_registry,
        ).as_dict()
        plugin_catalog = dict((getattr(container, 'runtime_context', {}) or {}).get('plugin_catalog', {}) or {})
        plugin_counts = dict(plugin_catalog.get('counts', {}) or {})
        summary['capabilities'] = {
            'solvers': len(matrix.get('solvers', [])),
            'planners': len(matrix.get('planners', [])),
            'importers': len(matrix.get('importers', [])),
            'plugin_registrations_enabled': int(plugin_counts.get('enabled', 0)),
            'runtime_provider_count': int(plugin_counts.get('capability_total', 0)),
            'runtime_provider_enabled_count': int(plugin_counts.get('capability_enabled', 0)),
            'capability_ontology_version': 'v2',
            'environment_contract_version': 'v2',
            'trajectory_stage_provider_surface_version': 'v1',
        }
        plugin_catalog = dict((getattr(container, 'runtime_context', {}) or {}).get('plugin_catalog', {}) or {})
        plugin_counts = dict(plugin_catalog.get('counts', {}) or {})
        runtime_paths = bootstrap_bundle.services.runtime_paths
        summary['runtime'] = {
            'project_root': str(container.project_root),
            'resource_root': str(runtime_paths.resource_root),
            'config_root': str(runtime_paths.config_root),
            'export_root': str(runtime_paths.export_root),
            'layout_mode': runtime_paths.layout_mode,
            'source_layout_available': bool(runtime_paths.source_layout_available),
            'config_resolution': bootstrap_bundle.services.config_service.describe_resolution(),
            'plugin_policy': bootstrap_bundle.services.runtime_feature_policy.as_dict(),
            'plugin_catalog_counts': plugin_counts,
            'capability_ontology_version': 'v2',
            'environment_contract': {
                'version': 'v2',
                'supports_clone': True,
                'supports_replay': True,
                'supports_diff_replication': True,
                'supports_concurrent_snapshots': True,
            },
        }
        logger.info('robot-sim startup summary=%s', summary)
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.warning('failed to log startup summary: %s', exc)
    return StartupSummarySnapshot(
        app_version=str(summary.get('app_version', versions.app_version)),
        schemas=dict(summary.get('schemas', {}) or {}),
        capabilities=dict(summary.get('capabilities', {}) or {}),
        runtime=dict(summary.get('runtime', {}) or {}),
        startup_environment=dict(summary.get('startup_environment', {}) or {}),
        startup_mode=str(summary.get('startup_mode', '') or ''),
    )


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
        repository-layout assumption. The bootstrap result is a typed attribute surface;
        historical tuple-style unpacking is no longer supported in the shipped mainline.
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
    runtime_context = getattr(container, 'runtime_context', None)
    if runtime_context is not None:
        if isinstance(runtime_context, RuntimeContextSnapshot):
            container.runtime_context = runtime_context.with_startup(
                startup_environment=environment_status.summary(),
                startup_mode=normalized_startup_mode,
            )
        else:
            raw_runtime_context = dict(runtime_context or {})
            raw_plugin_catalog = dict(raw_runtime_context.get('plugin_catalog', {}) or {})
            container.runtime_context = RuntimeContextSnapshot(
                project_root=str(raw_runtime_context.get('project_root', runtime_paths.project_root)),
                resource_root=str(raw_runtime_context.get('resource_root', getattr(runtime_paths, 'resource_root', runtime_paths.project_root))),
                config_root=str(raw_runtime_context.get('config_root', getattr(runtime_paths, 'config_root', runtime_paths.project_root))),
                robot_root=str(raw_runtime_context.get('robot_root', '')),
                bundled_robot_root=str(raw_runtime_context.get('bundled_robot_root', '')),
                profiles_root=str(raw_runtime_context.get('profiles_root', '')),
                plugin_manifest_path=str(raw_runtime_context.get('plugin_manifest_path', '')),
                plugin_manifest_paths=tuple(str(item) for item in raw_runtime_context.get('plugin_manifest_paths', ()) or ()),
                export_root=str(raw_runtime_context.get('export_root', getattr(runtime_paths, 'export_root', runtime_paths.project_root))),
                layout_mode=str(raw_runtime_context.get('layout_mode', 'unknown') or 'unknown'),
                runtime_feature_policy=dict(raw_runtime_context.get('runtime_feature_policy', {}) or {}),
                profiles=tuple(str(item) for item in raw_runtime_context.get('profiles', ()) or ()),
                plugin_discovery_enabled=bool(raw_runtime_context.get('plugin_discovery_enabled', False)),
                plugin_catalog=PluginCatalogSnapshot(
                    governance_entries=tuple(dict(item) for item in raw_plugin_catalog.get('governance_entries', raw_plugin_catalog.get('entries', ())) or ()),
                    capability_entries=tuple(dict(item) for item in raw_plugin_catalog.get('capability_entries', raw_plugin_catalog.get('entries', ())) or ()),
                    scene_backend_runtime_plugins=tuple(str(item) for item in raw_plugin_catalog.get('scene_backend_runtime_plugins', ()) or ()),
                    collision_backend_runtime_plugins=tuple(str(item) for item in raw_plugin_catalog.get('collision_backend_runtime_plugins', ()) or ()),
                ),
                source_layout_available=bool(raw_runtime_context.get('source_layout_available', False)),
                config_resolution=dict(raw_runtime_context.get('config_resolution', {}) or {}),
                startup_environment=environment_status.summary(),
                startup_mode=normalized_startup_mode,
            )
    startup_summary = _log_startup_summary(container, default_version_catalog())
    startup_summary = StartupSummarySnapshot(
        app_version=startup_summary.app_version,
        schemas=dict(startup_summary.schemas),
        capabilities=dict(startup_summary.capabilities),
        runtime=dict(startup_summary.runtime),
        startup_environment=environment_status.summary(),
        startup_mode=normalized_startup_mode,
    )
    if hasattr(container, 'startup_summary'):
        setattr(container, 'startup_summary', startup_summary)
    return BootstrapContext(project_root=runtime_paths.project_root, container=container)
