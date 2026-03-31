from __future__ import annotations
from pathlib import Path
import numpy as np

from robot_sim.application.dto import FKRequest, IKRequest, TrajectoryRequest
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.playback_service import PlaybackService, PlaybackFrame
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.core.math.so3 import exp_so3
from robot_sim.core.math.transforms import rot_x, rot_y, rot_z
from robot_sim.domain.enums import IKSolverMode
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.validators.input_validator import InputValidator
from robot_sim.presentation.state_store import StateStore


class MainController:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.registry = RobotRegistry(self.project_root / "configs" / "robots")
        self.exporter = ExportService(self.project_root / "exports")
        self.state_store = StateStore(SessionState())
        self.fk_uc = RunFKUseCase()
        self.ik_uc = RunIKUseCase()
        self.traj_uc = PlanTrajectoryUseCase()
        self.save_session_uc = SaveSessionUseCase(self.exporter)
        self.playback_service = PlaybackService()
        self.playback_uc = StepPlaybackUseCase(self.playback_service)

    @property
    def state(self) -> SessionState:
        return self.state_store.state

    def robot_names(self) -> list[str]:
        return self.registry.list_names()

    def available_specs(self) -> list[RobotSpec]:
        return self.registry.list_specs()

    def load_robot(self, name: str):
        spec = self.registry.load(name)
        fk = self.fk_uc.execute(FKRequest(spec, spec.home_q.copy()))
        self.state_store.patch(
            robot_spec=spec,
            q_current=spec.home_q.copy(),
            fk_result=fk,
            target_pose=None,
            ik_result=None,
            trajectory=None,
            playback=PlaybackState(),
            last_error="",
            last_warning="",
        )
        return fk

    def build_robot_from_editor(self, existing_spec: RobotSpec | None, rows, home_q) -> RobotSpec:
        if existing_spec is None:
            raise RuntimeError("robot not loaded")
        home_q = np.asarray(home_q, dtype=float)
        home_q = InputValidator.validate_home_q(rows, home_q)
        return RobotSpec(
            name=existing_spec.name,
            dh_rows=tuple(rows),
            base_T=existing_spec.base_T,
            tool_T=existing_spec.tool_T,
            home_q=home_q,
            display_name=existing_spec.display_name,
            description=existing_spec.description,
            metadata=dict(existing_spec.metadata),
        )

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        spec = self.state.robot_spec
        if spec is None:
            raise RuntimeError("robot not loaded")
        if rows is not None or home_q is not None:
            rows_in = rows if rows is not None else spec.dh_rows
            home_q_in = home_q if home_q is not None else spec.home_q
            spec = self.build_robot_from_editor(rows=rows_in, home_q=home_q_in, existing_spec=spec)
            self.state_store.patch(robot_spec=spec)
        return self.registry.save(spec, name=name)

    def run_fk(self, q=None):
        spec = self.state.robot_spec
        q_current = self.state.q_current if q is None else np.asarray(q, dtype=float)
        if spec is None or q_current is None:
            raise RuntimeError("robot not loaded")
        q_current = InputValidator.validate_joint_vector(spec, q_current, clamp=False)
        self.state_store.patch(q_current=q_current.copy())
        fk = self.fk_uc.execute(FKRequest(spec, q_current))
        self.state_store.patch(fk_result=fk)
        return fk

    def build_target_pose(self, values6, orientation_mode: str = "rvec"):
        values6 = InputValidator.validate_target_values(values6)
        p = np.asarray(values6[:3], dtype=float)
        if orientation_mode == "euler_zyx":
            yaw, pitch, roll = values6[3:]
            R = rot_z(float(yaw)) @ rot_y(float(pitch)) @ rot_x(float(roll))
        else:
            R = exp_so3(np.asarray(values6[3:], dtype=float))
        return Pose(p=p, R=R)

    def build_ik_request(
        self,
        values6,
        *,
        orientation_mode: str = "rvec",
        mode: str = "dls",
        max_iters: int = 150,
        step_scale: float = 0.5,
        damping: float = 0.05,
        enable_nullspace: bool = True,
        position_only: bool = False,
        pos_tol: float = 1e-4,
        ori_tol: float = 1e-4,
        max_step_norm: float = 0.35,
        auto_fallback: bool = True,
    ) -> IKRequest:
        spec = self.state.robot_spec
        q0 = self.state.q_current
        if spec is None or q0 is None:
            raise RuntimeError("robot not loaded")
        target = self.build_target_pose(values6, orientation_mode=orientation_mode)
        config = IKConfig(
            mode=IKSolverMode(mode),
            max_iters=int(max_iters),
            step_scale=float(step_scale),
            damping_lambda=float(damping),
            enable_nullspace=bool(enable_nullspace),
            position_only=bool(position_only),
            pos_tol=float(pos_tol),
            ori_tol=float(ori_tol),
            max_step_norm=float(max_step_norm),
            fallback_to_dls_when_singular=bool(auto_fallback),
        )
        return IKRequest(spec, target, q0.copy(), config)

    def apply_ik_result(self, req: IKRequest, result) -> None:
        self.state_store.patch(
            target_pose=req.target,
            ik_result=result,
            q_current=result.q_sol.copy(),
            last_error="" if result.success else result.message,
            last_warning="" if result.success else result.message,
        )
        self.state_store.patch(fk_result=self.fk_uc.execute(FKRequest(req.spec, self.state.q_current)))

    def run_ik(self, values6, **kwargs):
        req = self.build_ik_request(values6, **kwargs)
        result = self.ik_uc.execute(req)
        self.apply_ik_result(req, result)
        return result

    def build_trajectory_request(self, q_goal, duration=3.0, dt=0.02) -> TrajectoryRequest:
        if self.state.q_current is None or self.state.robot_spec is None:
            raise RuntimeError("robot not loaded")
        duration, dt = InputValidator.validate_duration_and_dt(duration, dt)
        q_goal = InputValidator.validate_joint_vector(self.state.robot_spec, q_goal, clamp=True)
        return TrajectoryRequest(self.state.q_current.copy(), np.asarray(q_goal, dtype=float), duration, dt)

    def plan_trajectory(self, q_goal, duration=3.0, dt=0.02):
        req = self.build_trajectory_request(q_goal=q_goal, duration=duration, dt=dt)
        result = self.traj_uc.execute(req)
        self.state_store.patch(
            trajectory=result,
            playback=self.playback_service.build_state(result, frame_idx=0, speed_multiplier=self.state.playback.speed_multiplier, loop_enabled=self.state.playback.loop_enabled),
        )
        return result

    def apply_trajectory(self, traj) -> None:
        self.state_store.patch(
            trajectory=traj,
            playback=self.playback_service.build_state(traj, frame_idx=0, speed_multiplier=self.state.playback.speed_multiplier, loop_enabled=self.state.playback.loop_enabled),
        )

    def current_playback_frame(self) -> PlaybackFrame:
        if self.state.trajectory is None:
            raise RuntimeError("trajectory not available")
        return self.playback_uc.current(self.state.trajectory, self.state.playback)

    def set_playback_frame(self, frame_idx: int) -> PlaybackFrame:
        if self.state.trajectory is None:
            raise RuntimeError("trajectory not available")
        state = self.state.playback.with_frame(frame_idx)
        frame = self.playback_service.frame(self.state.trajectory, state.frame_idx)
        self.state_store.patch(playback=state)
        return frame

    def next_playback_frame(self) -> PlaybackFrame | None:
        if self.state.trajectory is None:
            raise RuntimeError("trajectory not available")
        state, frame = self.playback_uc.next(self.state.trajectory, self.state.playback)
        self.state_store.patch(playback=state)
        return frame

    def set_playback_options(self, *, speed_multiplier: float | None = None, loop_enabled: bool | None = None) -> None:
        playback = self.state.playback
        if speed_multiplier is not None:
            playback = PlaybackState(
                is_playing=playback.is_playing,
                frame_idx=playback.frame_idx,
                total_frames=playback.total_frames,
                speed_multiplier=max(float(speed_multiplier), 0.05),
                loop_enabled=playback.loop_enabled if loop_enabled is None else bool(loop_enabled),
            )
        elif loop_enabled is not None:
            playback = PlaybackState(
                is_playing=playback.is_playing,
                frame_idx=playback.frame_idx,
                total_frames=playback.total_frames,
                speed_multiplier=playback.speed_multiplier,
                loop_enabled=bool(loop_enabled),
            )
        self.state_store.patch(playback=playback)

    def export_trajectory(self, name: str = "trajectory.csv"):
        traj = self.state.trajectory
        if traj is None:
            raise RuntimeError("trajectory not available")
        return self.exporter.save_trajectory(name, traj.t, traj.q, traj.qd, traj.qdd)

    def sample_ee_positions(self, q_samples) -> np.ndarray:
        spec = self.state.robot_spec
        if spec is None:
            raise RuntimeError("robot not loaded")
        pts = []
        for q in np.asarray(q_samples, dtype=float):
            fk = self.fk_uc.execute(FKRequest(spec, np.asarray(q, dtype=float)))
            pts.append(np.asarray(fk.ee_pose.p, dtype=float))
        return np.asarray(pts, dtype=float)

    def export_session(self, name: str = "session.json"):
        return self.save_session_uc.execute(name, self.state)
