from __future__ import annotations

from pathlib import Path

from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.state_store import StateStore


def test_robot_controller_loads_robot(project_root):
    from robot_sim.app.container import build_container

    state = StateStore(SessionState())
    registry = RobotRegistry(project_root / 'configs' / 'robots')
    container = build_container(project_root)
    controller = RobotController(state, registry, RunFKUseCase(), application_workflow=container.workflow_facade)
    fk = controller.load_robot('planar_2dof')
    assert state.state.robot_spec is not None
    assert fk.ee_pose.p.shape == (3,)


def test_robot_controller_prefers_application_workflow_import_path(tmp_path):
    from robot_sim.app.container import build_container

    project_root = Path(__file__).resolve().parents[2]
    container = build_container(project_root)
    registry = RobotRegistry(tmp_path)
    state = StateStore()
    controller = RobotController(
        state,
        registry,
        container.fk_uc,
        import_robot_uc=container.import_robot_uc,
        application_workflow=container.workflow_facade,
    )
    source = project_root / 'configs' / 'robots' / 'planar_2dof.yaml'
    result = controller.import_robot(str(source), importer_id='yaml', persist=False)
    assert result.staged_only is True
    assert state.state.robot_spec is not None
    assert state.state.robot_spec.name == result.suggested_name
