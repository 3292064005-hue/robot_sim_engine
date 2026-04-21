from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.package_service import PackageService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.services.task_error_mapper import TaskErrorMapper
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.model.runtime_snapshots import RuntimeContextSnapshot, StartupSummarySnapshot
from robot_sim.app.runtime_paths import RuntimePaths
from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.app.workflows.application_workflow import ApplicationWorkflowFacade


@dataclass(frozen=True)
class AppRegistryBundle:
    """Grouped registry surface exposed by :class:`AppContainer`."""

    robot_registry: RobotRegistry
    solver_registry: SolverRegistry
    planner_registry: PlannerRegistry
    importer_registry: ImporterRegistry


@dataclass(frozen=True)
class AppServiceBundle:
    """Grouped long-lived service surface exposed by :class:`AppContainer`."""

    runtime_paths: RuntimePaths
    config_service: ConfigService
    metrics_service: MetricsService
    export_service: ExportService
    package_service: PackageService
    capability_matrix_service: CapabilityService
    module_status_service: ModuleStatusService
    task_error_mapper: TaskErrorMapper
    runtime_feature_policy: RuntimeFeaturePolicy
    runtime_asset_service: RobotRuntimeAssetService
    playback_service: PlaybackService
    runtime_context: RuntimeContextSnapshot | None = None
    startup_summary: StartupSummarySnapshot | None = None


@dataclass(frozen=True)
class AppWorkflowBundle:
    """Grouped use-case/workflow surface exposed by :class:`AppContainer`."""

    fk_uc: RunFKUseCase
    ik_uc: RunIKUseCase
    traj_uc: PlanTrajectoryUseCase
    benchmark_uc: RunBenchmarkUseCase
    save_session_uc: SaveSessionUseCase
    playback_uc: StepPlaybackUseCase
    export_report_uc: ExportReportUseCase
    export_package_uc: ExportPackageUseCase
    import_robot_uc: ImportRobotUseCase


@dataclass(frozen=True)
class AppBootstrapBundle:
    """Canonical grouped runtime surface consumed by startup shells."""

    registries: AppRegistryBundle
    services: AppServiceBundle
    workflows: AppWorkflowBundle
    workflow_facade: ApplicationWorkflowFacade


@dataclass
class AppContainer:
    """Application dependency container."""

    project_root: Path
    runtime_paths: RuntimePaths
    config_service: ConfigService
    robot_registry: RobotRegistry
    metrics_service: MetricsService
    export_service: ExportService
    package_service: PackageService
    solver_registry: SolverRegistry
    planner_registry: PlannerRegistry
    importer_registry: ImporterRegistry
    capability_matrix_service: CapabilityService
    module_status_service: ModuleStatusService
    task_error_mapper: TaskErrorMapper
    runtime_feature_policy: RuntimeFeaturePolicy
    runtime_asset_service: RobotRuntimeAssetService
    fk_uc: RunFKUseCase
    ik_uc: RunIKUseCase
    traj_uc: PlanTrajectoryUseCase
    benchmark_uc: RunBenchmarkUseCase
    save_session_uc: SaveSessionUseCase
    playback_service: PlaybackService
    playback_uc: StepPlaybackUseCase
    export_report_uc: ExportReportUseCase
    export_package_uc: ExportPackageUseCase
    import_robot_uc: ImportRobotUseCase
    startup_summary: StartupSummarySnapshot | None = None
    runtime_context: RuntimeContextSnapshot | None = None

    @property
    def registry_bundle(self) -> AppRegistryBundle:
        return AppRegistryBundle(
            robot_registry=self.robot_registry,
            solver_registry=self.solver_registry,
            planner_registry=self.planner_registry,
            importer_registry=self.importer_registry,
        )

    @property
    def service_bundle(self) -> AppServiceBundle:
        return AppServiceBundle(
            runtime_paths=self.runtime_paths,
            config_service=self.config_service,
            metrics_service=self.metrics_service,
            export_service=self.export_service,
            package_service=self.package_service,
            capability_matrix_service=self.capability_matrix_service,
            module_status_service=self.module_status_service,
            task_error_mapper=self.task_error_mapper,
            runtime_feature_policy=self.runtime_feature_policy,
            runtime_asset_service=self.runtime_asset_service,
            playback_service=self.playback_service,
            runtime_context=self.runtime_context,
            startup_summary=self.startup_summary,
        )

    @property
    def workflow_bundle(self) -> AppWorkflowBundle:
        return AppWorkflowBundle(
            fk_uc=self.fk_uc,
            ik_uc=self.ik_uc,
            traj_uc=self.traj_uc,
            benchmark_uc=self.benchmark_uc,
            save_session_uc=self.save_session_uc,
            playback_uc=self.playback_uc,
            export_report_uc=self.export_report_uc,
            export_package_uc=self.export_package_uc,
            import_robot_uc=self.import_robot_uc,
        )

    @property
    def workflow_facade(self) -> ApplicationWorkflowFacade:
        return ApplicationWorkflowFacade(
            registries=self.registry_bundle,
            services=self.service_bundle,
            workflows=self.workflow_bundle,
            runtime_context=self.runtime_context,
            startup_summary=self.startup_summary,
        )

    @property
    def bootstrap_bundle(self) -> AppBootstrapBundle:
        return AppBootstrapBundle(
            registries=self.registry_bundle,
            services=self.service_bundle,
            workflows=self.workflow_bundle,
            workflow_facade=self.workflow_facade,
        )
