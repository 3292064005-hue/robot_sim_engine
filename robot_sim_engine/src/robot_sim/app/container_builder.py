from __future__ import annotations

import os
from pathlib import Path

from robot_sim.app.container_types import AppContainer
from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.app.registry_factory import build_importer_registry, build_planner_registry, build_solver_registry
from robot_sim.app.service_factory import (
    build_benchmark_service,
    build_capability_service,
    build_export_service,
    build_metrics_service,
    build_module_status_service,
    build_package_service,
    build_playback_service,
    build_runtime_feature_service,
)
from robot_sim.app.use_case_factory import UseCaseBundle, build_use_case_bundle
from robot_sim.application.pipelines.trajectory_pipeline_registry import build_trajectory_pipeline_registry
from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.services.task_error_mapper import TaskErrorMapper
from robot_sim.application.services.collision_backend_runtime import install_collision_backend_runtime_plugins
from robot_sim.application.services.scene_backend_runtime import install_scene_backend_runtime_plugins
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.model.runtime_snapshots import PluginCatalogSnapshot, RuntimeContextSnapshot
from robot_sim.app.runtime_paths import RuntimePaths, resolve_runtime_paths


def _attach_use_cases(container_kwargs: dict[str, object], bundle: UseCaseBundle) -> dict[str, object]:
    """Attach the constructed use-case bundle to container keyword arguments."""
    container_kwargs.update(
        fk_uc=bundle.fk_uc,
        ik_uc=bundle.ik_uc,
        traj_uc=bundle.traj_uc,
        benchmark_uc=bundle.benchmark_uc,
        save_session_uc=bundle.save_session_uc,
        playback_uc=bundle.playback_uc,
        export_report_uc=bundle.export_report_uc,
        export_package_uc=bundle.export_package_uc,
        import_robot_uc=bundle.import_robot_uc,
    )
    return container_kwargs


def _build_runtime_environment(runtime_paths: RuntimePaths) -> tuple[ConfigService, RuntimeFeaturePolicy, RobotRuntimeAssetService, PluginLoader, dict[str, object], tuple[str, ...], tuple[str, ...], TaskErrorMapper]:
    """Build configuration, plugin, and runtime policy services."""
    active_profile = str(os.environ.get('ROBOT_SIM_PROFILE', ConfigService.DEFAULT_PROFILE) or ConfigService.DEFAULT_PROFILE)
    config_service = ConfigService(runtime_paths.config_root, profile=active_profile)
    task_error_mapper = TaskErrorMapper()
    runtime_feature_service = build_runtime_feature_service(config_service)
    runtime_feature_policy = runtime_feature_service.load_policy()
    runtime_asset_service = RobotRuntimeAssetService(
        experimental_collision_backends_enabled=bool(getattr(runtime_feature_policy, 'experimental_backends_enabled', False))
    )
    runtime_asset_service.bind_runtime_context(
        profile_id=active_profile,
        collision_backend_scope='experimental' if bool(getattr(runtime_feature_policy, 'experimental_backends_enabled', False)) else 'stable',
        experimental_collision_backends_enabled=bool(getattr(runtime_feature_policy, 'experimental_backends_enabled', False)),
    )
    plugin_loader = PluginLoader(config_service.plugin_manifest_paths(), policy=runtime_feature_policy)
    plugin_catalog = plugin_loader.audit_split()
    installed_scene_backend_plugins = tuple(install_scene_backend_runtime_plugins(plugin_loader.registrations('scene_backend')))
    installed_collision_backend_plugins = tuple(install_collision_backend_runtime_plugins(plugin_loader.registrations('collision_backend')))
    return (
        config_service,
        runtime_feature_policy,
        runtime_asset_service,
        plugin_loader,
        plugin_catalog,
        installed_scene_backend_plugins,
        installed_collision_backend_plugins,
        task_error_mapper,
    )


def _build_runtime_context_snapshot(
    *,
    runtime_paths: RuntimePaths,
    config_service: ConfigService,
    runtime_feature_policy: RuntimeFeaturePolicy,
    plugin_catalog: dict[str, object],
    installed_scene_backend_plugins: tuple[str, ...],
    installed_collision_backend_plugins: tuple[str, ...],
) -> RuntimeContextSnapshot:
    """Build the stable typed runtime-context snapshot exported by startup flows."""
    plugin_manifest_paths = config_service.plugin_manifest_paths()
    return RuntimeContextSnapshot(
        project_root=str(runtime_paths.project_root),
        resource_root=str(runtime_paths.resource_root),
        config_root=str(runtime_paths.config_root),
        robot_root=str(runtime_paths.robot_root),
        bundled_robot_root=str(runtime_paths.bundled_robot_root),
        profiles_root=str(runtime_paths.profiles_root),
        plugin_manifest_path=str(runtime_paths.plugin_manifest_path),
        plugin_manifest_paths=tuple(str(path) for path in plugin_manifest_paths),
        export_root=str(runtime_paths.export_root),
        layout_mode=runtime_paths.layout_mode,
        runtime_feature_policy=runtime_feature_policy.as_dict(),
        profiles=tuple(config_service.available_profiles()),
        plugin_discovery_enabled=runtime_feature_policy.plugin_discovery_enabled,
        plugin_catalog=PluginCatalogSnapshot(
            governance_entries=tuple(dict(item) for item in plugin_catalog.get('governance_entries', ())),
            capability_entries=tuple(dict(item) for item in plugin_catalog.get('capability_entries', ())),
            scene_backend_runtime_plugins=tuple(str(item) for item in installed_scene_backend_plugins),
            collision_backend_runtime_plugins=tuple(str(item) for item in installed_collision_backend_plugins),
        ),
        source_layout_available=runtime_paths.source_layout_available,
        config_resolution=config_service.describe_resolution(),
    )


def build_container(project_root: str | Path | RuntimePaths) -> AppContainer:
    """Build the application dependency container.

    Args:
        project_root: Compatibility project root or pre-resolved runtime path bundle.

    Returns:
        AppContainer: Fully wired dependency container for the application runtime.

    Raises:
        Exception: Propagates configuration, registry, or service construction failures.
    """
    runtime_paths = project_root if isinstance(project_root, RuntimePaths) else resolve_runtime_paths(project_root)
    (
        config_service,
        runtime_feature_policy,
        runtime_asset_service,
        plugin_loader,
        plugin_catalog,
        installed_scene_backend_plugins,
        installed_collision_backend_plugins,
        task_error_mapper,
    ) = _build_runtime_environment(runtime_paths)

    robot_registry = RobotRegistry(
        runtime_paths.robot_root,
        readonly_roots=(runtime_paths.bundled_robot_root,),
    )
    metrics_service = build_metrics_service()
    export_service = build_export_service(runtime_paths.export_root)
    package_service = build_package_service(runtime_paths.export_root)
    playback_service = build_playback_service()
    capability_matrix_service = build_capability_service(
        runtime_feature_policy=runtime_feature_policy,
        plugin_loader=plugin_loader,
    )
    module_status_service = build_module_status_service(runtime_feature_policy=runtime_feature_policy)

    solver_registry = build_solver_registry(plugin_loader=plugin_loader)
    shared_ik_uc = RunIKUseCase(solver_registry)
    planner_registry = build_planner_registry(shared_ik_uc, plugin_loader=plugin_loader)
    importer_registry = build_importer_registry(robot_registry, plugin_loader=plugin_loader)
    benchmark_service: BenchmarkService = build_benchmark_service(shared_ik_uc)
    solver_settings = config_service.load_solver_settings()
    trajectory_pipeline_registry = build_trajectory_pipeline_registry(
        solver_settings.trajectory.pipelines,
        stage_catalog=solver_settings.trajectory.stage_catalog,
        runtime_feature_policy=runtime_feature_policy,
    )
    use_cases = build_use_case_bundle(
        solver_registry=solver_registry,
        planner_registry=planner_registry,
        importer_registry=importer_registry,
        benchmark_service=benchmark_service,
        export_service=export_service,
        package_service=package_service,
        playback_service=playback_service,
        ik_uc=shared_ik_uc,
        trajectory_pipeline_registry=trajectory_pipeline_registry,
    )

    container_kwargs: dict[str, object] = dict(
        project_root=runtime_paths.project_root,
        runtime_paths=runtime_paths,
        config_service=config_service,
        robot_registry=robot_registry,
        metrics_service=metrics_service,
        export_service=export_service,
        package_service=package_service,
        solver_registry=solver_registry,
        planner_registry=planner_registry,
        importer_registry=importer_registry,
        capability_matrix_service=capability_matrix_service,
        module_status_service=module_status_service,
        task_error_mapper=task_error_mapper,
        runtime_feature_policy=runtime_feature_policy,
        runtime_asset_service=runtime_asset_service,
        playback_service=playback_service,
        ik_uc=shared_ik_uc,
    )
    container = AppContainer(**_attach_use_cases(container_kwargs, use_cases))
    container.runtime_context = _build_runtime_context_snapshot(
        runtime_paths=runtime_paths,
        config_service=config_service,
        runtime_feature_policy=runtime_feature_policy,
        plugin_catalog=plugin_catalog,
        installed_scene_backend_plugins=installed_scene_backend_plugins,
        installed_collision_backend_plugins=installed_collision_backend_plugins,
    )
    return container
