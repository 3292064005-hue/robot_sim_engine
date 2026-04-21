from __future__ import annotations

import numpy as np

from robot_sim.app.container import build_container
from robot_sim.app.headless_api import HeadlessWorkflowService
from robot_sim.model.session_state import SessionState
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.controllers.trajectory_controller import TrajectoryController
from robot_sim.presentation.runtime_projection_service import RuntimeProjectionService
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.workflow_services import MotionWorkflowService, RobotWorkflowService


def _build_robot_workflow(project_root):
    container = build_container(project_root)
    state_store = StateStore(SessionState())
    runtime_projection = RuntimeProjectionService(state_store, container.fk_uc)
    editor_controller = RobotController(
        state_store,
        container.robot_registry,
        container.fk_uc,
        import_robot_uc=container.import_robot_uc,
        runtime_projection_service=runtime_projection,
        runtime_asset_service=container.runtime_asset_service,
        application_workflow=container.workflow_facade,
    )
    workflow = RobotWorkflowService(
        registry=container.robot_registry,
        fk_uc=container.fk_uc,
        state_store=state_store,
        runtime_projection_service=runtime_projection,
        importer_registry=container.importer_registry,
        import_robot_uc=container.import_robot_uc,
        editor_controller=editor_controller,
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


def _fake_trajectory_from_request(req) -> JointTrajectory:
    q_goal = req.q_start if req.q_goal is None else np.asarray(req.q_goal, dtype=float)
    q = np.vstack([np.asarray(req.q_start, dtype=float), q_goal])
    qd = np.zeros_like(q)
    qdd = np.zeros_like(q)
    return JointTrajectory(
        t=np.array([0.0, float(req.duration)], dtype=float),
        q=q,
        qd=qd,
        qdd=qdd,
        metadata={
            'planner_id': req.planner_id or 'captured_planner',
            'pipeline_id': req.pipeline_id or 'default',
            'retimer_id': 'captured_retimer',
            'validation_stage': 'captured_validation',
            'execution_graph': None if req.execution_graph is None else req.execution_graph.summary(),
        },
        feasibility={'feasible': True, 'reasons': ()},
        quality={},
    )


def test_motion_workflow_uses_profile_default_pipeline(project_root, monkeypatch):
    monkeypatch.setenv('ROBOT_SIM_PROFILE', 'research')
    container, state_store, robot_workflow = _build_robot_workflow(project_root)
    robot_workflow.load_robot('planar_2dof')
    workflow = _build_motion_workflow(container, state_store)

    req = workflow.build_trajectory_request(q_goal=[0.2, -0.1], duration=1.0, dt=0.1)

    assert req.pipeline_id == 'research_fast_path'
    assert req.execution_graph is not None
    assert req.execution_graph.summary()['strategy'] == 'active_path_over_tree'


def test_motion_workflow_threads_pipeline_and_execution_graph(project_root):
    container, state_store, robot_workflow = _build_robot_workflow(project_root)
    robot_workflow.load_robot('planar_2dof')
    workflow = _build_motion_workflow(container, state_store)
    spec = state_store.state.robot_spec
    assert spec is not None

    descriptor_payload = {
        'descriptor_id': 'gui_subset',
        'active_joint_names': list(spec.runtime_joint_names),
        'target_links': [spec.runtime_link_names[-1]],
        'metadata': {'caller': 'gui_contract_test'},
    }
    req = workflow.build_trajectory_request(
        q_goal=[0.2, -0.1],
        duration=1.0,
        dt=0.1,
        planner_id='joint_trapezoidal',
        pipeline_id='default',
        execution_graph=descriptor_payload,
        validation_layers=['timing', 'goal'],
    )

    assert req.pipeline_id == 'default'
    assert req.planner_id == 'joint_trapezoidal'
    assert req.validation_layers == ('timing', 'goal')
    assert req.execution_graph is not None
    assert req.execution_graph.descriptor_id == 'gui_subset'
    assert req.execution_graph.metadata['caller'] == 'gui_contract_test'



def test_motion_workflow_matches_headless_request_contract(project_root):
    container = build_container(project_root)
    captured: dict[str, object] = {}

    def _capture(req):
        captured['request'] = req
        return _fake_trajectory_from_request(req)

    container.traj_uc.execute = _capture
    headless = HeadlessWorkflowService(container)
    spec = container.robot_registry.load('planar_2dof')
    descriptor_payload = {
        'descriptor_id': 'shared_subset',
        'active_joint_names': list(spec.runtime_joint_names),
        'target_links': [spec.runtime_link_names[-1]],
        'metadata': {'caller': 'shared_contract_test'},
    }
    payload = {
        'robot': 'planar_2dof',
        'q_start': [0.0, 0.0],
        'q_goal': [0.2, -0.1],
        'duration': 1.0,
        'dt': 0.1,
        'planner_id': 'joint_trapezoidal',
        'pipeline_id': 'default',
        'validation_layers': ['timing', 'goal'],
        'execution_graph': descriptor_payload,
    }
    headless.execute('plan', payload)
    headless_request = captured['request']

    _, state_store, robot_workflow = _build_robot_workflow(project_root)
    robot_workflow.load_robot('planar_2dof')
    workflow = _build_motion_workflow(container, state_store)
    gui_request = workflow.build_trajectory_request(**{k: v for k, v in payload.items() if k != 'robot' and k != 'q_start'})

    np.testing.assert_allclose(np.asarray(gui_request.q_start, dtype=float), np.asarray(headless_request.q_start, dtype=float), atol=1.0e-9)
    np.testing.assert_allclose(np.asarray(gui_request.q_goal, dtype=float), np.asarray(headless_request.q_goal, dtype=float), atol=1.0e-9)
    assert gui_request.pipeline_id == headless_request.pipeline_id
    assert gui_request.planner_id == headless_request.planner_id
    assert gui_request.validation_layers == headless_request.validation_layers
    assert gui_request.execution_graph.summary() == headless_request.execution_graph.summary()



def test_trajectory_controller_matches_motion_workflow_profile_defaults(project_root, monkeypatch):
    monkeypatch.setenv('ROBOT_SIM_PROFILE', 'research')
    container, state_store, robot_workflow = _build_robot_workflow(project_root)
    robot_workflow.load_robot('planar_2dof')
    workflow = _build_motion_workflow(container, state_store)
    controller = TrajectoryController.from_solver_settings(
        state_store,
        container.traj_uc,
        container.playback_service,
        workflow.build_ik_request,
        container.config_service.load_solver_settings(),
    )

    workflow_request = workflow.build_trajectory_request(q_goal=[0.2, -0.1])
    controller_request = controller.build_trajectory_request(q_goal=[0.2, -0.1])

    assert controller_request.duration == workflow_request.duration
    assert controller_request.dt == workflow_request.dt
    assert controller_request.pipeline_id == workflow_request.pipeline_id


def test_trajectory_controller_matches_motion_workflow_contract(project_root):
    container, state_store, robot_workflow = _build_robot_workflow(project_root)
    robot_workflow.load_robot('planar_2dof')
    workflow = _build_motion_workflow(container, state_store)
    controller = TrajectoryController.from_solver_settings(
        state_store,
        container.traj_uc,
        container.playback_service,
        workflow.build_ik_request,
        container.config_service.load_solver_settings(),
    )
    spec = state_store.state.robot_spec
    assert spec is not None
    payload = {
        'q_goal': [0.2, -0.1],
        'duration': 1.0,
        'dt': 0.1,
        'planner_id': 'joint_trapezoidal',
        'pipeline_id': 'default',
        'validation_layers': ['timing', 'goal'],
        'execution_graph': {
            'descriptor_id': 'compat_subset',
            'active_joint_names': list(spec.runtime_joint_names),
            'target_links': [spec.runtime_link_names[-1]],
        },
    }

    workflow_request = workflow.build_trajectory_request(**payload)
    controller_request = controller.build_trajectory_request(**payload)

    np.testing.assert_allclose(np.asarray(workflow_request.q_start, dtype=float), np.asarray(controller_request.q_start, dtype=float), atol=1.0e-9)
    np.testing.assert_allclose(np.asarray(workflow_request.q_goal, dtype=float), np.asarray(controller_request.q_goal, dtype=float), atol=1.0e-9)
    assert workflow_request.pipeline_id == controller_request.pipeline_id
    assert workflow_request.planner_id == controller_request.planner_id
    assert workflow_request.validation_layers == controller_request.validation_layers
    assert workflow_request.execution_graph.summary() == controller_request.execution_graph.summary()
