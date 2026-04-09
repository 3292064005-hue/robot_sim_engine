from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
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
from robot_sim.app.runtime_paths import RuntimePaths


class MainControllerContainerProtocol(Protocol):
    """Explicit dependency contract required to bootstrap presentation collaborators.

    ``MainController`` no longer reaches into the concrete container field-by-field during
    object-graph assembly. Instead the startup path materializes a typed
    :class:`PresentationBootstrapBundle`, and the controller becomes a compatibility shell
    over that bundle. The protocol remains explicit so startup still fails fast when the
    application container is incomplete.
    """

    config_service: ConfigService
    robot_registry: RobotRegistry
    metrics_service: MetricsService
    export_service: ExportService
    solver_registry: SolverRegistry
    planner_registry: PlannerRegistry
    importer_registry: ImporterRegistry
    capability_matrix_service: CapabilityService
    module_status_service: ModuleStatusService
    task_error_mapper: TaskErrorMapper
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
    runtime_paths: RuntimePaths


@dataclass(frozen=True)
class PresentationRegistryBundle:
    """Registry dependencies consumed by the presentation startup shell."""

    robot_registry: RobotRegistry
    solver_registry: SolverRegistry
    planner_registry: PlannerRegistry
    importer_registry: ImporterRegistry


@dataclass(frozen=True)
class PresentationServiceBundle:
    """Long-lived service dependencies consumed by presentation runtime startup."""

    config_service: ConfigService
    metrics_service: MetricsService
    export_service: ExportService
    capability_service: CapabilityService
    module_status_service: ModuleStatusService
    task_error_mapper: TaskErrorMapper
    playback_service: PlaybackService
    runtime_paths: RuntimePaths | None
    runtime_feature_policy: RuntimeFeaturePolicy | None = None


@dataclass(frozen=True)
class PresentationUseCaseBundle:
    """Use-case dependencies consumed by the presentation runtime shell."""

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
class PresentationBootstrapBundle:
    """Typed presentation bootstrap dependency bundle.

    This bundle narrows the application-container surface consumed by presentation startup.
    Startup code may still source these dependencies from ``AppContainer`` or a compatible
    stand-in, but the rest of the presentation layer no longer needs to know the concrete
    container attribute layout.
    """

    project_root: Path
    registries: PresentationRegistryBundle
    services: PresentationServiceBundle
    use_cases: PresentationUseCaseBundle


def build_presentation_bootstrap_bundle(
    project_root: str | Path,
    *,
    container: MainControllerContainerProtocol,
) -> PresentationBootstrapBundle:
    """Materialize the typed presentation bootstrap bundle from the application container.

    Args:
        project_root: Runtime project root retained for compatibility with startup callers.
        container: Application container or compatible protocol implementation.

    Returns:
        PresentationBootstrapBundle: Narrow typed dependency bundle for presentation startup.

    Raises:
        ValueError: If ``container`` is missing.
    """
    if container is None:
        raise ValueError('build_presentation_bootstrap_bundle requires an explicit application container')
    return PresentationBootstrapBundle(
        project_root=Path(project_root),
        registries=PresentationRegistryBundle(
            robot_registry=container.robot_registry,
            solver_registry=container.solver_registry,
            planner_registry=container.planner_registry,
            importer_registry=container.importer_registry,
        ),
        services=PresentationServiceBundle(
            config_service=container.config_service,
            metrics_service=container.metrics_service,
            export_service=container.export_service,
            capability_service=container.capability_matrix_service,
            module_status_service=container.module_status_service,
            task_error_mapper=container.task_error_mapper,
            playback_service=container.playback_service,
            runtime_paths=getattr(container, 'runtime_paths', None),
            runtime_feature_policy=getattr(container, 'runtime_feature_policy', None),
        ),
        use_cases=PresentationUseCaseBundle(
            fk_uc=container.fk_uc,
            ik_uc=container.ik_uc,
            traj_uc=container.traj_uc,
            benchmark_uc=container.benchmark_uc,
            save_session_uc=container.save_session_uc,
            playback_uc=container.playback_uc,
            export_report_uc=container.export_report_uc,
            export_package_uc=container.export_package_uc,
            import_robot_uc=container.import_robot_uc,
        ),
    )
