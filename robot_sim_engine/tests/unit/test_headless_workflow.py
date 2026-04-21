from __future__ import annotations

import numpy as np

from robot_sim.app.container import build_container
from robot_sim.app.headless_api import HeadlessWorkflowService


def test_headless_workflow_fk_contract(project_root) -> None:
    container = build_container(project_root)
    service = HeadlessWorkflowService(container)
    payload = service.execute('fk', {'robot': 'planar_2dof', 'q': [0.0, 0.0]})
    assert payload['robot']['name'] == 'planar_2dof'
    assert payload['metadata']['execution_semantics'] == 'serial_tree'
    np.testing.assert_allclose(np.asarray(payload['ee_pose']['position'], dtype=float), np.array([2.0, 0.0, 0.0], dtype=float), atol=1.0e-9)


def test_headless_workflow_plan_contract(project_root) -> None:
    container = build_container(project_root)
    service = HeadlessWorkflowService(container)
    payload = service.execute('plan', {'robot': 'planar_2dof', 'q_start': [0.0, 0.0], 'q_goal': [0.2, -0.1], 'duration': 1.0, 'dt': 0.1})
    assert len(payload['t']) > 0
    assert payload['metadata']['planner_id']
    assert len(payload['q'][0]) == 2



def test_headless_workflow_uses_profile_default_pipeline(project_root, monkeypatch) -> None:
    monkeypatch.setenv('ROBOT_SIM_PROFILE', 'research')
    container = build_container(project_root)
    service = HeadlessWorkflowService(container)
    payload = service.execute('plan', {'robot': 'planar_2dof', 'q_start': [0.0, 0.0], 'q_goal': [0.2, -0.1], 'duration': 1.0, 'dt': 0.1})
    assert payload['metadata']['pipeline_id'] == 'research_fast_path'
    assert payload['metadata']['retimer_id'] == 'no_retime'
    assert payload['metadata']['validation_stage'] == 'validate_goal_only'
