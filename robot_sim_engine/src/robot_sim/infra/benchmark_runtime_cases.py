from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from robot_sim.app.container import build_container
from robot_sim.app.headless_api import HeadlessWorkflowService
from robot_sim.application.request_builders import build_execution_graph_descriptor
from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.domain.enums import TrajectoryMode
from robot_sim.model.solver_config import IKConfig


@dataclass(frozen=True)
class BenchmarkRuntimeCaseResult:
    """Structured result emitted by one runtime benchmark harness scenario."""

    case_id: str
    ok: bool
    summary: dict[str, object]


@dataclass(frozen=True)
class BenchmarkRuntimeCase:
    """Executable runtime benchmark scenario used by the matrix harness."""

    case_id: str
    description: str
    execution_environment: str
    runner: callable


class BenchmarkRuntimeCaseCatalog:
    """Registry of runtime benchmark scenarios consumed by the harness.

    Each runtime case exercises importer/scene/planner/capture behavior directly through the
    shipped runtime services instead of proxying through pytest selectors. The case identifiers stored
    in ``configs/benchmark_matrix.yaml`` therefore remain stable semantic runtime case ids.
    """

    def __init__(self) -> None:
        self._cases: dict[str, BenchmarkRuntimeCase] = {
            'runtime_case:yaml_like.clean_scene.ik_planar_smoke.snapshot_capture': BenchmarkRuntimeCase(
                case_id='runtime_case:yaml_like.clean_scene.ik_planar_smoke.snapshot_capture',
                description='Import shipped YAML robot, solve IK, run benchmark suite, and export a session snapshot.',
                execution_environment='headless',
                runner=_run_yaml_clean_ik_snapshot_case,
            ),
            'runtime_case:urdf_skeleton.obstacle_single_box.ik_planar_default_suite.snapshot_capture': BenchmarkRuntimeCase(
                case_id='runtime_case:urdf_skeleton.obstacle_single_box.ik_planar_default_suite.snapshot_capture',
                description='Import a URDF skeleton robot, seed a single-box planning scene, validate a trajectory, and export a session snapshot.',
                execution_environment='headless',
                runner=_run_urdf_skeleton_obstacle_case,
            ),
            'runtime_case:urdf_model.obstacle_dense.trajectory_plan_smoke.snapshot_capture': BenchmarkRuntimeCase(
                case_id='runtime_case:urdf_model.obstacle_dense.trajectory_plan_smoke.snapshot_capture',
                description='Import a URDF model robot, plan/validate a trajectory through a dense scene, and package trajectory/session artifacts.',
                execution_environment='headless',
                runner=_run_urdf_model_dense_trajectory_case,
            ),
            'runtime_case:gui_offscreen.urdf_model.clean_scene.live_capture_capability_probe': BenchmarkRuntimeCase(
                case_id='runtime_case:gui_offscreen.urdf_model.clean_scene.live_capture_capability_probe',
                description='Project URDF-model runtime data into the scene widget and verify live-capture/runtime snapshot contracts without pytest indirection.',
                execution_environment='gui',
                runner=_run_gui_render_contract_case,
            ),
        }

    def get(self, case_id: str) -> BenchmarkRuntimeCase | None:
        return self._cases.get(str(case_id))

    def require(self, case_id: str) -> BenchmarkRuntimeCase:
        case = self.get(case_id)
        if case is None:
            raise KeyError(f'unknown benchmark runtime case: {case_id}')
        return case

    def summary(self) -> dict[str, dict[str, object]]:
        return {
            case_id: {
                'description': case.description,
                'execution_environment': case.execution_environment,
            }
            for case_id, case in self._cases.items()
        }



def benchmark_runtime_case(case_id: str) -> BenchmarkRuntimeCase | None:
    return _RUNTIME_CASE_CATALOG.get(case_id)


def run_benchmark_runtime_case(case_id: str, *, repo_root: str | Path) -> BenchmarkRuntimeCaseResult:
    case = _RUNTIME_CASE_CATALOG.require(case_id)
    return case.runner(Path(repo_root).resolve())


def _build_runtime_container(repo_root: Path, *, export_root: Path):
    container = build_container(repo_root)
    export_root.mkdir(parents=True, exist_ok=True)
    container.service_bundle.export_service.export_dir = export_root
    container.service_bundle.package_service.export_dir = export_root
    return container


def _sample_serial_urdf(name: str) -> str:
    return (
        f'<robot name="{name}">\n'
        '  <link name="base"/>\n'
        '  <link name="l1"/>\n'
        '  <link name="l2"/>\n'
        '  <joint name="j1" type="revolute">\n'
        '    <parent link="base"/><child link="l1"/>\n'
        '    <origin xyz="0 0 0" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-3.14" upper="3.14"/>\n'
        '  </joint>\n'
        '  <joint name="j2" type="revolute">\n'
        '    <parent link="l1"/><child link="l2"/>\n'
        '    <origin xyz="1 0 0" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-3.14" upper="3.14"/>\n'
        '  </joint>\n'
        '</robot>\n'
    )


def _write_urdf(path: Path, *, name: str) -> Path:
    path.write_text(_sample_serial_urdf(name), encoding='utf-8')
    return path


def _runtime_assets(workflow, spec):
    return workflow.runtime_asset_service.build_assets(spec)


def _scene_with_obstacles(scene, obstacle_payloads: list[dict[str, object]]):
    authority = SceneAuthorityService()
    updated = authority.ensure_scene(scene, authority='benchmark_runtime_harness', scene_summary=scene.summary())
    for payload in obstacle_payloads:
        updated = authority.apply_obstacle_edit(updated, SceneObstacleEdit.from_mapping(payload), source='benchmark_runtime_harness')
    return updated


def _save_session_snapshot(container, *, name: str, state: SessionState) -> Path:
    bootstrap_bundle = container.bootstrap_bundle
    capability_snapshot = bootstrap_bundle.services.capability_matrix_service.build_matrix(
        solver_registry=bootstrap_bundle.registries.solver_registry,
        planner_registry=bootstrap_bundle.registries.planner_registry,
        importer_registry=bootstrap_bundle.registries.importer_registry,
    ).as_dict()
    return bootstrap_bundle.workflow_facade.export_session(
        name,
        state,
        environment=dict(bootstrap_bundle.services.runtime_context or {}),
        config_snapshot=bootstrap_bundle.services.config_service.describe_effective_snapshot(),
        capability_snapshot=capability_snapshot,
        telemetry_detail='minimal',
    )


def _run_yaml_clean_ik_snapshot_case(repo_root: Path) -> BenchmarkRuntimeCaseResult:
    with TemporaryDirectory(prefix='benchmark_case_yaml_', dir=str(repo_root)) as temp_dir:
        export_root = Path(temp_dir) / 'exports'
        container = _build_runtime_container(repo_root, export_root=export_root)
        workflow = HeadlessWorkflowService(container)
        source = repo_root / 'configs' / 'robots' / 'planar_2dof.yaml'
        imported = workflow.import_robot({'source': str(source), 'importer_id': 'yaml'})
        fk_payload = workflow.run_fk({'source': str(source), 'importer_id': 'yaml', 'q': [0.35, -0.25]})
        ik_payload = workflow.run_ik(
            {
                'source': str(source),
                'importer_id': 'yaml',
                'target': fk_payload['ee_pose'],
                'q0': [0.0, 0.0],
                'config': {'retry_count': 1, 'position_only': False},
            }
        )
        if not bool(ik_payload.get('success', False)):
            raise RuntimeError(f'IK smoke runtime case failed: {ik_payload.get("message", "unknown error")}')
        benchmark_payload = workflow.run_benchmark(
            {'source': str(source), 'importer_id': 'yaml', 'config': {'retry_count': 1, 'position_only': True}}
        )
        session_payload = workflow.export_session(
            {
                'source': str(source),
                'importer_id': 'yaml',
                'q_current': ik_payload['q_sol'],
                'name': 'yaml_clean_session.json',
                'telemetry_detail': 'minimal',
            }
        )
        session_path = Path(str(session_payload['path']))
        if not session_path.exists():
            raise RuntimeError(f'session snapshot was not written: {session_path}')
        return BenchmarkRuntimeCaseResult(
            case_id='runtime_case:yaml_like.clean_scene.ik_planar_smoke.snapshot_capture',
            ok=True,
            summary={
                'imported_package_present': bool(imported.get('imported_package_present', False)),
                'ik_success': bool(ik_payload.get('success', False)),
                'benchmark_cases': int(benchmark_payload.get('num_cases', 0)),
                'benchmark_success_rate': float(benchmark_payload.get('success_rate', 0.0)),
                'session_path': str(session_path),
            },
        )


def _run_urdf_skeleton_obstacle_case(repo_root: Path) -> BenchmarkRuntimeCaseResult:
    with TemporaryDirectory(prefix='benchmark_case_skeleton_', dir=str(repo_root)) as temp_dir:
        temp_root = Path(temp_dir)
        export_root = temp_root / 'exports'
        container = _build_runtime_container(repo_root, export_root=export_root)
        urdf_path = _write_urdf(temp_root / 'skeleton_case.urdf', name='skeleton_case')
        workflow = container.workflow_facade
        spec = workflow.resolve_import(urdf_path, importer_id='urdf_skeleton', persist=False).spec
        assets = _runtime_assets(workflow, spec)
        scene = _scene_with_obstacles(
            assets.planning_scene,
            [
                {
                    'object_id': 'fixture_box',
                    'center': [0.85, 0.55, 0.0],
                    'size': [0.2, 0.2, 0.2],
                    'shape': 'box',
                }
            ],
        )
        execution_graph = build_execution_graph_descriptor(spec, None)
        benchmark_report = workflow.run_benchmark(
            spec,
            config=IKConfig(position_only=True, retry_count=1),
            execution_graph=execution_graph,
        )
        trajectory = workflow.plan_trajectory(
            spec,
            q_start=np.asarray(spec.home_q, dtype=float),
            q_goal=np.asarray(spec.q_mid(), dtype=float),
            duration=2.0,
            dt=0.05,
            mode=TrajectoryMode.JOINT,
            target_pose=None,
            ik_config=None,
            planner_id=None,
            max_velocity=None,
            max_acceleration=None,
            validation_layers=('timing', 'limits', 'collision', 'goal_metrics', 'path_metrics'),
            pipeline_id=None,
            execution_graph=execution_graph,
        )
        validation = workflow.validate_trajectory(
            spec,
            trajectory,
            target_pose=None,
            q_goal=np.asarray(spec.q_mid(), dtype=float),
            validation_layers=('timing', 'limits', 'collision', 'goal_metrics', 'path_metrics'),
        )
        if not validation.feasible:
            raise RuntimeError(f'urdf_skeleton runtime case produced infeasible trajectory: {validation.reasons!r}')
        session_state = workflow.build_session_state(
            spec,
            q_current=np.asarray(spec.home_q, dtype=float),
            trajectory=trajectory,
            benchmark_report=benchmark_report,
        )
        session_state.planning_scene = scene
        session_state.scene_summary = scene.summary()
        session_path = _save_session_snapshot(container, name='urdf_skeleton_single_box_session.json', state=session_state)
        return BenchmarkRuntimeCaseResult(
            case_id='runtime_case:urdf_skeleton.obstacle_single_box.ik_planar_default_suite.snapshot_capture',
            ok=True,
            summary={
                'obstacle_count': int(len(scene.obstacles)),
                'trajectory_samples': int(np.asarray(trajectory.t, dtype=float).shape[0]),
                'benchmark_cases': int(benchmark_report.num_cases),
                'validation_feasible': bool(validation.feasible),
                'session_path': str(session_path),
            },
        )


def _run_urdf_model_dense_trajectory_case(repo_root: Path) -> BenchmarkRuntimeCaseResult:
    with TemporaryDirectory(prefix='benchmark_case_urdf_model_', dir=str(repo_root)) as temp_dir:
        temp_root = Path(temp_dir)
        export_root = temp_root / 'exports'
        container = _build_runtime_container(repo_root, export_root=export_root)
        urdf_path = _write_urdf(temp_root / 'model_case.urdf', name='model_case')
        workflow = container.workflow_facade
        spec = workflow.resolve_import(urdf_path, importer_id='urdf_model', persist=False).spec
        assets = _runtime_assets(workflow, spec)
        scene = _scene_with_obstacles(
            assets.planning_scene,
            [
                {'object_id': 'wall_a', 'center': [1.1, 0.6, 0.0], 'size': [0.18, 0.18, 0.18], 'shape': 'box'},
                {'object_id': 'wall_b', 'center': [1.4, -0.7, 0.0], 'size': [0.20, 0.20, 0.20], 'shape': 'box'},
                {'object_id': 'wall_c', 'center': [0.3, 1.0, 0.0], 'size': [0.16, 0.16, 0.16], 'shape': 'box'},
            ],
        )
        q_start = np.asarray(spec.home_q, dtype=float)
        q_goal = np.asarray(spec.q_mid(), dtype=float)
        execution_graph = build_execution_graph_descriptor(spec, None)
        trajectory = workflow.plan_trajectory(
            spec,
            q_start=q_start,
            q_goal=q_goal,
            duration=2.5,
            dt=0.05,
            mode=TrajectoryMode.JOINT,
            target_pose=None,
            ik_config=None,
            planner_id=None,
            max_velocity=None,
            max_acceleration=None,
            validation_layers=('timing', 'limits', 'collision', 'goal_metrics', 'path_metrics'),
            pipeline_id=None,
            execution_graph=execution_graph,
        )
        validation = workflow.validate_trajectory(
            spec,
            trajectory,
            target_pose=None,
            q_goal=q_goal,
            validation_layers=('timing', 'limits', 'collision', 'goal_metrics', 'path_metrics'),
        )
        if not validation.feasible:
            raise RuntimeError(f'urdf_model runtime case produced infeasible trajectory: {validation.reasons!r}')
        session_state = workflow.build_session_state(
            spec,
            q_current=q_goal,
            trajectory=trajectory,
        )
        session_state.planning_scene = scene
        session_state.scene_summary = scene.summary()
        session_path = _save_session_snapshot(container, name='urdf_model_dense_session.json', state=session_state)
        bootstrap_bundle = container.bootstrap_bundle
        bundle_path = bootstrap_bundle.workflow_facade.export_package(
            'urdf_model_dense_bundle.zip',
            [session_path],
            environment=dict(bootstrap_bundle.services.runtime_context or {}),
            config_snapshot=bootstrap_bundle.services.config_service.describe_effective_snapshot(),
            capability_snapshot=bootstrap_bundle.services.capability_matrix_service.build_matrix(
                solver_registry=bootstrap_bundle.registries.solver_registry,
                planner_registry=bootstrap_bundle.registries.planner_registry,
                importer_registry=bootstrap_bundle.registries.importer_registry,
            ).as_dict(),
            metadata={'source': 'benchmark_runtime_case'},
            replayable=True,
        )
        if not Path(bundle_path).exists():
            raise RuntimeError(f'benchmark runtime package was not written: {bundle_path}')
        return BenchmarkRuntimeCaseResult(
            case_id='runtime_case:urdf_model.obstacle_dense.trajectory_plan_smoke.snapshot_capture',
            ok=True,
            summary={
                'obstacle_count': int(len(scene.obstacles)),
                'trajectory_samples': int(np.asarray(trajectory.t, dtype=float).shape[0]),
                'validation_feasible': bool(validation.feasible),
                'package_path': str(bundle_path),
            },
        )


def _run_gui_render_contract_case(repo_root: Path) -> BenchmarkRuntimeCaseResult:
    if importlib.util.find_spec('PySide6') is None:
        from robot_sim.testing.qt_shims import install_pyside6_test_shims

        install_pyside6_test_shims()

    from robot_sim.render.scene_controller import SceneController
    from robot_sim.render.scene_3d_widget import Scene3DWidget

    with TemporaryDirectory(prefix='benchmark_case_gui_', dir=str(repo_root)) as temp_dir:
        temp_root = Path(temp_dir)
        container = _build_runtime_container(repo_root, export_root=temp_root / 'exports')
        urdf_path = _write_urdf(temp_root / 'gui_case.urdf', name='gui_case')
        workflow = container.workflow_facade
        spec = workflow.resolve_import(urdf_path, importer_id='urdf_model', persist=False).spec
        assets = _runtime_assets(workflow, spec)
        fk_result = workflow.run_fk(spec, np.asarray(spec.home_q, dtype=float))
        widget = Scene3DWidget()
        controller = SceneController(widget)
        controller.update_robot_geometry_projection(assets.robot_geometry.summary() if hasattr(assets.robot_geometry, 'summary') else {'links': spec.dof})
        controller.update_fk_projection(fk_result, target_pose=None, append_path=True)
        controller.update_planning_scene_projection(assets.planning_scene)
        snapshot = widget.scene_snapshot()
        runtime_snapshot = widget.render_runtime_snapshot()
        if 'robot_geometry' not in snapshot or snapshot['robot_geometry'] in (None, {}):
            raise RuntimeError('scene snapshot did not preserve robot geometry projection')
        if 'scene_3d' not in runtime_snapshot or 'screenshot' not in runtime_snapshot:
            raise RuntimeError('render runtime snapshot missing required capabilities')
        return BenchmarkRuntimeCaseResult(
            case_id='runtime_case:gui_offscreen.urdf_model.clean_scene.live_capture_capability_probe',
            ok=True,
            summary={
                'scene_snapshot_keys': sorted(snapshot.keys()),
                'scene_3d_status': runtime_snapshot['scene_3d'].status,
                'screenshot_status': runtime_snapshot['screenshot'].status,
            },
        )


_RUNTIME_CASE_CATALOG = BenchmarkRuntimeCaseCatalog()
