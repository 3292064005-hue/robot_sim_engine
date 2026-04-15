from __future__ import annotations

from dataclasses import dataclass

from robot_sim.app.contracts import PresentationBootstrapBundle
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.benchmark_controller import BenchmarkController
from robot_sim.presentation.controllers.diagnostics_controller import DiagnosticsController
from robot_sim.presentation.controllers.export_controller import ExportController
from robot_sim.presentation.controllers.ik_controller import IKController
from robot_sim.presentation.controllers.playback_controller import PlaybackController
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.controllers.trajectory_controller import TrajectoryController
from robot_sim.presentation.facades import BenchmarkFacade, ExportFacade, PlaybackFacade, RobotFacade, RuntimeFacade, SolverFacade, TrajectoryFacade
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.workflow_services import ExportWorkflowService, MotionWorkflowService, RobotWorkflowService


@dataclass(frozen=True)
class PresentationControllerCollaborators:
    state_store: StateStore
    diagnostics_controller: DiagnosticsController
    robot_controller: RobotController
    ik_controller: IKController
    trajectory_controller: TrajectoryController
    playback_controller: PlaybackController
    benchmark_controller: BenchmarkController
    export_controller: ExportController
    runtime_facade: RuntimeFacade
    robot_facade: RobotFacade
    solver_facade: SolverFacade
    trajectory_facade: TrajectoryFacade
    playback_facade: PlaybackFacade
    benchmark_facade: BenchmarkFacade
    export_facade: ExportFacade
    robot_workflow: RobotWorkflowService
    motion_workflow: MotionWorkflowService
    export_workflow: ExportWorkflowService



def build_presentation_collaborators(bundle: PresentationBootstrapBundle) -> PresentationControllerCollaborators:
    state_store = StateStore(SessionState())
    capability_matrix = bundle.services.capability_service.build_matrix(
        solver_registry=bundle.registries.solver_registry,
        planner_registry=bundle.registries.planner_registry,
        importer_registry=bundle.registries.importer_registry,
    )
    state_store.patch_capabilities(capability_matrix)
    state_store.patch(
        segment='session',
        module_statuses=bundle.services.module_status_service.snapshot_details(),
    )
    diagnostics_controller = DiagnosticsController(state_store, bundle.services.metrics_service)
    ik_controller = IKController(
        state_store,
        bundle.services.config_service.load_solver_settings().ik.as_dict(),
        bundle.use_cases.fk_uc,
        bundle.use_cases.ik_uc,
    )
    runtime_asset_service = RobotRuntimeAssetService(
        experimental_collision_backends_enabled=bool(getattr(bundle.services.runtime_feature_policy, 'experimental_backends_enabled', False))
    )
    robot_controller = RobotController(
        state_store,
        bundle.registries.robot_registry,
        bundle.use_cases.fk_uc,
        import_robot_uc=bundle.use_cases.import_robot_uc,
        runtime_asset_service=runtime_asset_service,
    )
    solver_settings = bundle.services.config_service.load_solver_settings()
    trajectory_controller = TrajectoryController(
        state_store,
        bundle.use_cases.traj_uc,
        bundle.services.playback_service,
        ik_controller.build_ik_request,
        default_validation_layers=solver_settings.trajectory.validation_layers,
    )
    playback_controller = PlaybackController(state_store, bundle.services.playback_service, bundle.use_cases.playback_uc)
    benchmark_controller = BenchmarkController(state_store, bundle.use_cases.benchmark_uc, ik_controller.build_ik_request)
    app_settings = bundle.services.config_service.load_app_settings()
    app_config = app_settings.as_dict()
    runtime_paths = bundle.services.runtime_paths
    resource_root = bundle.project_root if runtime_paths is None else runtime_paths.resource_root
    config_root = bundle.project_root / 'configs' if runtime_paths is None else runtime_paths.config_root
    export_root = bundle.project_root / 'exports' if runtime_paths is None else runtime_paths.export_root
    runtime_facade = RuntimeFacade(
        project_root=bundle.project_root,
        resource_root=resource_root,
        config_root=config_root,
        export_root=export_root,
        app_config=app_config,
        app_settings=app_settings,
        solver_config=solver_settings.as_dict(),
        solver_settings=solver_settings,
        runtime_context=dict(bundle.services.runtime_context or {}),
        startup_summary=dict(bundle.services.startup_summary or {}),
        effective_config_snapshot=bundle.services.config_service.describe_effective_snapshot(),
        state_store=state_store,
        metrics_service=bundle.services.metrics_service,
        task_error_mapper=bundle.services.task_error_mapper,
        capability_service=bundle.services.capability_service,
        module_status_service=bundle.services.module_status_service,
    )
    export_controller = ExportController(
        state_store,
        bundle.services.export_service,
        bundle.use_cases.export_report_uc,
        bundle.use_cases.save_session_uc,
        bundle.use_cases.export_package_uc,
        runtime_facade=runtime_facade,
    )
    robot_workflow = RobotWorkflowService(
        registry=bundle.registries.robot_registry,
        controller=robot_controller,
        importer_registry=bundle.registries.importer_registry,
    )
    motion_workflow = MotionWorkflowService(
        solver_settings=solver_settings,
        ik_controller=ik_controller,
        trajectory_controller=trajectory_controller,
        benchmark_controller=benchmark_controller,
        playback_controller=playback_controller,
        playback_service=bundle.services.playback_service,
        ik_use_case=bundle.use_cases.ik_uc,
        trajectory_use_case=bundle.use_cases.traj_uc,
        benchmark_use_case=bundle.use_cases.benchmark_uc,
    )
    export_workflow = ExportWorkflowService(export_controller=export_controller)

    return PresentationControllerCollaborators(
        state_store=state_store,
        diagnostics_controller=diagnostics_controller,
        robot_controller=robot_controller,
        ik_controller=ik_controller,
        trajectory_controller=trajectory_controller,
        playback_controller=playback_controller,
        benchmark_controller=benchmark_controller,
        export_controller=export_controller,
        runtime_facade=runtime_facade,
        robot_facade=RobotFacade(robot_workflow),
        solver_facade=SolverFacade(motion_workflow),
        trajectory_facade=TrajectoryFacade(motion_workflow),
        playback_facade=PlaybackFacade(motion_workflow),
        benchmark_facade=BenchmarkFacade(motion_workflow),
        export_facade=ExportFacade(export_workflow),
        robot_workflow=robot_workflow,
        motion_workflow=motion_workflow,
        export_workflow=export_workflow,
    )



def install_main_controller_collaborators(controller: object, collaborators: PresentationControllerCollaborators) -> None:
    controller.state_store = collaborators.state_store
    controller.diagnostics_controller = collaborators.diagnostics_controller
    controller.robot_controller = collaborators.robot_controller
    controller.ik_controller = collaborators.ik_controller
    controller.trajectory_controller = collaborators.trajectory_controller
    controller.playback_controller = collaborators.playback_controller
    controller.benchmark_controller = collaborators.benchmark_controller
    controller.export_controller = collaborators.export_controller
    controller.runtime_facade = collaborators.runtime_facade
    controller.robot_facade = collaborators.robot_facade
    controller.solver_facade = collaborators.solver_facade
    controller.trajectory_facade = collaborators.trajectory_facade
    controller.playback_facade = collaborators.playback_facade
    controller.benchmark_facade = collaborators.benchmark_facade
    controller.export_facade = collaborators.export_facade
    controller.robot_workflow = collaborators.robot_workflow
    controller.motion_workflow = collaborators.motion_workflow
    controller.export_workflow = collaborators.export_workflow
