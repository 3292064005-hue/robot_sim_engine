from __future__ import annotations

import numpy as np

from robot_sim.app.container import build_container
from robot_sim.app.headless_api import HeadlessWorkflowService
from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.model.session_state import SessionState
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.presentation.runtime_projection_service import RuntimeProjectionService
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.workflow_services import MotionWorkflowService


def _trajectory_from_kwargs(q_start, q_goal, duration: float) -> JointTrajectory:
    goal = np.asarray(q_start if q_goal is None else q_goal, dtype=float)
    q = np.vstack([np.asarray(q_start, dtype=float), goal])
    return JointTrajectory(
        t=np.array([0.0, float(duration)], dtype=float),
        q=q,
        qd=np.zeros_like(q),
        qdd=np.zeros_like(q),
        metadata={'planner_id': 'contract_capture', 'cache_status': 'none'},
        feasibility={'feasible': True, 'reasons': ()},
        quality={},
    )


def _scene_with_obstacle(base_scene, object_id: str = 'contract_box'):
    service = SceneAuthorityService()
    scene = service.ensure_scene(
        base_scene,
        scene_summary={} if base_scene is None else base_scene.summary(),
        authority='test_scene_contract',
        edit_surface='unit_test',
    )
    return service.execute_obstacle_edit(
        scene,
        SceneObstacleEdit(
            object_id=object_id,
            center=(0.4, 0.0, 0.0),
            size=(0.1, 0.1, 0.1),
            replace_existing=True,
        ),
        source='unit_test',
    ).scene


class _CapturingWorkflow:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    def plan_trajectory(self, spec, **kwargs):
        self.kwargs = dict(kwargs)
        return _trajectory_from_kwargs(kwargs['q_start'], kwargs['q_goal'], float(kwargs['duration']))


def _motion_workflow(container, state_store, application_workflow):
    return MotionWorkflowService(
        solver_settings=container.config_service.load_solver_settings(),
        state_store=state_store,
        fk_uc=container.fk_uc,
        ik_use_case=container.ik_uc,
        trajectory_use_case=container.traj_uc,
        benchmark_use_case=container.benchmark_uc,
        playback_service=container.playback_service,
        playback_use_case=container.playback_uc,
        application_workflow=application_workflow,
    )


def test_gui_motion_workflow_forwards_session_planning_scene(project_root):
    container = build_container(project_root)
    state_store = StateStore(SessionState())
    runtime_projection = RuntimeProjectionService(state_store, container.fk_uc, runtime_asset_service=container.runtime_asset_service)
    runtime_projection.load_robot_spec(container.robot_registry.load('planar_2dof'))
    scene = _scene_with_obstacle(state_store.state.planning_scene)
    state_store.patch_scene(scene.summary(), planning_scene=scene, scene_revision=scene.revision)

    capturing = _CapturingWorkflow()
    workflow = _motion_workflow(container, state_store, capturing)

    workflow.plan_trajectory(q_goal=[0.2, -0.1], duration=1.0, dt=0.1)

    assert capturing.kwargs['planning_scene'] is scene
    assert 'contract_box' in capturing.kwargs['planning_scene'].obstacle_ids


def test_headless_plan_scene_payload_reaches_application_request(project_root):
    container = build_container(project_root)
    captured: dict[str, object] = {}

    def _capture(req):
        captured['request'] = req
        return _trajectory_from_kwargs(req.q_start, req.q_goal, req.duration)

    container.traj_uc.execute = _capture
    service = HeadlessWorkflowService(container)
    service.execute(
        'plan',
        {
            'robot': 'planar_2dof',
            'q_start': [0.0, 0.0],
            'q_goal': [0.2, -0.1],
            'duration': 1.0,
            'dt': 0.1,
            'planning_scene': {
                'obstacles': [
                    {
                        'object_id': 'headless_box',
                        'center': [0.5, 0.0, 0.0],
                        'size': [0.1, 0.1, 0.1],
                        'replace_existing': True,
                    }
                ]
            },
        },
    )

    request = captured['request']
    assert request.planning_scene_source == 'caller_scene'
    assert 'headless_box' in request.planning_scene.obstacle_ids


def test_session_projection_prefers_caller_scene_truth(project_root):
    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline_scene = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene
    scene = _scene_with_obstacle(baseline_scene, object_id='session_box')

    state = container.workflow_facade.build_session_state(
        spec,
        q_current=spec.home_q,
        planning_scene=scene,
    )

    assert state.planning_scene is scene
    assert state.scene_summary['planning_scene_source'] == 'caller_scene'
    assert state.scene_summary['scene_truth_layer'] == 'session_planning_scene'
    assert state.scene_summary['materialization_source'] == 'caller_supplied_scene'
    assert str(state.scene_summary['scene_materialization_revision_key']).startswith('caller_scene:rev:')
    assert 'session_box' in state.planning_scene.obstacle_ids


def test_headless_scene_diff_non_mapping_fails_closed(project_root):
    import pytest

    from robot_sim.app.headless_scene_adapter import build_planning_scene_from_payload

    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene

    with pytest.raises(ValueError, match='scene_diff payload must be a mapping'):
        build_planning_scene_from_payload({'scene_diff': ['bad', 'payload']}, baseline_scene=baseline)


def test_headless_obstacle_aliases_are_normalized_and_unsupported_shapes_fail(project_root):
    import pytest

    from robot_sim.app.headless_scene_adapter import build_planning_scene_from_payload

    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene

    scene = build_planning_scene_from_payload(
        {
            'obstacles': [
                {
                    'id': 'alias_box',
                    'kind': 'box',
                    'position': [0.25, 0.0, 0.0],
                    'dimensions': [0.1, 0.2, 0.3],
                }
            ]
        },
        baseline_scene=baseline,
    )
    assert scene is not None
    assert 'alias_box' in scene.obstacle_ids

    with pytest.raises(ValueError, match='unsupported scene obstacle shape: mesh'):
        build_planning_scene_from_payload(
            {
                'obstacles': [
                    {
                        'id': 'unsupported_mesh',
                        'kind': 'mesh',
                        'position': [0.0, 0.0, 0.0],
                        'dimensions': [1.0, 1.0, 1.0],
                    }
                ]
            },
            baseline_scene=baseline,
        )


def test_validation_capability_schema_uses_required_keys(project_root):
    from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase

    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene
    trajectory = _trajectory_from_kwargs(spec.home_q, spec.q_mid(), 1.0)

    report = ValidateTrajectoryUseCase().execute(
        trajectory,
        spec=spec,
        q_goal=spec.q_mid(),
        planning_scene=baseline,
        planning_scene_source='caller_scene',
        validation_layers=('timing', 'limits', 'collision', 'goal_metrics', 'path_metrics'),
    )

    capabilities = report.metadata['validation_capabilities']
    for key in (
        'joint_limits',
        'goal_validation',
        'collision_broad_phase',
        'continuous_collision',
        'mesh_collision',
        'attached_object_validation',
        'allowed_collision_matrix',
        'scene_validation_mode',
        'scene_validation_precision',
    ):
        assert key in capabilities
    assert capabilities['goal_validation'] is True
    assert capabilities['collision_broad_phase'] is True


def test_headless_full_snapshot_replays_exported_obstacle_records(project_root):
    from robot_sim.app.headless_scene_adapter import build_planning_scene_from_payload

    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene
    exported_scene = _scene_with_obstacle(baseline, object_id='snapshot_box')

    replayed = build_planning_scene_from_payload(exported_scene.summary(), baseline_scene=baseline)

    assert replayed is not None
    assert 'snapshot_box' in replayed.obstacle_ids
    assert replayed.metadata['planning_scene_source'] == 'caller_scene'


def test_headless_unknown_or_diagnostic_only_scene_payload_fails_closed(project_root):
    import pytest

    from robot_sim.app.headless_scene_adapter import build_planning_scene_from_payload

    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene

    with pytest.raises(ValueError, match='not replayable'):
        build_planning_scene_from_payload({'obstacle_ids': ['missing_geometry']}, baseline_scene=baseline)

    with pytest.raises(ValueError, match='no supported scene fields'):
        build_planning_scene_from_payload({'unsupported_field': 'value'}, baseline_scene=baseline)

    with pytest.raises(ValueError, match='replayable scene fields'):
        build_planning_scene_from_payload({}, baseline_scene=baseline)


def test_headless_malformed_allowed_collision_pairs_fail_closed(project_root):
    import pytest

    from robot_sim.app.headless_scene_adapter import build_planning_scene_from_payload

    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene

    with pytest.raises(ValueError, match='allowed_collision_pairs entries must'):
        build_planning_scene_from_payload({'allowed_collision_pairs': [1]}, baseline_scene=baseline)


def test_runtime_asset_cache_partitions_by_scene_materialization_revision(project_root):
    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    service = container.workflow_facade.runtime_asset_service

    service.invalidate(reason='unit_test_cache_partition')
    service.build_assets(spec)
    assert service.cache_stats()['entries'] == 1

    service.build_assets(spec, scene_materialization_revision_key='caller_scene:rev:1')
    assert service.cache_stats()['entries'] == 2

    service.build_assets(spec, scene_materialization_revision_key='caller_scene:rev:1')
    assert service.cache_stats()['entries'] == 2

    service.build_assets(spec, scene_materialization_revision_key='caller_scene:rev:2')
    assert service.cache_stats()['entries'] == 3


def test_scene_session_revision_key_hashes_scene_content(project_root):
    from robot_sim.application.services.scene_session_authority import SceneSessionAuthority

    container = build_container(project_root)
    spec = container.robot_registry.load('planar_2dof')
    baseline = container.workflow_facade.runtime_asset_service.build_assets(spec).planning_scene
    scene_a = _scene_with_obstacle(baseline, object_id='same_rev_box_a')
    scene_b = _scene_with_obstacle(baseline, object_id='same_rev_box_b')

    assert scene_a.revision == scene_b.revision
    key_a = SceneSessionAuthority.revision_key(scene_a, source='caller_scene')
    key_b = SceneSessionAuthority.revision_key(scene_b, source='caller_scene')

    assert key_a != key_b
    assert ':hash:' in key_a
    assert ':hash:' in key_b

    service = container.workflow_facade.runtime_asset_service
    service.invalidate(reason='unit_test_scene_content_hash_partition')
    service.build_assets(spec, scene_materialization_revision_key=key_a)
    service.build_assets(spec, scene_materialization_revision_key=key_a)
    assert service.cache_stats()['entries'] == 1
    service.build_assets(spec, scene_materialization_revision_key=key_b)
    assert service.cache_stats()['entries'] == 2


def test_false_headless_scene_control_flags_are_absent_payloads():
    from robot_sim.app.headless_scene_adapter import build_scene_payload_from_request, request_has_scene_payload

    request = {
        'robot': 'planar_2dof',
        'q_goal': [0.1, 0.2],
        'clear_obstacles': False,
        'reset_obstacles': False,
        'clear_allowed_collision_pairs': False,
    }

    assert request_has_scene_payload(request) is False
    assert build_scene_payload_from_request(request) is None
