from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from robot_sim.application.services.manifest_builder import ManifestBuilder, export_manifest_as_dict
from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.domain.collision_fidelity import summarize_collision_fidelity
from robot_sim.model.capability_schema import build_runtime_capability_schema
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.session_state import SessionState
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.version_catalog import VersionCatalog, current_version_catalog


class ExportService:
    """Export service for trajectories, benchmark artifacts, and session state."""

    def __init__(self, export_dir: str | Path, version_catalog: VersionCatalog | None = None) -> None:
        """Create the export service.

        Args:
            export_dir: Destination directory for exported artifacts.
            version_catalog: Optional version catalog used for manifest metadata.

        Returns:
            None: Initializes export destinations only.

        Raises:
            OSError: If the export directory cannot be created.
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._versions = version_catalog or current_version_catalog()
        self._manifest_builder = ManifestBuilder(self._versions)

    def save_json(self, name: str, payload: dict) -> Path:
        path = self.export_dir / name
        with path.open('w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path

    def save_csv(self, name: str, array: np.ndarray, header: str = '') -> Path:
        path = self.export_dir / name
        np.savetxt(path, array, delimiter=',', header=header, comments='')
        return path

    def save_dict_csv(self, name: str, rows: list[dict[str, object]]) -> Path:
        path = self.export_dir / name
        with path.open('w', encoding='utf-8', newline='') as handle:
            if not rows:
                handle.write('')
                return path
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def build_manifest(
        self,
        *,
        robot_id: str | None = None,
        solver_id: str | None = None,
        planner_id: str | None = None,
        reproducibility_seed: int | None = None,
        files: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        schema_version: str | None = None,
        export_version: str | None = None,
        correlation_id: str | None = None,
        bundle_kind: str = 'artifact_bundle',
        bundle_contract: str = 'artifact_audit_bundle',
        replayable: bool = False,
        environment: dict[str, object] | None = None,
        config_snapshot: dict[str, object] | None = None,
        scene_snapshot: dict[str, object] | None = None,
        plugin_snapshot: dict[str, object] | None = None,
        capability_snapshot: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Build a structured export manifest for downstream consumers."""
        manifest = self._manifest_builder.build_manifest(
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=planner_id,
            reproducibility_seed=reproducibility_seed,
            files=files,
            metadata=metadata,
            schema_version=schema_version,
            export_version=export_version,
            correlation_id=correlation_id,
            bundle_kind=bundle_kind,
            bundle_contract=bundle_contract,
            replayable=replayable,
            environment=environment,
            config_snapshot=config_snapshot,
            scene_snapshot=scene_snapshot,
            plugin_snapshot=plugin_snapshot,
            capability_snapshot=capability_snapshot,
        )
        return export_manifest_as_dict(manifest)

    def save_trajectory(self, name: str, t: np.ndarray, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> Path:
        header_cols = ['t']
        header_cols += [f'q{i}' for i in range(q.shape[1])]
        header_cols += [f'qd{i}' for i in range(qd.shape[1])]
        header_cols += [f'qdd{i}' for i in range(qdd.shape[1])]
        merged = np.column_stack([t, q, qd, qdd])
        return self.save_csv(name, merged, header=','.join(header_cols))

    def save_trajectory_bundle(self, name: str, trajectory: JointTrajectory, *, robot_id: str | None = None, solver_id: str | None = None, planner_id: str | None = None) -> Path:
        stem = Path(name).stem
        path = self.export_dir / f'{stem}.npz'
        canonical = resolve_planner_metadata(trajectory.metadata)
        resolved_planner_id = str(planner_id or canonical['planner_id'] or '')
        manifest = self.build_manifest(
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=resolved_planner_id,
            files=[path.name],
            metadata={
                'kind': 'trajectory_bundle',
                'cache_status': trajectory.cache_status,
                'scene_revision': trajectory.scene_revision,
                'planner_summary': canonical,
            },
            correlation_id=str(trajectory.metadata.get('correlation_id', '') or ''),
        )
        payload: dict[str, object] = {
            't': np.asarray(trajectory.t, dtype=float),
            'q': np.asarray(trajectory.q, dtype=float),
            'qd': np.asarray(trajectory.qd, dtype=float),
            'qdd': np.asarray(trajectory.qdd, dtype=float),
            'manifest_json': json.dumps(manifest, ensure_ascii=False),
            'metadata_json': json.dumps(trajectory.metadata, ensure_ascii=False),
            'quality_json': json.dumps(trajectory.quality, ensure_ascii=False),
            'feasibility_json': json.dumps(trajectory.feasibility, ensure_ascii=False),
        }
        if trajectory.ee_positions is not None:
            payload['ee_positions'] = np.asarray(trajectory.ee_positions, dtype=float)
        if trajectory.joint_positions is not None:
            payload['joint_positions'] = np.asarray(trajectory.joint_positions, dtype=float)
        if trajectory.ee_rotations is not None:
            payload['ee_rotations'] = np.asarray(trajectory.ee_rotations, dtype=float)
        np.savez_compressed(path, **payload)
        return path

    def save_metrics(self, name: str, payload: dict) -> Path:
        return self.save_json(name, payload)

    def save_metrics_csv(self, name: str, payload: dict) -> Path:
        return self.save_dict_csv(name, [{'metric': key, 'value': value} for key, value in payload.items()])

    def save_benchmark_report(self, name: str, payload: dict) -> Path:
        return self.save_json(name, payload)

    def save_benchmark_cases_csv(self, name: str, report: BenchmarkReport) -> Path:
        return self.save_dict_csv(name, [dict(case) for case in report.cases])

    def save_session(
        self,
        name: str,
        state: SessionState,
        *,
        environment: dict[str, object] | None = None,
        config_snapshot: dict[str, object] | None = None,
        scene_snapshot: dict[str, object] | None = None,
        plugin_snapshot: dict[str, object] | None = None,
        capability_snapshot: dict[str, object] | None = None,
        telemetry_detail: str = 'full',
    ) -> Path:
        task_snapshot = state.active_task_snapshot
        correlation_id = '' if task_snapshot is None else str(task_snapshot.correlation_id)
        planner_id = None
        planner_summary = None
        if state.trajectory is not None:
            planner_summary = resolve_planner_metadata(state.trajectory.metadata)
            planner_id = planner_summary['planner_id'] or None
        normalized_telemetry_detail = str(telemetry_detail or 'full').strip().lower() or 'full'
        if normalized_telemetry_detail not in {'full', 'minimal'}:
            raise ValueError(f'unsupported telemetry detail: {telemetry_detail}')
        telemetry_events = tuple(getattr(state, 'render_telemetry', ()) or ())
        operation_spans = tuple(getattr(state, 'render_operation_spans', ()) or ())
        sampling_counters = tuple(getattr(state, 'render_sampling_counters', ()) or ())
        backend_performance = tuple(getattr(state, 'render_backend_performance', ()) or ())
        runtime_advice = dict(getattr(state, 'render_runtime_advice', {}) or {})
        if normalized_telemetry_detail == 'full':
            render_telemetry_payload = {
                'detail': 'full',
                'event_count': len(telemetry_events),
                'sequence': int(getattr(state, 'render_telemetry_sequence', 0) or 0),
                'events': [event.as_dict() if hasattr(event, 'as_dict') else dict(event) for event in telemetry_events],
                'operation_span_count': len(operation_spans),
                'operation_sequence': int(getattr(state, 'render_operation_sequence', 0) or 0),
                'operation_spans': [span.as_dict() if hasattr(span, 'as_dict') else dict(span) for span in operation_spans],
                'sampling_counter_count': len(sampling_counters),
                'sampling_sequence': int(getattr(state, 'render_sampling_sequence', 0) or 0),
                'sampling_counters': [counter.as_dict() if hasattr(counter, 'as_dict') else dict(counter) for counter in sampling_counters],
                'backend_count': len(backend_performance),
                'runtime_advice': runtime_advice,
                'backend_performance': [entry.as_dict() if hasattr(entry, 'as_dict') else dict(entry) for entry in backend_performance],
                'runtime_advice': runtime_advice,
            }
        else:
            render_telemetry_payload = {
                'detail': 'minimal',
                'event_count': len(telemetry_events),
                'sequence': int(getattr(state, 'render_telemetry_sequence', 0) or 0),
                'operation_span_count': len(operation_spans),
                'operation_sequence': int(getattr(state, 'render_operation_sequence', 0) or 0),
                'sampling_counter_count': len(sampling_counters),
                'sampling_sequence': int(getattr(state, 'render_sampling_sequence', 0) or 0),
                'backend_count': len(backend_performance),
            }
        planning_scene_summary = None if state.planning_scene is None else (
            state.planning_scene.summary()
            if hasattr(state.planning_scene, 'summary')
            else {
                'revision': int(getattr(state.planning_scene, 'revision', 0)),
                'collision_level': getattr(getattr(state.planning_scene, 'collision_level', None), 'value', str(getattr(state.planning_scene, 'collision_level', 'aabb'))),
                'collision_backend': str(getattr(state.planning_scene, 'collision_backend', 'aabb')),
                'obstacle_ids': list(getattr(state.planning_scene, 'obstacle_ids', ())),
                'attached_object_ids': [obj.object_id for obj in getattr(state.planning_scene, 'attached_objects', ())],
            }
        )
        scene_runtime_summary = dict(getattr(state, 'scene_summary', {}) or {})
        if not scene_runtime_summary and planning_scene_summary is not None:
            scene_runtime_summary = {
                'revision': int(planning_scene_summary.get('revision', 0) or 0),
                'environment_contract': dict(planning_scene_summary.get('environment_contract', {}) or {}),
                'log_policy': dict(planning_scene_summary.get('log_policy', {}) or {}),
                'diff_replication': dict(planning_scene_summary.get('diff_replication', {}) or {'change_count': 0, 'obstacle_delta': 0, 'attached_object_delta': 0}),
                'replay_cursor': str(planning_scene_summary.get('replay_cursor', '') or ''),
            }
        imported_package_summary = (
            dict(scene_runtime_summary.get('imported_package_summary', {}) or {})
            or (None if state.robot_spec is None or state.robot_spec.imported_package is None else state.robot_spec.imported_package.summary())
        )
        planning_collision_summary = {} if planning_scene_summary is None else dict(planning_scene_summary.get('collision_fidelity', {}) or {})
        if not planning_collision_summary and planning_scene_summary is not None:
            planning_collision_summary = summarize_collision_fidelity(
                collision_level=planning_scene_summary.get('collision_level', getattr(getattr(state.planning_scene, 'collision_level', None), 'value', None)),
                collision_backend=planning_scene_summary.get('collision_backend', getattr(state.planning_scene, 'collision_backend', 'aabb')),
                scene_fidelity=planning_scene_summary.get('scene_fidelity', getattr(state.planning_scene, 'geometry_source', 'generated')),
            )
        validation_surface_summary = {} if planning_scene_summary is None else dict(planning_scene_summary.get('validation_surface', {}) or {})
        trajectory_validation_caps = (
            {}
            if state.trajectory is None
            else dict(state.trajectory.metadata.get('validation_capabilities', {}) or {})
        )
        trajectory_collision_summary = (
            {}
            if state.trajectory is None
            else dict(state.trajectory.typed_feasibility.collision_summary or {})
        )
        collision_broad_phase_executed = bool(
            trajectory_validation_caps.get('collision_broad_phase', False) or trajectory_collision_summary
        )
        scene_validation_precision = str(
            trajectory_validation_caps.get(
                'scene_validation_precision',
                validation_surface_summary.get('scene_validation_precision', ''),
            )
            or ''
        )
        validation_capabilities = {
            'layers': list(trajectory_validation_caps.get('layers', ()) or ()),
            'joint_limits': bool(trajectory_validation_caps.get('joint_limits', False)),
            'goal_validation': bool(trajectory_validation_caps.get('goal_validation', trajectory_validation_caps.get('goal_metrics', False))),
            'goal_metrics': bool(trajectory_validation_caps.get('goal_metrics', trajectory_validation_caps.get('goal_validation', False))),
            'timing_validation': bool(trajectory_validation_caps.get('timing_validation', trajectory_validation_caps.get('timing', False))),
            'timing': bool(trajectory_validation_caps.get('timing', trajectory_validation_caps.get('timing_validation', False))),
            'path_metrics': bool(trajectory_validation_caps.get('path_metrics', False)),
            'collision_broad_phase': collision_broad_phase_executed,
            'collision_backend': None if planning_scene_summary is None else str(planning_scene_summary.get('collision_backend', 'aabb')),
            'collision_precision': scene_validation_precision or 'none',
            'continuous_collision': False,
            'mesh_collision': False,
            'attached_object_validation': bool(collision_broad_phase_executed and planning_scene_summary is not None and planning_scene_summary.get('attached_object_count', 0)),
            'allowed_collision_matrix': bool(collision_broad_phase_executed and planning_scene_summary is not None and planning_scene_summary.get('collision_filter_pair_count', 0)),
            'scene_validation_mode': str(
                trajectory_validation_caps.get(
                    'scene_validation_mode',
                    validation_surface_summary.get('scene_validation_mode', 'none' if not collision_broad_phase_executed else 'broad_phase'),
                )
                or 'none'
            ),
            'scene_validation_precision': scene_validation_precision or 'none',
            'scene_validation_effective': collision_broad_phase_executed,
            'warning': '' if collision_broad_phase_executed else 'collision_validation_not_executed_or_not_recorded',
        }
        scene_fidelity_summary = {
            'collision_backend': None if planning_scene_summary is None else str(planning_collision_summary.get('collision_backend', planning_scene_summary.get('collision_backend', 'aabb'))),
            'collision_level': None if planning_scene_summary is None else str(planning_collision_summary.get('collision_level', planning_scene_summary.get('collision_level', 'aabb'))),
            'scene_fidelity': None if planning_scene_summary is None else str(planning_collision_summary.get('scene_fidelity', planning_scene_summary.get('scene_fidelity', 'generated'))),
            'precision': None if planning_scene_summary is None else str(planning_collision_summary.get('precision', '')),
            'stable_surface': False if planning_scene_summary is None else bool(planning_collision_summary.get('stable_surface', False)),
            'promotion_state': None if planning_scene_summary is None else str(planning_collision_summary.get('promotion_state', '')),
            'summary': None if planning_scene_summary is None else str(planning_collision_summary.get('summary', '')),
            'backend_status': None if planning_scene_summary is None else str(planning_collision_summary.get('backend_status', '')),
            'backend_availability': None if planning_scene_summary is None else str(planning_collision_summary.get('backend_availability', '')),
            'backend_family': None if planning_scene_summary is None else str(planning_collision_summary.get('backend_family', '')),
            'supported_collision_levels': [] if planning_scene_summary is None else [str(item) for item in planning_collision_summary.get('supported_collision_levels', ()) or ()],
            'validation_surface': 'planning_scene.summary',
            'scene_validation_mode': None if planning_scene_summary is None else str(validation_surface_summary.get('scene_validation_mode', '')),
            'scene_validation_precision': None if planning_scene_summary is None else str(validation_surface_summary.get('scene_validation_precision', '')),
            'scene_geometry_contract': None if planning_scene_summary is None else str(planning_scene_summary.get('scene_geometry_contract') or dict(imported_package_summary.get('geometry_model', {}) if imported_package_summary else {}).get('geometry_contract', '')),
            'stable_surface_version': None if planning_scene_summary is None else str(planning_scene_summary.get('stable_surface_version', '')),
            'validation_capabilities': validation_capabilities,
        }
        capability_schema = build_runtime_capability_schema(
            execution_summary=None if state.robot_spec is None else dict(state.robot_spec.execution_summary or {}),
            imported_package_summary=imported_package_summary,
            scene_fidelity_summary=scene_fidelity_summary,
            scene_snapshot=scene_snapshot or planning_scene_summary,
            plugin_snapshot=plugin_snapshot,
            capability_snapshot=capability_snapshot or dict(getattr(state, 'capability_matrix', {}) or {}),
        )
        payload = {
            'manifest': self.build_manifest(
                robot_id=state.robot_spec.name if state.robot_spec is not None else None,
                solver_id=state.ik_result.effective_mode if state.ik_result is not None else None,
                planner_id=planner_id,
                files=[name],
                metadata={'kind': 'session'},
                schema_version=self._versions.session_schema_version,
                export_version=self._versions.session_schema_version,
                correlation_id=correlation_id,
                bundle_kind='session_snapshot',
                bundle_contract='session_audit_bundle',
                replayable=False,
                environment=environment,
                config_snapshot=config_snapshot,
                scene_snapshot=scene_snapshot,
                plugin_snapshot=plugin_snapshot,
                capability_snapshot=capability_snapshot,
            ),
            'robot_name': state.robot_spec.name if state.robot_spec is not None else None,
            'planner_summary': planner_summary,
            'robot_label': state.robot_spec.label if state.robot_spec is not None else None,
            'robot_model_source': state.robot_spec.model_source if state.robot_spec is not None else None,
            'source_model_summary': None if state.robot_spec is None else dict(state.robot_spec.source_model_summary or {}),
            'execution_summary': None if state.robot_spec is None else dict(state.robot_spec.execution_summary or {}),
            'runtime_model_summary': None if state.robot_spec is None else state.robot_spec.runtime_model.summary(),
            'articulated_model_summary': None if state.robot_spec is None else state.robot_spec.articulated_model.summary(),
            'geometry_model_summary': (
                dict(getattr(state, 'scene_summary', {}).get('geometry_model_summary', {}) or {})
                or (
                    None
                    if state.robot_spec is None or state.robot_spec.imported_package is None or state.robot_spec.imported_package.geometry_model is None
                    else state.robot_spec.imported_package.geometry_model.summary()
                )
            ),
            'imported_package_summary': imported_package_summary,
            'import_fidelity_breakdown': None if imported_package_summary is None else dict(imported_package_summary.get('fidelity_breakdown', {}) or {}),
            'q_current': None if state.q_current is None else np.asarray(state.q_current, dtype=float).tolist(),
            'target_pose': None if state.target_pose is None else {'p': np.asarray(state.target_pose.p, dtype=float).tolist(), 'R': np.asarray(state.target_pose.R, dtype=float).tolist(), 'frame': getattr(state.target_pose.frame, 'value', str(state.target_pose.frame))},
            'ik': None if state.ik_result is None else {
                'success': state.ik_result.success,
                'message': state.ik_result.message,
                'iterations': len(state.ik_result.logs),
                'final_pos_err': float(state.ik_result.final_pos_err),
                'final_ori_err': float(state.ik_result.final_ori_err),
                'stop_reason': state.ik_result.stop_reason,
                'restarts_used': int(state.ik_result.restarts_used),
                'diagnostics': dict(state.ik_result.diagnostics),
            },
            'trajectory': None if state.trajectory is None else {
                'num_samples': int(state.trajectory.t.shape[0]),
                'dof': int(state.trajectory.q.shape[1]),
                'cached_fk': bool(state.trajectory.ee_positions is not None and state.trajectory.joint_positions is not None),
                'cache_status': state.trajectory.cache_status,
                'metadata': dict(state.trajectory.metadata),
                'quality': dict(state.trajectory.quality),
                'feasibility': dict(state.trajectory.feasibility),
            },
            'benchmark_report': None if state.benchmark_report is None else {
                'robot': state.benchmark_report.robot,
                'num_cases': int(state.benchmark_report.num_cases),
                'success_rate': float(state.benchmark_report.success_rate),
                'aggregate': dict(state.benchmark_report.aggregate),
                'metadata': dict(state.benchmark_report.metadata),
                'comparison': dict(state.benchmark_report.comparison),
            },
            'playback': {
                'frame_idx': int(state.playback.frame_idx),
                'total_frames': int(state.playback.total_frames),
                'speed_multiplier': float(state.playback.speed_multiplier),
                'loop_enabled': bool(state.playback.loop_enabled),
            },
            'planning_scene': planning_scene_summary,
            'scene_runtime_summary': scene_runtime_summary,
            'scene_fidelity_summary': scene_fidelity_summary,
            'app_state': getattr(state.app_state, 'value', str(state.app_state)),
            'active_task_id': state.active_task_id,
            'active_task_kind': state.active_task_kind,
            'warnings': list(state.warnings),
            'last_error': state.last_error,
            'last_error_payload': dict(state.last_error_payload),
            'last_error_code': state.last_error_code,
            'last_error_title': state.last_error_title,
            'last_error_severity': state.last_error_severity,
            'last_error_hint': state.last_error_hint,
            'active_task_snapshot': None if task_snapshot is None else {
                'task_id': task_snapshot.task_id,
                'task_kind': task_snapshot.task_kind,
                'task_state': task_snapshot.task_state.value,
                'progress_stage': task_snapshot.progress_stage,
                'progress_percent': float(task_snapshot.progress_percent),
                'message': task_snapshot.message,
                'correlation_id': task_snapshot.correlation_id,
                'started_at': None if task_snapshot.started_at is None else task_snapshot.started_at.isoformat(),
                'finished_at': None if task_snapshot.finished_at is None else task_snapshot.finished_at.isoformat(),
                'stop_reason': task_snapshot.stop_reason,
            },
            'scene_revision': int(state.scene_revision),
            'render_runtime': state.render_runtime.as_dict() if hasattr(state.render_runtime, 'as_dict') else dict(state.render_runtime),
            'render_runtime_advice': runtime_advice,
            'capability_matrix': dict(getattr(state, 'capability_matrix', {}) or {}),
            'capability_schema': capability_schema,
            'validation_capabilities': validation_capabilities,
            'module_statuses': dict(getattr(state, 'module_statuses', {}) or {}),
            'render_telemetry': render_telemetry_payload,
        }
        return self.save_json(name, payload)
