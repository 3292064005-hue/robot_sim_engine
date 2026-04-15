from __future__ import annotations

from pathlib import Path

from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.presentation.state_store import StateStore


class ExportController:
    """Presentation-facing export controller.

    Trajectory export is defined in terms of a trajectory-bundle artifact. The historical
    ``export_trajectory`` method is preserved only as a compatibility alias to the canonical
    ``export_trajectory_bundle`` operation so callers no longer need to reason about an
    ambiguous CSV-vs-bundle surface.
    """

    def __init__(
        self,
        state_store: StateStore,
        exporter: ExportService,
        export_report_uc: ExportReportUseCase,
        save_session_uc: SaveSessionUseCase,
        export_package_uc: ExportPackageUseCase | None = None,
        *,
        runtime_facade: object | None = None,
    ) -> None:
        """Create the presentation export controller.

        Args:
            state_store: Shared presentation state store.
            exporter: Low-level export service used for direct artifact writes.
            export_report_uc: Report export use case.
            save_session_uc: Session export use case.
            export_package_uc: Optional package export use case.
            runtime_facade: Optional runtime facade used to snapshot resolved config/runtime
                metadata for package/session manifests.

        Returns:
            None: Stores the collaborators for later export operations.

        Raises:
            None: Construction only stores references.
        """
        self._state_store = state_store
        self._exporter = exporter
        self._export_report_uc = export_report_uc
        self._save_session_uc = save_session_uc
        self._export_package_uc = export_package_uc
        self._runtime_facade = runtime_facade

    def _runtime_export_context(self) -> dict[str, object]:
        """Return stable runtime/config/package metadata for export operations.

        The export layer prefers runtime-facade metadata when the fully bootstrapped
        application surface is available. When the controller is used in lightweight
        or test-only contexts without a runtime facade, the method must still preserve
        the session capability matrix so exported session/package manifests remain
        audit-complete instead of silently dropping capability truth.

        Returns:
            dict[str, object]: Environment, config, plugin, and capability snapshots
                suitable for session/package manifests. Missing runtime-facade metadata
                degrades to empty environment/config/plugin snapshots, while capability
                data falls back to the state-store session snapshot.

        Raises:
            None: Missing runtime metadata is handled as a supported degraded mode.
        """
        runtime = self._runtime_facade
        capability_snapshot = dict(getattr(self._state_store.state, 'capability_matrix', {}) or {})
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
            'registrations': list(plugin_catalog.get('entries', []) or []),
        }
        return {
            'environment': environment,
            'config_snapshot': config_snapshot,
            'plugin_snapshot': plugin_snapshot,
            'capability_snapshot': capability_snapshot,
        }

    def _scene_snapshot(self) -> dict[str, object]:
        """Return the current scene snapshot used by package/session manifests."""
        planning_scene = getattr(self._state_store.state, 'planning_scene', None)
        if planning_scene is None:
            return {}
        if hasattr(planning_scene, 'summary'):
            return dict(planning_scene.summary() or {})
        return {
            'revision': int(getattr(planning_scene, 'revision', 0) or 0),
            'collision_backend': str(getattr(planning_scene, 'collision_backend', 'aabb') or 'aabb'),
            'scene_fidelity': str(getattr(planning_scene, 'scene_fidelity', 'unknown') or 'unknown'),
            'obstacle_ids': list(getattr(planning_scene, 'obstacle_ids', ()) or ()),
            'attached_object_ids': list(getattr(planning_scene, 'attached_object_ids', ()) or ()),
        }

    def export_trajectory_bundle(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        """Export the active trajectory bundle using canonical manifest metadata.

        Args:
            name: Destination bundle filename under the export root.

        Returns:
            Path: Written trajectory-bundle path.

        Raises:
            RuntimeError: If no trajectory is available for export.
        """
        traj = self._state_store.state.trajectory
        if traj is None:
            raise RuntimeError('trajectory not available')
        robot_id = self._state_store.state.robot_spec.name if self._state_store.state.robot_spec is not None else None
        solver_id = self._state_store.state.ik_result.effective_mode if self._state_store.state.ik_result is not None else None
        planner_id = resolve_planner_metadata(traj.metadata)['planner_id']
        return self._exporter.save_trajectory_bundle(name, traj, robot_id=robot_id, solver_id=solver_id, planner_id=planner_id)

    def export_trajectory(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        """Compatibility alias for :meth:`export_trajectory_bundle`."""
        return self.export_trajectory_bundle(name=name)

    def export_trajectory_metrics(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_metrics_name, metrics: dict | None = None):
        """Export trajectory metrics as JSON."""
        return self._export_report_uc.metrics_json(name, metrics or {})

    def export_benchmark(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name):
        """Export the active benchmark summary JSON."""
        report = self._state_store.state.benchmark_report
        if report is None:
            raise RuntimeError('benchmark report not available')
        return self._export_report_uc.benchmark_json(name, report)

    def export_benchmark_cases_csv(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name):
        """Export benchmark case rows as CSV."""
        report = self._state_store.state.benchmark_report
        if report is None:
            raise RuntimeError('benchmark report not available')
        return self._exporter.save_benchmark_cases_csv(name, report)

    def export_session(self, name: str = DEFAULT_EXPORT_ARTIFACTS.session_name, *, telemetry_detail: str = 'full'):
        """Export the active session snapshot."""
        runtime_context = self._runtime_export_context()
        return self._save_session_uc.execute(
            name,
            self._state_store.state,
            environment=runtime_context['environment'],
            config_snapshot=runtime_context['config_snapshot'],
            plugin_snapshot=runtime_context['plugin_snapshot'],
            capability_snapshot=runtime_context['capability_snapshot'],
            scene_snapshot=self._scene_snapshot(),
            telemetry_detail=telemetry_detail,
        )

    def export_package(self, name: str = DEFAULT_EXPORT_ARTIFACTS.package_name, *, telemetry_detail: str = 'minimal') -> Path:
        """Export the currently available artifacts as an artifact/audit package bundle."""
        if self._export_package_uc is None:
            raise RuntimeError('package export not configured')
        files: list[Path] = []
        if self._state_store.state.trajectory is not None:
            files.append(self.export_trajectory_bundle(DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name))
        if self._state_store.state.benchmark_report is not None:
            files.append(self.export_benchmark(DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name))
            files.append(self.export_benchmark_cases_csv(DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name))
        files.append(self.export_session(DEFAULT_EXPORT_ARTIFACTS.session_name, telemetry_detail=telemetry_detail))
        if not files:
            raise RuntimeError('nothing to export')
        robot_id = self._state_store.state.robot_spec.name if self._state_store.state.robot_spec is not None else None
        solver_id = self._state_store.state.ik_result.effective_mode if self._state_store.state.ik_result is not None else None
        planner_id = None
        if self._state_store.state.trajectory is not None:
            planner_id = resolve_planner_metadata(self._state_store.state.trajectory.metadata)['planner_id']
        runtime_context = self._runtime_export_context()
        return self._export_package_uc.execute(
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
