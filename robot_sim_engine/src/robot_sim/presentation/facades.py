from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS
from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.domain.error_projection import TaskErrorMapper
from robot_sim.infra.compatibility_usage import record_compatibility_usage
from robot_sim.model.app_config import AppConfig
from robot_sim.model.solver_config import SolverSettings
from robot_sim.presentation.state_store import StateStore

_COMPATIBILITY_SURFACE = 'presentation facade alias adapters'


def _record_facade_usage(adapter: str, operation: str) -> None:
    record_compatibility_usage(_COMPATIBILITY_SURFACE, detail=f'{adapter}:{operation}')


class _CompatibilityWorkflowAdapter:
    """Adapter-only compatibility shell over a canonical workflow service."""

    _adapter_name = 'facade'

    def __init__(self, workflow: Any) -> None:
        self._workflow = workflow

    @property
    def workflow(self) -> Any:
        return self._workflow

    def _delegate(self, operation: str, *args, **kwargs):
        _record_facade_usage(self._adapter_name, operation)
        return getattr(self._workflow, operation)(*args, **kwargs)

    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        _record_facade_usage(self._adapter_name, f'attr:{name}')
        return getattr(self._workflow, name)


@dataclass(frozen=True)
class RuntimeFacade:
    """Narrow runtime surface exposed to the Qt shell."""

    project_root: Path
    resource_root: Path
    config_root: Path
    export_root: Path
    app_config: Mapping[str, object]
    app_settings: AppConfig
    solver_config: Mapping[str, object]
    solver_settings: SolverSettings
    runtime_context: Mapping[str, object] | None
    startup_summary: Mapping[str, object] | None
    state_store: StateStore
    metrics_service: MetricsService
    task_error_mapper: TaskErrorMapper
    capability_service: CapabilityService
    module_status_service: ModuleStatusService
    effective_config_snapshot: Mapping[str, object] | None = None

    @property
    def state(self):
        return self.state_store.state


class RobotFacade(_CompatibilityWorkflowAdapter):
    _adapter_name = 'robot_facade'

    def robot_names(self) -> list[str]:
        return self._delegate('robot_names')

    def robot_entries(self):
        return self._delegate('robot_entries')

    def available_specs(self):
        return self._delegate('available_specs')

    def importer_entries(self):
        return self._delegate('importer_entries')

    def load_robot(self, name: str):
        return self._delegate('load_robot', name)

    def import_robot(self, source: str, importer_id: str | None = None):
        return self._delegate('import_robot', source, importer_id=importer_id)

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        return self._delegate('build_robot_from_editor', existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        return self._delegate('save_current_robot', rows=rows, home_q=home_q, name=name)

    def run_fk(self, q=None):
        return self._delegate('run_fk', q=q)

    def sample_ee_positions(self, q_samples):
        return self._delegate('sample_ee_positions', q_samples)


class SolverFacade(_CompatibilityWorkflowAdapter):
    _adapter_name = 'solver_facade'

    def solver_defaults(self) -> dict[str, object]:
        return self._delegate('solver_defaults')

    def build_target_pose(self, values6, orientation_mode: str = 'rvec'):
        return self._delegate('build_target_pose', values6, orientation_mode=orientation_mode)

    def build_ik_request(self, values6, **kwargs):
        return self._delegate('build_ik_request', values6, **kwargs)

    def apply_ik_result(self, req, result) -> None:
        self._delegate('apply_ik_result', req, result)

    def run_ik(self, values6, **kwargs):
        return self._delegate('run_ik', values6, **kwargs)


class TrajectoryFacade(_CompatibilityWorkflowAdapter):
    _adapter_name = 'trajectory_facade'

    def trajectory_defaults(self) -> dict[str, object]:
        return self._delegate('trajectory_defaults')

    def trajectory_goal_or_raise(self):
        return self._delegate('trajectory_goal_or_raise')

    def build_trajectory_request(self, **kwargs):
        return self._delegate('build_trajectory_request', **kwargs)

    def plan_trajectory(self, **kwargs):
        return self._delegate('plan_trajectory', **kwargs)

    def apply_trajectory(self, traj) -> None:
        self._delegate('apply_trajectory', traj)


class PlaybackFacade(_CompatibilityWorkflowAdapter):
    _adapter_name = 'playback_facade'

    def current_playback_frame(self):
        return self._delegate('current_playback_frame')

    def set_playback_frame(self, frame_idx: int):
        return self._delegate('set_playback_frame', frame_idx)

    def next_playback_frame(self):
        return self._delegate('next_playback_frame')

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None:
        self._delegate('set_playback_options', speed_multiplier=speed_multiplier, loop_enabled=loop_enabled)

    def ensure_playback_ready(self, *, strict: bool = True) -> None:
        self._delegate('ensure_playback_ready', strict=strict)


class BenchmarkFacade(_CompatibilityWorkflowAdapter):
    _adapter_name = 'benchmark_facade'

    def build_benchmark_config(self, **kwargs):
        return self._delegate('build_benchmark_config', **kwargs)

    def run_benchmark(self, config=None):
        return self._delegate('run_benchmark', config=config)


class ExportFacade(_CompatibilityWorkflowAdapter):
    _adapter_name = 'export_facade'

    def export_trajectory_bundle(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        return self._delegate('export_trajectory_bundle', name=name)

    def export_trajectory(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        return self._delegate('export_trajectory', name=name)

    def export_trajectory_metrics(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_metrics_name, metrics: dict[str, object] | None = None):
        return self._delegate('export_trajectory_metrics', name=name, metrics=metrics)

    def export_benchmark(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name):
        return self._delegate('export_benchmark', name=name)

    def export_benchmark_cases_csv(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name):
        return self._delegate('export_benchmark_cases_csv', name=name)

    def export_session(self, name: str = DEFAULT_EXPORT_ARTIFACTS.session_name, *, telemetry_detail: str = 'full'):
        return self._delegate('export_session', name=name, telemetry_detail=telemetry_detail)

    def export_package(self, name: str = DEFAULT_EXPORT_ARTIFACTS.package_name, *, telemetry_detail: str = 'minimal'):
        return self._delegate('export_package', name=name, telemetry_detail=telemetry_detail)
