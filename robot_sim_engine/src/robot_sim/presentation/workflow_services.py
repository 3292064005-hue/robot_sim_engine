from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RobotWorkflowService:
    """Robot-library and FK workflow grouped away from the main controller."""

    facade: Any

    def robot_names(self) -> list[str]:
        return self.facade.robot_names()

    def robot_entries(self):
        return self.facade.robot_entries()

    def available_specs(self):
        return self.facade.available_specs()

    def importer_entries(self):
        return self.facade.importer_entries()

    def import_robot(self, source: str, importer_id: str | None = None):
        return self.facade.import_robot(source, importer_id=importer_id)

    def load_robot(self, name: str):
        return self.facade.load_robot(name)

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        return self.facade.build_robot_from_editor(existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        return self.facade.save_current_robot(rows=rows, home_q=home_q, name=name)

    def run_fk(self, q=None):
        return self.facade.run_fk(q=q)

    def sample_ee_positions(self, q_samples):
        return self.facade.sample_ee_positions(q_samples)


@dataclass(frozen=True)
class MotionWorkflowService:
    """Motion-planning and playback workflow grouped away from the main controller."""

    solver_facade: Any
    trajectory_facade: Any
    benchmark_facade: Any
    playback_facade: Any
    solver_settings: Any

    def solver_defaults(self) -> dict[str, object]:
        return self.solver_settings.ik.as_dict()

    def trajectory_defaults(self) -> dict[str, object]:
        return self.solver_settings.trajectory.as_dict()

    def build_target_pose(self, values6, orientation_mode: str = 'rvec'):
        return self.solver_facade.build_target_pose(values6, orientation_mode=orientation_mode)

    def build_ik_request(self, values6, **kwargs):
        return self.solver_facade.build_ik_request(values6, **kwargs)

    def apply_ik_result(self, req, result) -> None:
        self.solver_facade.apply_ik_result(req, result)

    def run_ik(self, values6, **kwargs):
        return self.solver_facade.run_ik(values6, **kwargs)

    def build_benchmark_config(self, **kwargs):
        return self.benchmark_facade.build_benchmark_config(**kwargs)

    def run_benchmark(self, config=None):
        return self.benchmark_facade.run_benchmark(config=config)

    def trajectory_goal_or_raise(self):
        return self.trajectory_facade.trajectory_goal_or_raise()

    def build_trajectory_request(self, **kwargs):
        return self.trajectory_facade.build_trajectory_request(**kwargs)

    def plan_trajectory(self, **kwargs):
        return self.trajectory_facade.plan_trajectory(**kwargs)

    def apply_trajectory(self, traj) -> None:
        self.trajectory_facade.apply_trajectory(traj)

    def current_playback_frame(self):
        return self.playback_facade.current_playback_frame()

    def set_playback_frame(self, frame_idx: int):
        return self.playback_facade.set_playback_frame(frame_idx)

    def next_playback_frame(self):
        return self.playback_facade.next_playback_frame()

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None:
        self.playback_facade.set_playback_options(speed_multiplier=speed_multiplier, loop_enabled=loop_enabled)


@dataclass(frozen=True)
class ExportWorkflowService:
    """Export/report/package workflow grouped away from the main controller."""

    export_facade: Any

    def export_trajectory(self, name: str = 'trajectory.csv'):
        return self.export_facade.export_trajectory(name=name)

    def export_trajectory_bundle(self, name: str = 'trajectory_bundle.npz'):
        return self.export_facade.export_trajectory_bundle(name=name)

    def export_trajectory_metrics(self, name: str = 'trajectory_metrics.json', metrics: dict[str, object] | None = None):
        return self.export_facade.export_trajectory_metrics(name=name, metrics=metrics)

    def export_benchmark(self, name: str = 'benchmark_report.json'):
        return self.export_facade.export_benchmark(name=name)

    def export_benchmark_cases_csv(self, name: str = 'benchmark_cases.csv'):
        return self.export_facade.export_benchmark_cases_csv(name=name)

    def export_session(self, name: str = 'session.json'):
        return self.export_facade.export_session(name=name)

    def export_package(self, name: str = 'robot_sim_package.zip'):
        return self.export_facade.export_package(name=name)
