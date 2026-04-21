from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.application.dto import FKRequest, IKRequest
from robot_sim.application.request_builders import (
    build_execution_graph_descriptor,
    build_ik_config,
    build_ik_request as build_ik_request_contract,
    build_pose_from_values6,
    build_trajectory_request as build_trajectory_request_contract,
    normalize_validation_layers,
)
from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS
from robot_sim.application.services.playback_service import PlaybackFrame, PlaybackService
from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.domain.enums import AppExecutionState, IKSolverMode, TrajectoryMode
from robot_sim.model.imported_robot_result import ImportedRobotResult
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.pose import Pose
from robot_sim.model.runtime_snapshots import EnvironmentSnapshot
from robot_sim.model.solver_config import IKConfig, SolverSettings
from robot_sim.presentation.runtime_projection_service import RuntimeProjectionService
from robot_sim.presentation.trajectory_request_support import build_motion_trajectory_request
from robot_sim.presentation.state_events import (
    BenchmarkReportProjectedEvent,
    FKProjectedEvent,
    IKResultAppliedEvent,
    PlaybackStateChangedEvent,
    TrajectoryAppliedEvent,
    WarningProjectedEvent,
)
from robot_sim.presentation.validators.input_validator import InputValidator
from robot_sim.presentation.view_contracts import ExportWorkflowContract, MotionWorkflowContract, RobotWorkflowContract

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.application.registries.importer_registry import ImporterRegistry
    from robot_sim.application.services.export_service import ExportService
    from robot_sim.application.services.robot_registry import RobotRegistry
    from robot_sim.application.use_cases.export_package import ExportPackageUseCase
    from robot_sim.application.use_cases.export_report import ExportReportUseCase
    from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
    from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
    from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
    from robot_sim.application.use_cases.run_fk import RunFKUseCase
    from robot_sim.application.use_cases.run_ik import RunIKUseCase
    from robot_sim.application.use_cases.save_session import SaveSessionUseCase
    from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
    from robot_sim.app.workflow_facade import ApplicationWorkflowFacade
    from robot_sim.model.benchmark_report import BenchmarkReport
    from robot_sim.model.robot_spec import RobotSpec
    from robot_sim.model.trajectory import JointTrajectory
    from robot_sim.presentation.controllers.robot_controller import RobotController
    from robot_sim.presentation.facades import RuntimeFacade
    from robot_sim.presentation.state_store import StateStore


@dataclass(frozen=True)
class ExportWorkflowService(ExportWorkflowContract):
    """Canonical export capability port for presentation callers."""

    state_store: 'StateStore'
    exporter: 'ExportService'
    export_report_use_case: 'ExportReportUseCase'
    save_session_use_case: 'SaveSessionUseCase'
    export_package_use_case: 'ExportPackageUseCase | None' = None
    runtime_facade: 'RuntimeFacade | None' = None
    application_workflow: 'ApplicationWorkflowFacade | None' = None

    def _application_workflow_or_raise(self):
        if self.application_workflow is None:
            raise RuntimeError('application workflow facade is not configured')
        return self.application_workflow

    def _runtime_export_context(self) -> dict[str, object]:
        runtime = self.runtime_facade
        capability_snapshot = dict(getattr(self.state_store.state, 'capability_matrix', {}) or {})
        if runtime is None:
            return {
                'environment': {},
                'config_snapshot': {},
                'plugin_snapshot': {},
                'capability_snapshot': capability_snapshot,
            }
        runtime_context = dict(getattr(runtime, 'runtime_context', {}) or {})
        startup_summary = dict(getattr(runtime, 'startup_summary', {}) or {})
        plugin_catalog = dict(runtime_context.get('plugin_catalog', {}) or {})
        environment = {
            'project_root': str(getattr(runtime, 'project_root', '')),
            'resource_root': str(getattr(runtime, 'resource_root', '')),
            'config_root': str(getattr(runtime, 'config_root', '')),
            'export_root': str(getattr(runtime, 'export_root', '')),
            'layout_mode': runtime_context.get('layout_mode', ''),
            'startup_mode': startup_summary.get('startup_mode', runtime_context.get('startup_mode', '')),
            'startup_environment': dict(startup_summary.get('startup_environment', runtime_context.get('startup_environment', {})) or {}),
            'runtime_paths': {
                'robot_root': runtime_context.get('robot_root', ''),
                'bundled_robot_root': runtime_context.get('bundled_robot_root', ''),
                'profiles_root': runtime_context.get('profiles_root', ''),
                'plugin_manifest_path': runtime_context.get('plugin_manifest_path', ''),
                'plugin_manifest_paths': list(runtime_context.get('plugin_manifest_paths', ()) or ()),
            },
        }
        config_snapshot = dict(getattr(runtime, 'effective_config_snapshot', {}) or {})
        if not config_snapshot:
            config_snapshot = {
                'profile': runtime_context.get('active_profile', ''),
                'app': dict(getattr(runtime, 'app_config', {}) or {}),
                'solver': dict(getattr(runtime, 'solver_config', {}) or {}),
                'resolution': dict(runtime_context.get('config_resolution', {}) or {}),
            }
        plugin_snapshot = {
            'policy': dict(runtime_context.get('runtime_feature_policy', startup_summary.get('runtime', {}).get('plugin_policy', {})) or {}),
            'catalog_counts': dict(plugin_catalog.get('counts', {}) or {}),
            'runtime_provider_surface_version': 'v1',
            'governance_registrations': list(plugin_catalog.get('governance_entries', plugin_catalog.get('entries', [])) or []),
            'capability_registrations': list(plugin_catalog.get('capability_entries', plugin_catalog.get('entries', [])) or []),
            'registrations': list(plugin_catalog.get('entries', []) or []),
        }
        return {
            'environment': environment,
            'config_snapshot': config_snapshot,
            'plugin_snapshot': plugin_snapshot,
            'capability_snapshot': capability_snapshot,
        }

    def _scene_snapshot(self) -> dict[str, object]:
        planning_scene = getattr(self.state_store.state, 'planning_scene', None)
        if planning_scene is None:
            return {}
        if hasattr(planning_scene, 'summary'):
            return EnvironmentSnapshot.from_scene_summary(planning_scene.summary()).as_dict()
        return EnvironmentSnapshot(
            revision=int(getattr(planning_scene, 'revision', 0) or 0),
            collision_backend=str(getattr(planning_scene, 'collision_backend', 'aabb') or 'aabb'),
            scene_fidelity=str(getattr(planning_scene, 'scene_fidelity', 'unknown') or 'unknown'),
            obstacle_ids=tuple(str(item) for item in getattr(planning_scene, 'obstacle_ids', ()) or ()),
            attached_object_ids=tuple(str(item) for item in getattr(planning_scene, 'attached_object_ids', ()) or ()),
        ).as_dict()

    def export_trajectory_bundle(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        trajectory = self.state_store.state.trajectory
        if trajectory is None:
            raise RuntimeError('trajectory not available')
        robot_id = self.state_store.state.robot_spec.name if self.state_store.state.robot_spec is not None else None
        solver_id = self.state_store.state.ik_result.effective_mode if self.state_store.state.ik_result is not None else None
        planner_id = resolve_planner_metadata(trajectory.metadata)['planner_id']
        workflow = self._application_workflow_or_raise()
        return workflow.export_trajectory_bundle(name, trajectory, robot_id=robot_id, solver_id=solver_id, planner_id=planner_id)

    def export_trajectory_metrics(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_metrics_name, metrics: dict[str, object] | None = None):
        return self.export_report_use_case.metrics_json(name, metrics or {})

    def export_benchmark(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name):
        report = self.state_store.state.benchmark_report
        if report is None:
            raise RuntimeError('benchmark report not available')
        workflow = self._application_workflow_or_raise()
        payload = report.as_dict() if hasattr(report, 'as_dict') else dict(report.__dict__)
        return workflow.export_benchmark_report(name, payload)

    def export_benchmark_cases_csv(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name):
        report = self.state_store.state.benchmark_report
        if report is None:
            raise RuntimeError('benchmark report not available')
        return self.exporter.save_benchmark_cases_csv(name, report)

    def export_session(self, name: str = DEFAULT_EXPORT_ARTIFACTS.session_name, *, telemetry_detail: str = 'full'):
        runtime_context = self._runtime_export_context()
        workflow = self._application_workflow_or_raise()
        return workflow.export_session(
            name,
            self.state_store.state,
            environment=runtime_context['environment'],
            config_snapshot=runtime_context['config_snapshot'],
            plugin_snapshot=runtime_context['plugin_snapshot'],
            capability_snapshot=runtime_context['capability_snapshot'],
            scene_snapshot=self._scene_snapshot(),
            telemetry_detail=telemetry_detail,
        )

    def export_package(self, name: str = DEFAULT_EXPORT_ARTIFACTS.package_name, *, telemetry_detail: str = 'minimal'):
        if self.export_package_use_case is None:
            raise RuntimeError('package export not configured')
        files: list[Path] = []
        if self.state_store.state.trajectory is not None:
            files.append(self.export_trajectory_bundle(DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name))
        if self.state_store.state.benchmark_report is not None:
            files.append(self.export_benchmark(DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name))
            files.append(self.export_benchmark_cases_csv(DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name))
        files.append(self.export_session(DEFAULT_EXPORT_ARTIFACTS.session_name, telemetry_detail=telemetry_detail))
        if not files:
            raise RuntimeError('nothing to export')
        robot_id = self.state_store.state.robot_spec.name if self.state_store.state.robot_spec is not None else None
        solver_id = self.state_store.state.ik_result.effective_mode if self.state_store.state.ik_result is not None else None
        planner_id = None
        if self.state_store.state.trajectory is not None:
            planner_id = resolve_planner_metadata(self.state_store.state.trajectory.metadata)['planner_id']
        runtime_context = self._runtime_export_context()
        workflow = self._application_workflow_or_raise()
        return workflow.export_package(
            name,
            files,
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=planner_id,
            bundle_kind='artifact_bundle',
            bundle_contract='artifact_audit_bundle',
            replayable=False,
            environment=runtime_context['environment'],
            config_snapshot=runtime_context['config_snapshot'],
            scene_snapshot=self._scene_snapshot(),
            plugin_snapshot=runtime_context['plugin_snapshot'],
            capability_snapshot=runtime_context['capability_snapshot'],
        )
