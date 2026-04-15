from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS


@dataclass(frozen=True)
class RobotWorkflowService:
    """Canonical robot capability port for presentation and task coordinators.

    Historical façade references are intentionally collapsed into this workflow service so
    new presentation code has exactly one robot-domain dependency surface.
    """

    registry: Any
    controller: Any
    importer_registry: Any | None = None

    def robot_names(self) -> list[str]:
        return self.registry.list_names()

    def robot_entries(self):
        return self.registry.list_entries()

    def available_specs(self):
        return self.registry.list_specs()

    def importer_entries(self):
        if self.importer_registry is None:
            return []
        return list(self.importer_registry.descriptors())

    def import_robot(self, source: str, importer_id: str | None = None):
        return self.controller.import_robot(source, importer_id=importer_id)

    def load_robot(self, name: str):
        return self.controller.load_robot(name)

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        return self.controller.build_robot_from_editor(existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        return self.controller.save_current_robot(rows=rows, home_q=home_q, name=name)

    def run_fk(self, q=None):
        return self.controller.run_fk(q=q)

    def sample_ee_positions(self, q_samples):
        return self.controller.sample_ee_positions(q_samples)


@dataclass(frozen=True)
class MotionWorkflowService:
    """Canonical motion capability port consumed by Qt tasks and widgets.

    The workflow is the only stable presentation dependency for IK, trajectory planning,
    playback, and benchmark orchestration. Historical solver/trajectory/playback/benchmark
    façades are intentionally projected as compatibility aliases that point back here.
    """

    solver_settings: Any
    ik_controller: Any
    trajectory_controller: Any
    benchmark_controller: Any
    playback_controller: Any
    playback_service: Any
    ik_use_case: Any
    trajectory_use_case: Any
    benchmark_use_case: Any

    def solver_defaults(self) -> dict[str, object]:
        return self.solver_settings.ik.as_dict()

    def trajectory_defaults(self) -> dict[str, object]:
        return self.solver_settings.trajectory.as_dict()

    def build_target_pose(self, values6, orientation_mode: str = 'rvec'):
        return self.ik_controller.build_target_pose(values6, orientation_mode=orientation_mode)

    def build_ik_request(self, values6, **kwargs):
        return self.ik_controller.build_ik_request(values6, **kwargs)

    def apply_ik_result(self, req, result) -> None:
        self.ik_controller.apply_ik_result(req, result)

    def run_ik(self, values6, **kwargs):
        return self.ik_controller.run_ik(values6, **kwargs)

    def build_benchmark_config(self, **kwargs):
        return self.benchmark_controller.build_benchmark_config(**kwargs)

    def run_benchmark(self, config=None):
        return self.benchmark_controller.run_benchmark(config=config)

    def trajectory_goal_or_raise(self):
        return self.trajectory_controller.trajectory_goal_or_raise()

    def build_trajectory_request(self, **kwargs):
        return self.trajectory_controller.build_trajectory_request(**kwargs)

    def plan_trajectory(self, **kwargs):
        return self.trajectory_controller.plan_trajectory(**kwargs)

    def apply_trajectory(self, traj) -> None:
        self.trajectory_controller.apply_trajectory(traj)

    def current_playback_frame(self):
        return self.playback_controller.current_playback_frame()

    def set_playback_frame(self, frame_idx: int):
        return self.playback_controller.set_playback_frame(frame_idx)

    def next_playback_frame(self):
        return self.playback_controller.next_playback_frame()

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None:
        self.playback_controller.set_playback_options(speed_multiplier=speed_multiplier, loop_enabled=loop_enabled)

    def ensure_playback_ready(self, *, strict: bool = True) -> None:
        self.playback_controller.ensure_playback_ready(strict=strict)


@dataclass(frozen=True)
class ExportWorkflowService:
    """Canonical export capability port for presentation callers.

    Trajectory export is defined in terms of a trajectory bundle artifact. The historical
    ``export_trajectory`` name is preserved only as a compatibility alias to the canonical
    ``export_trajectory_bundle`` operation.
    """

    export_controller: Any

    def export_trajectory_bundle(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        return self.export_controller.export_trajectory_bundle(name=name)

    def export_trajectory(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        return self.export_trajectory_bundle(name=name)

    def export_trajectory_metrics(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_metrics_name, metrics: dict[str, object] | None = None):
        return self.export_controller.export_trajectory_metrics(name=name, metrics=metrics)

    def export_benchmark(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name):
        return self.export_controller.export_benchmark(name=name)

    def export_benchmark_cases_csv(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name):
        return self.export_controller.export_benchmark_cases_csv(name=name)

    def export_session(self, name: str = DEFAULT_EXPORT_ARTIFACTS.session_name, *, telemetry_detail: str = 'full'):
        return self.export_controller.export_session(name=name, telemetry_detail=telemetry_detail)

    def export_package(self, name: str = DEFAULT_EXPORT_ARTIFACTS.package_name, *, telemetry_detail: str = 'minimal'):
        return self.export_controller.export_package(name=name, telemetry_detail=telemetry_detail)
