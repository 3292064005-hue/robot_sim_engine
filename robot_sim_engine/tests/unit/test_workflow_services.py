from __future__ import annotations

import numpy as np

from robot_sim.app.container import build_container
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.runtime_projection_service import RuntimeProjectionService
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.workflow_services import ExportWorkflowService, MotionWorkflowService, RobotWorkflowService


def _build_robot_workflow(project_root):
    container = build_container(project_root)
    state_store = StateStore(SessionState())
    runtime_projection = RuntimeProjectionService(state_store, container.fk_uc)
    workflow = RobotWorkflowService(
        registry=container.robot_registry,
        fk_uc=container.fk_uc,
        state_store=state_store,
        runtime_projection_service=runtime_projection,
        importer_registry=container.importer_registry,
        import_robot_uc=container.import_robot_uc,
        application_workflow=container.workflow_facade,
    )
    return container, state_store, workflow


def _build_motion_workflow(container, state_store):
    return MotionWorkflowService(
        solver_settings=container.config_service.load_solver_settings(),
        state_store=state_store,
        fk_uc=container.fk_uc,
        ik_use_case=container.ik_uc,
        trajectory_use_case=container.traj_uc,
        benchmark_use_case=container.benchmark_uc,
        playback_service=container.playback_service,
        playback_use_case=container.playback_uc,
        application_workflow=container.workflow_facade,
    )


def test_robot_workflow_load_import_and_fk(project_root):
    container, state_store, workflow = _build_robot_workflow(project_root)
    assert 'planar_2dof' in workflow.robot_names()
    assert workflow.importer_entries()

    fk = workflow.load_robot('planar_2dof')
    assert state_store.state.robot_spec is not None
    np.testing.assert_allclose(np.asarray(fk.ee_pose.p, dtype=float), np.array([2.0, 0.0, 0.0], dtype=float), atol=1.0e-9)

    imported = workflow.import_robot(str(project_root / 'configs' / 'robots' / 'planar_2dof.yaml'), importer_id='yaml')
    assert imported.persisted_path is None
    assert imported.staged_only is True
    assert state_store.state.robot_spec is not None
    assert state_store.state.robot_spec.name == imported.spec.name

    fk_after = workflow.run_fk([0.0, 0.0])
    np.testing.assert_allclose(np.asarray(fk_after.ee_pose.p, dtype=float), np.array([2.0, 0.0, 0.0], dtype=float), atol=1.0e-9)
    persisted_path = workflow.save_current_robot()
    assert persisted_path.exists()
    assert container.robot_registry.exists(persisted_path.stem)


def test_motion_workflow_plans_playback_and_benchmark(project_root):
    container, state_store, robot_workflow = _build_robot_workflow(project_root)
    robot_workflow.load_robot('planar_2dof')
    workflow = _build_motion_workflow(container, state_store)

    target = workflow.build_target_pose([1.5, 0.0, 0.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(np.asarray(target.p, dtype=float), np.array([1.5, 0.0, 0.0], dtype=float), atol=1.0e-9)

    traj = workflow.plan_trajectory(q_goal=[0.2, -0.1], duration=1.0, dt=0.1)
    assert traj.q.shape[1] == 2
    frame = workflow.current_playback_frame()
    assert frame is not None
    workflow.set_playback_options(speed_multiplier=2.0, loop_enabled=True)
    assert state_store.state.playback.speed_multiplier == 2.0
    report = workflow.run_benchmark(workflow.build_benchmark_config())
    assert report.num_cases > 0
    assert state_store.state.benchmark_report is not None


def test_export_workflow_exports_session_and_package(project_root):
    container, state_store, robot_workflow = _build_robot_workflow(project_root)
    robot_workflow.load_robot('planar_2dof')
    motion_workflow = _build_motion_workflow(container, state_store)
    motion_workflow.plan_trajectory(q_goal=[0.2, -0.1], duration=1.0, dt=0.1)
    motion_workflow.run_benchmark(motion_workflow.build_benchmark_config())

    workflow = ExportWorkflowService(
        state_store=state_store,
        exporter=container.export_service,
        export_report_use_case=container.export_report_uc,
        save_session_use_case=container.save_session_uc,
        export_package_use_case=container.export_package_uc,
        runtime_facade=None,
        application_workflow=container.workflow_facade,
    )
    session_path = workflow.export_session('workflow_session.json', telemetry_detail='minimal')
    package_path = workflow.export_package('workflow_bundle.zip', telemetry_detail='minimal')
    assert session_path.exists()
    assert package_path.exists()



def test_runtime_projection_service_invalidates_cached_assets_before_reload(project_root):
    container = build_container(project_root)
    state_store = StateStore(SessionState())
    runtime_projection = RuntimeProjectionService(state_store, container.fk_uc, runtime_asset_service=container.runtime_asset_service)
    spec = container.robot_registry.load('planar_2dof')
    container.runtime_asset_service.build_assets(spec)
    before = container.runtime_asset_service.cache_stats()
    runtime_projection.load_robot_spec(spec)
    after = container.runtime_asset_service.cache_stats()
    assert before['entries'] == 1
    assert after['entries'] == 1
    assert after['invalidations'] >= before['invalidations'] + 1
    assert container.runtime_asset_service.invalidation_log()[-1].reason == 'runtime_projection_reload'


def test_robot_workflow_save_current_robot_keeps_relative_source_paths(project_root):
    import yaml

    container, state_store, workflow = _build_robot_workflow(project_root)
    workflow.load_robot('planar_2dof')

    persisted_path = workflow.save_current_robot(name='planar_saved_contract_check')
    payload = yaml.safe_load(persisted_path.read_text(encoding='utf-8')) or {}

    imported_package = dict(payload.get('imported_package') or {})
    assert imported_package.get('source_path') == 'configs/robots/planar_2dof.yaml'

    # cleanup to keep repository tree stable during tests
    persisted_path.unlink()


def test_legacy_controller_compatibility_package_exports_frozen_surface() -> None:
    from robot_sim.presentation.controllers.compatibility import LEGACY_CONTROLLER_IDS

    assert LEGACY_CONTROLLER_IDS == (
        'IKController',
        'TrajectoryController',
        'BenchmarkController',
        'ExportController',
    )
