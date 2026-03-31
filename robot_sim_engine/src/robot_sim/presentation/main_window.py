from __future__ import annotations
from pathlib import Path
import numpy as np

from robot_sim.presentation.main_controller import MainController
from robot_sim.presentation.thread_orchestrator import ThreadOrchestrator
from robot_sim.application.workers.ik_worker import IKWorker
from robot_sim.application.workers.trajectory_worker import TrajectoryWorker
from robot_sim.application.workers.playback_worker import PlaybackWorker
from robot_sim.application.services.metrics_service import MetricsService

try:
    from PySide6.QtWidgets import (
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QSplitter,
        QMessageBox,
    )
    from PySide6.QtCore import Qt
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PySide6 is required to launch the GUI.") from exc

from robot_sim.presentation.widgets.robot_config_panel import RobotConfigPanel
from robot_sim.presentation.widgets.target_pose_panel import TargetPosePanel
from robot_sim.presentation.widgets.solver_panel import SolverPanel
from robot_sim.presentation.widgets.status_panel import StatusPanel
from robot_sim.presentation.widgets.plots_panel import PlotsPanel
from robot_sim.presentation.widgets.playback_panel import PlaybackPanel
from robot_sim.render.scene_3d_widget import Scene3DWidget
from robot_sim.render.plots_manager import PlotsManager
from robot_sim.render.scene_controller import SceneController


class MainWindow(QMainWindow):  # pragma: no cover - GUI shell
    def __init__(self, project_root: str | Path):
        super().__init__()
        self.controller = MainController(project_root)
        self.metrics_service = MetricsService()
        self.threader = ThreadOrchestrator(self)
        self.playback_threader = ThreadOrchestrator(self)
        self._pending_ik_request = None
        self._pending_traj_request = None
        self.setWindowTitle("Robot Sim Engine")

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        v_split = QSplitter(Qt.Vertical)
        top_split = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.robot_panel = RobotConfigPanel(self.controller.robot_names())
        self.target_panel = TargetPosePanel()
        self.solver_panel = SolverPanel()
        left_layout.addWidget(self.robot_panel)
        left_layout.addWidget(self.target_panel)
        left_layout.addWidget(self.solver_panel)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.scene_widget = Scene3DWidget()
        self.scene_controller = SceneController(self.scene_widget)
        self.playback_panel = PlaybackPanel()
        center_layout.addWidget(self.scene_widget)
        center_layout.addWidget(self.playback_panel)

        self.status_panel = StatusPanel()
        self.plots_panel = PlotsPanel()
        self.plots_manager = PlotsManager(getattr(self.plots_panel, "plot_widgets", None))

        top_split.addWidget(left)
        top_split.addWidget(center)
        top_split.addWidget(self.status_panel)
        top_split.setSizes([420, 820, 360])

        v_split.addWidget(top_split)
        v_split.addWidget(self.plots_panel)
        v_split.setSizes([700, 260])
        root_layout.addWidget(v_split)

        self.robot_panel.load_button.clicked.connect(self.on_load_robot)
        self.robot_panel.save_button.clicked.connect(self.on_save_robot)
        self.target_panel.fill_current_btn.clicked.connect(self.on_fill_current_pose)
        self.solver_panel.run_fk_btn.clicked.connect(self.on_run_fk)
        self.solver_panel.run_ik_btn.clicked.connect(self.on_run_ik)
        self.solver_panel.cancel_btn.clicked.connect(self.on_cancel_ik)
        self.solver_panel.plan_btn.clicked.connect(self.on_plan)
        self.playback_panel.play_btn.clicked.connect(self.on_play)
        self.playback_panel.pause_btn.clicked.connect(self.on_pause)
        self.playback_panel.stop_btn.clicked.connect(self.on_stop_playback)
        self.playback_panel.step_btn.clicked.connect(self.on_step)
        self.playback_panel.slider.valueChanged.connect(self.on_seek_frame)
        self.playback_panel.speed.valueChanged.connect(self.on_playback_speed_changed)
        self.playback_panel.loop.toggled.connect(self.on_playback_loop_changed)
        self.playback_panel.export_btn.clicked.connect(self.on_export_trajectory)
        self.playback_panel.session_btn.clicked.connect(self.on_export_session)

        self.resize(1680, 980)
        if self.controller.robot_names():
            self.on_load_robot()

    def _set_busy(self, busy: bool, reason: str = "") -> None:
        self.controller.state_store.patch(is_busy=busy, busy_reason=reason)
        self.solver_panel.set_running(busy)
        if not busy:
            self.status_panel.set_metrics(playback=self._playback_status_text())

    def _set_playback_running(self, running: bool) -> None:
        self.playback_panel.set_running(running)
        playback = self.controller.state.playback.play() if running else self.controller.state.playback.pause()
        self.controller.state_store.patch(playback=playback)
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def _playback_status_text(self) -> str:
        pb = self.controller.state.playback
        if pb.total_frames <= 0:
            return "无轨迹"
        return f"{'播放中' if pb.is_playing else '就绪'} @ {pb.speed_multiplier:.1f}x"

    def _trajectory_goal(self) -> np.ndarray:
        spec = self.controller.state.robot_spec
        if spec is None:
            raise RuntimeError("robot not loaded")
        return spec.q_mid()

    def on_load_robot(self):
        try:
            fk = self.controller.load_robot(self.robot_panel.robot_combo.currentText())
            self.robot_panel.set_robot_spec(self.controller.state.robot_spec)
            self.scene_controller.reset_path()
            self.scene_controller.update_fk(fk)
            self.target_panel.set_from_pose(fk.ee_pose)
            self.playback_panel.set_total_frames(0)
            self.status_panel.summary.setText(f"已加载机器人：{self.controller.state.robot_spec.label}")
            self.status_panel.set_metrics(playback=self._playback_status_text())
            self.status_panel.append("机器人加载完成")
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def on_save_robot(self):
        try:
            path = self.controller.save_current_robot(
                rows=self.robot_panel.edited_rows(),
                home_q=self.robot_panel.edited_home_q(),
                name=self.robot_panel.robot_combo.currentText(),
            )
            self.status_panel.append(f"机器人配置已保存：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def on_fill_current_pose(self):
        fk = self.controller.state.fk_result
        if fk is None:
            return
        self.target_panel.set_from_pose(fk.ee_pose)
        self.status_panel.append("已用当前位姿填充目标")

    def on_run_fk(self):
        try:
            q = np.array(self.robot_panel.edited_home_q(), dtype=float)
            fk = self.controller.run_fk(q=q)
            self.scene_controller.update_fk(fk, self.controller.state.target_pose)
            self.status_panel.summary.setText(
                f"FK 完成 | p = {np.array2string(fk.ee_pose.p, precision=4)}"
            )
            self.status_panel.append("FK 更新成功")
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def _build_ik_request(self):
        values = self.target_panel.values6()
        return self.controller.build_ik_request(
            values,
            orientation_mode=self.target_panel.orientation_mode.currentText(),
            mode=self.solver_panel.mode_combo.currentText(),
            max_iters=self.solver_panel.max_iters.value(),
            step_scale=self.solver_panel.step_scale.value(),
            damping=self.solver_panel.damping.value(),
            enable_nullspace=self.solver_panel.enable_nullspace.isChecked(),
            position_only=self.solver_panel.position_only.isChecked(),
            pos_tol=self.solver_panel.pos_tol.value(),
            ori_tol=self.solver_panel.ori_tol.value(),
            max_step_norm=self.solver_panel.max_step_norm.value(),
            auto_fallback=self.solver_panel.auto_fallback.isChecked(),
        )

    def on_run_ik(self):
        try:
            req = self._build_ik_request()
            worker = IKWorker(req)
            self._pending_ik_request = req
            self._set_busy(True, "ik")
            self.status_panel.append("IK 任务已启动")
            self.threader.start(
                worker=worker,
                on_progress=self.on_ik_progress,
                on_finished=self.on_ik_finished,
                on_failed=self.on_worker_failed,
                on_cancelled=self.on_worker_cancelled,
            )
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def on_cancel_ik(self):
        self.threader.cancel()
        self.status_panel.append("正在请求取消 IK")

    def on_ik_progress(self, log):
        self.status_panel.set_metrics(
            iterations=log.iter_idx + 1,
            pos_err=f"{log.pos_err_norm:.4e}",
            ori_err=f"{log.ori_err_norm:.4e}",
            cond=f"{log.cond_number:.4e}",
            manip=f"{log.manipulability:.4e}",
            dq_norm=f"{log.dq_norm:.4e}",
            mode=log.effective_mode or "-",
            elapsed=f"{log.elapsed_ms:.1f}",
        )

    def on_ik_finished(self, result):
        self._set_busy(False)
        try:
            self.controller.apply_ik_result(self._pending_ik_request, result)
            fk = self.controller.state.fk_result
            self.scene_controller.update_fk(fk, self.controller.state.target_pose)
            summary = self.metrics_service.summarize_ik(result)
            self.status_panel.summary.setText(
                f"IK {'收敛' if result.success else '失败'} | iters={summary['iterations']} | pos={summary['final_pos_err']:.3e}"
            )
            self.status_panel.set_metrics(
                iterations=summary["iterations"],
                pos_err=f"{summary['final_pos_err']:.4e}",
                ori_err=f"{summary['final_ori_err']:.4e}",
                cond=f"{summary['final_cond']:.4e}",
                manip=f"{summary['final_manipulability']:.4e}",
                dq_norm=f"{summary['final_dq_norm']:.4e}",
                mode=(result.logs[-1].effective_mode if result.logs else "-"),
                elapsed=f"{summary['elapsed_ms']:.1f}",
                playback=self._playback_status_text(),
            )
            self.status_panel.append(result.message)
            if result.logs:
                x = np.array([log.iter_idx for log in result.logs], dtype=float)
                pos = np.array([log.pos_err_norm for log in result.logs], dtype=float)
                ori = np.array([log.ori_err_norm for log in result.logs], dtype=float)
                cond = np.array([log.cond_number for log in result.logs], dtype=float)
                manip = np.array([log.manipulability for log in result.logs], dtype=float)
                self.plots_manager.clear("ik_error")
                self.plots_manager.clear("condition")
                self.plots_manager.set_curve("ik_error", "position_error", x, pos)
                self.plots_manager.set_curve("ik_error", "orientation_error", x, ori)
                self.plots_manager.set_curve("condition", "condition_number", x, cond)
                self.plots_manager.set_curve("condition", "manipulability", x, manip)
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def _build_trajectory_request(self):
        q_goal = self._trajectory_goal()
        return self.controller.build_trajectory_request(
            q_goal=q_goal,
            duration=self.solver_panel.traj_duration.value(),
            dt=self.solver_panel.traj_dt.value(),
        )

    def on_plan(self):
        try:
            req = self._build_trajectory_request()
            self._pending_traj_request = req
            self._set_busy(True, "trajectory")
            self.status_panel.append("轨迹任务已启动")
            self.threader.start(
                worker=TrajectoryWorker(req),
                on_finished=self.on_trajectory_finished,
                on_failed=self.on_worker_failed,
                on_cancelled=self.on_worker_cancelled,
            )
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def on_trajectory_finished(self, traj):
        self._set_busy(False)
        try:
            self.controller.apply_trajectory(traj)
            self.playback_panel.set_total_frames(traj.t.shape[0])
            self.playback_panel.set_frame(0, traj.t.shape[0])
            self.plots_manager.clear("joint_position")
            self.plots_manager.clear("joint_velocity")
            self.plots_manager.clear("joint_acceleration")
            for i in range(traj.q.shape[1]):
                self.plots_manager.set_curve("joint_position", f"q{i}", traj.t, traj.q[:, i])
                self.plots_manager.set_curve("joint_velocity", f"qd{i}", traj.t, traj.qd[:, i])
                self.plots_manager.set_curve("joint_acceleration", f"qdd{i}", traj.t, traj.qdd[:, i])
            ee_points = self.controller.sample_ee_positions(traj.q)
            if ee_points.size:
                self.scene_controller.set_trajectory_from_fk_samples(ee_points)
            self.status_panel.append(f"轨迹已生成：{traj.q.shape[0]} 个采样点")
            metrics = self.metrics_service.summarize_trajectory(traj)
            self.status_panel.summary.setText(
                f"轨迹完成 | samples={metrics['num_samples']} | duration={metrics['duration']:.2f}s"
            )
            self.status_panel.set_metrics(playback=self._playback_status_text())
            self.on_seek_frame(0)
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def on_play(self):
        try:
            traj = self.controller.state.trajectory
            if traj is None:
                raise RuntimeError("trajectory not available")
            self.controller.set_playback_options(
                speed_multiplier=self.playback_panel.speed.value(),
                loop_enabled=self.playback_panel.loop.isChecked(),
            )
            worker = PlaybackWorker(traj, self.controller.state.playback, frame_interval_ms=max(int(self.solver_panel.traj_dt.value() * 1000), 5))
            self.playback_threader.start(
                worker=worker,
                on_started=lambda: self._set_playback_running(True),
                on_progress=self.on_playback_progress,
                on_finished=self.on_playback_finished,
                on_failed=self.on_playback_failed,
                on_cancelled=self.on_playback_cancelled,
            )
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def on_pause(self):
        self.playback_threader.cancel()

    def on_stop_playback(self):
        self.playback_threader.stop(wait=False)
        self._set_playback_running(False)
        self.on_seek_frame(0)

    def on_step(self):
        try:
            frame = self.controller.next_playback_frame()
            if frame is not None:
                self._apply_playback_frame(frame)
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def on_seek_frame(self, idx: int):
        try:
            if self.controller.state.trajectory is None:
                return
            frame = self.controller.set_playback_frame(int(idx))
            self._apply_playback_frame(frame)
        except Exception:
            pass

    def on_playback_speed_changed(self, value: float):
        self.controller.set_playback_options(speed_multiplier=float(value))
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_loop_changed(self, checked: bool):
        self.controller.set_playback_options(loop_enabled=bool(checked))
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def _apply_playback_frame(self, frame):
        fk = self.controller.run_fk(q=frame.q)
        self.scene_controller.update_fk(fk, self.controller.state.target_pose, append_path=False)
        total = self.controller.state.playback.total_frames
        self.playback_panel.set_frame(frame.frame_idx, total)
        self.plots_manager.set_cursor("joint_position", frame.t)
        self.plots_manager.set_cursor("joint_velocity", frame.t)
        self.plots_manager.set_cursor("joint_acceleration", frame.t)
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_progress(self, frame):
        self.controller.state_store.patch(playback=self.controller.state.playback.with_frame(frame.frame_idx).play())
        self._apply_playback_frame(frame)

    def on_playback_finished(self, final_state):
        self.controller.state_store.patch(playback=final_state.pause())
        self._set_playback_running(False)
        self.status_panel.append("轨迹播放完成")

    def on_playback_cancelled(self):
        self._set_playback_running(False)
        self.status_panel.append("轨迹播放已暂停")

    def on_playback_failed(self, message: str):
        self._set_playback_running(False)
        QMessageBox.critical(self, "播放失败", message)

    def on_export_trajectory(self):
        try:
            path = self.controller.export_trajectory()
            self.status_panel.append(f"轨迹已导出：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def on_export_session(self):
        try:
            path = self.controller.export_session()
            self.status_panel.append(f"会话已导出：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def on_worker_failed(self, message: str):
        self._set_busy(False)
        QMessageBox.critical(self, "后台任务失败", message)

    def on_worker_cancelled(self):
        self._set_busy(False)
        self.status_panel.append("后台任务已取消")
        self.status_panel.summary.setText("状态：任务已取消")
