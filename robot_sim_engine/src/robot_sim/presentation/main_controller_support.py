from __future__ import annotations

from dataclasses import dataclass

from robot_sim.app.contracts import PresentationBootstrapBundle
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.application.services.render_runtime_advisor import RenderAdviceThresholds, RenderRuntimeAdvisor
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.diagnostics_controller import DiagnosticsController
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.facades import RuntimeFacade
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.workflow_services import ExportWorkflowService, MotionWorkflowService, RobotWorkflowService


@dataclass(frozen=True)
class PresentationControllerCollaborators:
    """Canonical presentation collaborators installed on ``MainController``.

    Legacy controller wrappers are intentionally excluded from the active startup surface.
    They remain in-repo only for compatibility tests and narrow downstream adapters.
    """

    state_store: StateStore
    diagnostics_controller: DiagnosticsController
    runtime_facade: RuntimeFacade
    robot_workflow: RobotWorkflowService
    motion_workflow: MotionWorkflowService
    export_workflow: ExportWorkflowService



def build_presentation_collaborators(bundle: PresentationBootstrapBundle) -> PresentationControllerCollaborators:
    app_settings = bundle.services.config_service.load_app_settings()
    state_store = StateStore(
        SessionState(),
        render_runtime_advisor=RenderRuntimeAdvisor(
            RenderAdviceThresholds(**app_settings.render.advice.as_dict())
        ),
    )
    capability_matrix = bundle.services.capability_service.build_matrix(
        solver_registry=bundle.registries.solver_registry,
        planner_registry=bundle.registries.planner_registry,
        importer_registry=bundle.registries.importer_registry,
    )
    state_store.patch_capabilities(capability_matrix)
    state_store.session.patch_module_statuses(bundle.services.module_status_service.snapshot_details())
    diagnostics_controller = DiagnosticsController(state_store, bundle.services.metrics_service)
    runtime_asset_service = bundle.services.runtime_asset_service or RobotRuntimeAssetService(
        experimental_collision_backends_enabled=bool(getattr(bundle.services.runtime_feature_policy, 'experimental_backends_enabled', False))
    )
    if bundle.services.runtime_asset_service is None:
        runtime_asset_service.bind_runtime_context(
            profile_id=str(getattr(bundle.services.config_service, 'profile', 'default') or 'default'),
            collision_backend_scope='experimental' if bool(getattr(bundle.services.runtime_feature_policy, 'experimental_backends_enabled', False)) else 'stable',
            experimental_collision_backends_enabled=bool(getattr(bundle.services.runtime_feature_policy, 'experimental_backends_enabled', False)),
        )
    solver_settings = bundle.services.config_service.load_solver_settings()
    runtime_paths = bundle.services.runtime_paths
    resource_root = bundle.project_root if runtime_paths is None else runtime_paths.resource_root
    config_root = bundle.project_root / 'configs' if runtime_paths is None else runtime_paths.config_root
    export_root = bundle.project_root / 'exports' if runtime_paths is None else runtime_paths.export_root
    runtime_facade = RuntimeFacade(
        project_root=bundle.project_root,
        resource_root=resource_root,
        config_root=config_root,
        export_root=export_root,
        app_config=app_settings.as_dict(),
        app_settings=app_settings,
        solver_config=solver_settings.as_dict(),
        solver_settings=solver_settings,
        runtime_context=bundle.services.runtime_context,
        startup_summary=bundle.services.startup_summary,
        effective_config_snapshot=bundle.services.config_service.describe_effective_snapshot(),
        state_store=state_store,
        metrics_service=bundle.services.metrics_service,
        task_error_mapper=bundle.services.task_error_mapper,
        capability_service=bundle.services.capability_service,
        module_status_service=bundle.services.module_status_service,
    )
    editor_controller = RobotController(
        state_store,
        bundle.registries.robot_registry,
        bundle.use_cases.fk_uc,
        import_robot_uc=bundle.use_cases.import_robot_uc,
        runtime_asset_service=runtime_asset_service,
        application_workflow=bundle.services.workflow_facade,
    )
    robot_workflow = RobotWorkflowService(
        registry=bundle.registries.robot_registry,
        fk_uc=bundle.use_cases.fk_uc,
        state_store=state_store,
        runtime_projection_service=editor_controller._runtime_projection_service,
        importer_registry=bundle.registries.importer_registry,
        import_robot_uc=bundle.use_cases.import_robot_uc,
        editor_controller=editor_controller,
        application_workflow=bundle.services.workflow_facade,
    )
    motion_workflow = MotionWorkflowService(
        solver_settings=solver_settings,
        state_store=state_store,
        fk_uc=bundle.use_cases.fk_uc,
        ik_use_case=bundle.use_cases.ik_uc,
        trajectory_use_case=bundle.use_cases.traj_uc,
        benchmark_use_case=bundle.use_cases.benchmark_uc,
        playback_service=bundle.services.playback_service,
        playback_use_case=bundle.use_cases.playback_uc,
        runtime_asset_service=runtime_asset_service,
        application_workflow=bundle.services.workflow_facade,
    )
    export_workflow = ExportWorkflowService(
        state_store=state_store,
        exporter=bundle.services.export_service,
        export_report_use_case=bundle.use_cases.export_report_uc,
        save_session_use_case=bundle.use_cases.save_session_uc,
        export_package_use_case=bundle.use_cases.export_package_uc,
        runtime_facade=runtime_facade,
        application_workflow=bundle.services.workflow_facade,
    )

    return PresentationControllerCollaborators(
        state_store=state_store,
        diagnostics_controller=diagnostics_controller,
        runtime_facade=runtime_facade,
        robot_workflow=robot_workflow,
        motion_workflow=motion_workflow,
        export_workflow=export_workflow,
    )



def install_main_controller_collaborators(controller: object, collaborators: PresentationControllerCollaborators) -> None:
    controller.state_store = collaborators.state_store
    controller.diagnostics_controller = collaborators.diagnostics_controller
    controller.runtime_facade = collaborators.runtime_facade
    controller.robot_workflow = collaborators.robot_workflow
    controller.motion_workflow = collaborators.motion_workflow
    controller.export_workflow = collaborators.export_workflow
