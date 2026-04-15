from __future__ import annotations

from dataclasses import dataclass

from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.package_service import PackageService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase


@dataclass(frozen=True)
class UseCaseBundle:
    fk_uc: RunFKUseCase
    ik_uc: RunIKUseCase
    traj_uc: PlanTrajectoryUseCase
    benchmark_uc: RunBenchmarkUseCase
    save_session_uc: SaveSessionUseCase
    playback_uc: StepPlaybackUseCase
    export_report_uc: ExportReportUseCase
    export_package_uc: ExportPackageUseCase
    import_robot_uc: ImportRobotUseCase


def build_use_case_bundle(
    *,
    solver_registry: SolverRegistry,
    planner_registry: PlannerRegistry,
    importer_registry: ImporterRegistry,
    benchmark_service: BenchmarkService,
    export_service: ExportService,
    package_service: PackageService,
    playback_service: PlaybackService,
    ik_uc: RunIKUseCase | None = None,
) -> UseCaseBundle:
    """Build the canonical application use-case bundle.

    Args:
        solver_registry: Solver registry used when the shared IK use case must be created.
        planner_registry: Planner registry consumed by the trajectory use case.
        importer_registry: Importer registry consumed by the robot import use case.
        benchmark_service: Benchmark service consumed by the benchmark use case.
        export_service: Export service consumed by report/session export use cases.
        package_service: Package service consumed by package export use cases.
        playback_service: Playback service consumed by playback stepping.
        ik_uc: Optional shared IK use case. When supplied, planner, benchmark, and runtime
            IK execution share one authority object.

    Returns:
        UseCaseBundle: Fully wired use-case bundle.

    Raises:
        None: Constructor failures propagate from downstream use cases.
    """
    fk_uc = RunFKUseCase()
    shared_ik_uc = ik_uc or RunIKUseCase(solver_registry)
    traj_uc = PlanTrajectoryUseCase(planner_registry)
    benchmark_uc = RunBenchmarkUseCase(benchmark_service)
    save_session_uc = SaveSessionUseCase(export_service)
    playback_uc = StepPlaybackUseCase(playback_service)
    export_report_uc = ExportReportUseCase(export_service)
    export_package_uc = ExportPackageUseCase(package_service)
    import_robot_uc = ImportRobotUseCase(importer_registry)
    return UseCaseBundle(
        fk_uc=fk_uc,
        ik_uc=shared_ik_uc,
        traj_uc=traj_uc,
        benchmark_uc=benchmark_uc,
        save_session_uc=save_session_uc,
        playback_uc=playback_uc,
        export_report_uc=export_report_uc,
        export_package_uc=export_package_uc,
        import_robot_uc=import_robot_uc,
    )
