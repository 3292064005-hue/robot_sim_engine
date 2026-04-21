from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np
import yaml

from robot_sim.application.request_builders import (
    build_execution_graph_descriptor,
    build_ik_config,
    build_ik_request,
    build_pose_from_mapping,
    build_trajectory_request,
    normalize_validation_layers,
)
from robot_sim.app.headless_request_adapter import HeadlessRequestContractAdapter
from robot_sim.app.workflow_facade import ApplicationWorkflowFacade
from robot_sim.domain.enums import TrajectoryMode
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.session_state import SessionState
from robot_sim.model.trajectory import JointTrajectory


class HeadlessError(ValueError):
    """Base error raised by the headless CLI/API surface."""


class HeadlessRequestError(HeadlessError):
    """Raised when a headless CLI/API request payload is invalid."""


class HeadlessExecutionError(HeadlessError):
    """Raised when a headless command cannot complete its requested workflow."""


class HeadlessWorkflowService:
    """Headless workflow surface exposing stable machine-readable contracts.

    The service binds the existing application use cases to typed JSON/YAML request payloads so
    private automation, CI, and batch validation can use the engine without the GUI shell.
    """

    def __init__(self, container) -> None:
        self._container = container
        self._services = getattr(container, 'service_bundle', container)
        self._registries = getattr(container, 'registry_bundle', container)
        self._workflows = getattr(container, 'workflow_bundle', container)
        self._application_workflow = getattr(container, 'workflow_facade', None) or ApplicationWorkflowFacade.from_container(container)

    def execute(self, command: str, request: Mapping[str, object]) -> dict[str, object]:
        dispatch = {
            'import': self.import_robot,
            'fk': self.run_fk,
            'ik': self.run_ik,
            'plan': self.plan_trajectory,
            'validate': self.validate_trajectory,
            'benchmark': self.run_benchmark,
            'export-session': self.export_session,
            'export-package': self.export_package,
        }
        action = dispatch.get(str(command))
        if action is None:
            raise HeadlessRequestError(f'unsupported headless command: {command}')
        try:
            return action(dict(request or {}))
        except HeadlessError:
            raise
        except (RuntimeError, ValueError, TypeError, KeyError, FileNotFoundError, OSError) as exc:
            raise HeadlessExecutionError(f'{command} failed: {exc}') from exc

    def import_robot(self, request: Mapping[str, object]) -> dict[str, object]:
        spec = self._resolve_spec(request)
        execution_graph = build_execution_graph_descriptor(spec, request.get('execution_graph'))
        return {
            'robot': self._spec_summary(spec),
            'imported_package_present': bool(spec.imported_package is not None),
            'execution_summary': dict(spec.execution_summary),
            'execution_graph': execution_graph.summary(),
        }

    def run_fk(self, request: Mapping[str, object]) -> dict[str, object]:
        spec = self._resolve_spec(request)
        q = self._joint_vector(request.get('q'), spec=spec, field='q', default=spec.home_q)
        result = self._application_workflow.run_fk(spec, q)
        return {
            'robot': self._spec_summary(spec),
            'q': np.asarray(q, dtype=float).tolist(),
            'ee_pose': self._pose_payload(result.ee_pose),
            'metadata': dict(result.metadata),
            'joint_positions': np.asarray(result.joint_positions, dtype=float).tolist(),
        }

    def run_ik(self, request: Mapping[str, object]) -> dict[str, object]:
        spec = self._resolve_spec(request)
        target = self._pose_from_request(request)
        solver_defaults = self._services.config_service.load_solver_settings().ik
        config = build_ik_config(request.get('config'), defaults=solver_defaults, error_factory=HeadlessRequestError)
        q0 = self._joint_vector(request.get('q0'), spec=spec, field='q0', default=spec.home_q)
        execution_graph = build_execution_graph_descriptor(spec, request.get('execution_graph'), error_factory=HeadlessRequestError)
        result = self._application_workflow.run_ik(spec, target=target, q0=q0, config=config, execution_graph=execution_graph)
        return {
            'robot': self._spec_summary(spec),
            'success': bool(result.success),
            'message': str(result.message),
            'stop_reason': result.stop_reason,
            'q_sol': np.asarray(result.q_sol, dtype=float).tolist(),
            'best_q': None if result.best_q is None else np.asarray(result.best_q, dtype=float).tolist(),
            'final_pos_err': float(result.final_pos_err),
            'final_ori_err': float(result.final_ori_err),
            'elapsed_ms': float(result.elapsed_ms),
            'diagnostics': dict(result.diagnostics),
            'warnings': list(result.warnings),
            'execution_graph': execution_graph.summary(),
        }

    def plan_trajectory(self, request: Mapping[str, object]) -> dict[str, object]:
        spec = self._resolve_spec(request)
        q_start = self._joint_vector(request.get('q_start'), spec=spec, field='q_start', default=spec.home_q)
        duration = float(request.get('duration', 3.0) or 3.0)
        dt = float(request.get('dt', 0.02) or 0.02)
        mode = self._trajectory_mode(request.get('mode', 'joint_space'))
        planner_id = None if request.get('planner_id') in (None, '') else str(request.get('planner_id'))
        default_pipeline_id = self._services.config_service.load_solver_settings().trajectory.pipeline_id
        pipeline_id = default_pipeline_id if request.get('pipeline_id') in (None, '') else str(request.get('pipeline_id'))
        target_pose = None
        ik_config = None
        q_goal = request.get('q_goal')
        if mode is TrajectoryMode.CARTESIAN:
            target_pose = self._pose_from_request(request)
            solver_defaults = self._services.config_service.load_solver_settings().ik
            ik_config = build_ik_config(request.get('ik_config') or request.get('config'), defaults=solver_defaults, error_factory=HeadlessRequestError)
            q_goal = None
        elif q_goal is not None:
            q_goal = self._joint_vector(q_goal, spec=spec, field='q_goal', default=spec.home_q)
        else:
            ik_payload = request.get('ik')
            if isinstance(ik_payload, Mapping):
                ik_result = self.run_ik(
                    {
                        **dict(ik_payload),
                        'robot': request.get('robot'),
                        'source': request.get('source'),
                        'importer_id': request.get('importer_id'),
                        'execution_graph': request.get('execution_graph'),
                    }
                )
                if not bool(ik_result.get('success', False)):
                    raise HeadlessExecutionError(
                        f'plan request could not derive q_goal from IK: {ik_result.get("message", "IK failed")}'
                    )
                q_goal = np.asarray(ik_result['q_sol'], dtype=float)
            else:
                q_goal = self._joint_vector(spec.q_mid(), spec=spec, field='q_goal', default=spec.home_q)
        validation_layers = normalize_validation_layers(request.get('validation_layers'), error_factory=HeadlessRequestError)
        execution_graph = build_execution_graph_descriptor(spec, request.get('execution_graph'), error_factory=HeadlessRequestError)
        traj = self._application_workflow.plan_trajectory(
            spec,
            q_start=q_start,
            q_goal=None if q_goal is None else np.asarray(q_goal, dtype=float),
            duration=duration,
            dt=dt,
            mode=mode,
            target_pose=target_pose,
            ik_config=ik_config,
            planner_id=planner_id,
            max_velocity=None if request.get('max_velocity') is None else float(request['max_velocity']),
            max_acceleration=None if request.get('max_acceleration') is None else float(request['max_acceleration']),
            validation_layers=validation_layers,
            pipeline_id=pipeline_id,
            execution_graph=execution_graph,
        )
        return self._trajectory_payload(traj)

    def validate_trajectory(self, request: Mapping[str, object]) -> dict[str, object]:
        spec = self._resolve_spec(request)
        trajectory = self._trajectory_from_payload(request.get('trajectory'))
        target_pose = None
        if isinstance(request.get('target'), Mapping):
            target_pose = build_pose_from_mapping(dict(request['target']), error_factory=HeadlessRequestError)
        q_goal = None if request.get('q_goal') is None else self._joint_vector(request.get('q_goal'), spec=spec, field='q_goal', default=spec.home_q)
        validation_layers = normalize_validation_layers(request.get('validation_layers'), error_factory=HeadlessRequestError)
        report = self._application_workflow.validate_trajectory(
            spec,
            trajectory,
            target_pose=target_pose,
            q_goal=q_goal,
            validation_layers=validation_layers,
        )
        return report.as_dict() if hasattr(report, 'as_dict') else dict(report.__dict__)

    def run_benchmark(self, request: Mapping[str, object]) -> dict[str, object]:
        spec = self._resolve_spec(request)
        solver_defaults = self._services.config_service.load_solver_settings().ik
        config = build_ik_config(request.get('config'), defaults=solver_defaults, error_factory=HeadlessRequestError)
        execution_graph = build_execution_graph_descriptor(spec, request.get('execution_graph'), error_factory=HeadlessRequestError)
        report = self._application_workflow.run_benchmark(spec, config=config, execution_graph=execution_graph)
        return {
            'robot': report.robot,
            'num_cases': int(report.num_cases),
            'success_rate': float(report.success_rate),
            'cases': [dict(item) for item in report.cases],
            'aggregate': dict(report.aggregate),
            'metadata': dict(report.metadata),
            'comparison': dict(report.comparison),
        }

    def export_session(self, request: Mapping[str, object]) -> dict[str, object]:
        spec = self._resolve_spec(request)
        q_current = self._joint_vector(request.get('q_current'), spec=spec, field='q_current', default=spec.home_q)
        trajectory = self._trajectory_from_payload(request['trajectory']) if isinstance(request.get('trajectory'), Mapping) else None
        benchmark_report = None
        if isinstance(request.get('benchmark_report'), Mapping):
            payload = dict(request['benchmark_report'])
            benchmark_report = BenchmarkReport(
                robot=str(payload.get('robot', spec.name)),
                num_cases=int(payload.get('num_cases', 0)),
                success_rate=float(payload.get('success_rate', 0.0)),
                cases=tuple(payload.get('cases', ()) or ()),
                aggregate=dict(payload.get('aggregate', {}) or {}),
                metadata=dict(payload.get('metadata', {}) or {}),
                comparison=dict(payload.get('comparison', {}) or {}),
            )
        state = self._application_workflow.build_session_state(
            spec,
            q_current=q_current,
            trajectory=trajectory,
            benchmark_report=benchmark_report,
        )
        name = str(request.get('name', 'headless_session.json') or 'headless_session.json')
        path = self._application_workflow.export_session(
            name,
            state,
            environment=dict(self._container.runtime_context or {}),
            config_snapshot=self._services.config_service.describe_effective_snapshot(),
            capability_snapshot=self._capability_snapshot(),
            telemetry_detail=str(request.get('telemetry_detail', 'full') or 'full'),
        )
        return {'path': str(path), 'name': path.name}

    def export_package(self, request: Mapping[str, object]) -> dict[str, object]:
        files: list[Path] = []
        for item in request.get('files', ()) or ():
            path = Path(str(item)).expanduser()
            if not path.exists():
                raise HeadlessRequestError(f'package file not found: {path}')
            files.append(path)
        if not files and isinstance(request.get('session_request'), Mapping):
            session_result = self.export_session(dict(request['session_request']))
            files.append(Path(str(session_result['path'])))
        if not files and isinstance(request.get('benchmark_request'), Mapping):
            benchmark_payload = self.run_benchmark(dict(request['benchmark_request']))
            benchmark_path = self._application_workflow.export_benchmark_report(
                str(request.get('benchmark_name', 'headless_benchmark.json') or 'headless_benchmark.json'),
                benchmark_payload,
            )
            files.append(benchmark_path)
        if not files and isinstance(request.get('trajectory_request'), Mapping):
            trajectory_payload = self.plan_trajectory(dict(request['trajectory_request']))
            trajectory = self._trajectory_from_payload(trajectory_payload)
            trajectory_path = self._application_workflow.export_trajectory_bundle(
                str(request.get('trajectory_name', 'headless_trajectory.npz') or 'headless_trajectory.npz'),
                trajectory,
                robot_id=trajectory_payload.get('robot', {}).get('name') if isinstance(trajectory_payload.get('robot'), Mapping) else None,
                planner_id=str((trajectory.metadata or {}).get('planner_id', '') or ''),
            )
            files.append(trajectory_path)
        if not files:
            raise HeadlessRequestError('export-package requires files, session_request, benchmark_request, or trajectory_request')
        name = str(request.get('name', 'headless_bundle.zip') or 'headless_bundle.zip')
        package_path = self._application_workflow.export_package(
            name,
            files,
            environment=dict(self._container.runtime_context or {}),
            config_snapshot=self._services.config_service.describe_effective_snapshot(),
            capability_snapshot=self._capability_snapshot(),
            metadata={'source': 'headless_workflow'},
            replayable=True,
        )
        return {'path': str(package_path), 'name': package_path.name, 'files': [file.name for file in files]}

    def _resolve_spec(self, request: Mapping[str, object]) -> RobotSpec:
        source = request.get('source')
        robot = request.get('robot')
        importer_id = None if request.get('importer_id') in (None, '') else str(request.get('importer_id'))
        try:
            return self._application_workflow.resolve_spec_reference(
                robot=None if robot in (None, '') else str(robot),
                source=None if source in (None, '') else str(source),
                importer_id=importer_id,
            )
        except FileNotFoundError as exc:
            raise HeadlessRequestError(str(exc)) from exc
        except ValueError as exc:
            raise HeadlessRequestError(str(exc)) from exc

    @staticmethod
    def _joint_vector(raw: object, *, spec: RobotSpec, field: str, default) -> np.ndarray:
        if raw is None or (isinstance(raw, str) and raw == ''):
            value = default
        else:
            value = raw
        try:
            q = np.asarray(value, dtype=float).reshape(-1)
        except (TypeError, ValueError) as exc:
            raise HeadlessRequestError(f'{field} must be a numeric joint vector') from exc
        if q.shape != (spec.dof,):
            raise HeadlessRequestError(f'{field} shape mismatch: expected {(spec.dof,)}, got {q.shape}')
        if not np.isfinite(q).all():
            raise HeadlessRequestError(f'{field} contains non-finite values')
        return q.copy()

    @staticmethod
    def _trajectory_mode(value: object) -> TrajectoryMode:
        try:
            return TrajectoryMode(str(value or TrajectoryMode.JOINT.value))
        except ValueError as exc:
            raise HeadlessRequestError(f'unsupported trajectory mode: {value}') from exc

    def _pose_from_request(self, request: Mapping[str, object]):
        raw_target = request.get('target')
        if isinstance(raw_target, Mapping):
            return build_pose_from_mapping(dict(raw_target), error_factory=HeadlessRequestError)
        position = request.get('position')
        if position is None:
            raise HeadlessRequestError('pose request missing target/position payload')
        return build_pose_from_mapping(
            {
                'position': position,
                'rotation_rvec': request.get('rotation_rvec'),
                'rotation_matrix': request.get('rotation_matrix'),
                'euler_zyx': request.get('euler_zyx'),
            },
            error_factory=HeadlessRequestError,
        )

    def _trajectory_from_payload(self, raw: object) -> JointTrajectory:
        if not isinstance(raw, Mapping):
            raise HeadlessRequestError('trajectory payload must be a mapping')

        def _array(name: str, *, default=None):
            value = raw.get(name, default)
            if value is None:
                return None
            try:
                return np.asarray(value, dtype=float)
            except (TypeError, ValueError) as exc:
                raise HeadlessRequestError(f'trajectory.{name} must be numeric') from exc

        try:
            metadata = dict(raw.get('metadata', {}) or {})
            feasibility = dict(raw.get('feasibility', {}) or {})
            quality = dict(raw.get('quality', {}) or {})
        except (TypeError, ValueError) as exc:
            raise HeadlessRequestError('trajectory metadata/feasibility/quality must be mapping-like') from exc
        return JointTrajectory(
            t=_array('t'),
            q=_array('q'),
            qd=_array('qd'),
            qdd=_array('qdd'),
            ee_positions=_array('ee_positions'),
            joint_positions=_array('joint_positions'),
            ee_rotations=_array('ee_rotations'),
            metadata=metadata,
            feasibility=feasibility,
            quality=quality,
        )

    @staticmethod
    def _trajectory_payload(trajectory: JointTrajectory) -> dict[str, object]:
        return {
            't': np.asarray(trajectory.t, dtype=float).tolist(),
            'q': np.asarray(trajectory.q, dtype=float).tolist(),
            'qd': None if trajectory.qd is None else np.asarray(trajectory.qd, dtype=float).tolist(),
            'qdd': None if trajectory.qdd is None else np.asarray(trajectory.qdd, dtype=float).tolist(),
            'ee_positions': None if trajectory.ee_positions is None else np.asarray(trajectory.ee_positions, dtype=float).tolist(),
            'joint_positions': None if trajectory.joint_positions is None else np.asarray(trajectory.joint_positions, dtype=float).tolist(),
            'ee_rotations': None if trajectory.ee_rotations is None else np.asarray(trajectory.ee_rotations, dtype=float).tolist(),
            'metadata': dict(trajectory.metadata),
            'feasibility': dict(trajectory.feasibility),
            'quality': dict(trajectory.quality),
            'cache_status': trajectory.cache_status,
            'scene_revision': trajectory.scene_revision,
        }

    @staticmethod
    def _pose_payload(pose) -> dict[str, object]:
        return {
            'position': np.asarray(pose.p, dtype=float).tolist(),
            'rotation_matrix': np.asarray(pose.R, dtype=float).tolist(),
            'frame': getattr(getattr(pose, 'frame', None), 'value', str(getattr(pose, 'frame', 'base'))),
        }

    @staticmethod
    def _spec_summary(spec: RobotSpec) -> dict[str, object]:
        return {
            'name': spec.name,
            'label': spec.label,
            'dof': int(spec.dof),
            'model_source': str(spec.model_source or ''),
            'kinematic_source': str(spec.kinematic_source or ''),
            'source_model_summary': dict(spec.source_model_summary or {}),
        }

    def _capability_snapshot(self) -> dict[str, object]:
        service = getattr(self._container, 'capability_matrix_service', None)
        if service is None:
            return {}
        matrix = service.build_matrix(
            solver_registry=self._registries.solver_registry,
            planner_registry=self._registries.planner_registry,
            importer_registry=self._registries.importer_registry,
        )
        return matrix.as_dict() if hasattr(matrix, 'as_dict') else dict(matrix)


def load_request_payload(
    path: str | Path | None = None,
    *,
    request_file: str | Path | None = None,
    request_json: str | None = None,
) -> dict[str, object]:
    """Load one headless batch request payload through the canonical contract adapter.

    All transport-layer parse failures are mapped to :class:`HeadlessRequestError`, which keeps
    the CLI/API surface machine-readable and allows malformed payloads to be rejected before
    runtime bootstrap.
    """
    adapter = HeadlessRequestContractAdapter(HeadlessRequestError)
    return adapter.load(path, request_file=request_file, request_json=request_json)
