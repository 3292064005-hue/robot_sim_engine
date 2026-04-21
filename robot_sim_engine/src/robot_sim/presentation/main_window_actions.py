from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from robot_sim.presentation.state_events import PlaybackFrameProjectedEvent, PlaybackStateChangedEvent

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowActionView


class MainWindowActionMixin:
    """Action mixin that delegates orchestration to coordinators."""

    def on_load_robot(self: 'MainWindowActionView') -> None:
        """Entry point wired to the robot-load button."""
        self.task_orchestration.robot_coordinator.load_robot()


    def on_save_robot(self: 'MainWindowActionView') -> None:
        """Entry point wired to the robot-save button."""
        self.task_orchestration.robot_coordinator.save_current_robot()


    def on_import_robot(self: 'MainWindowActionView') -> None:
        """Entry point wired to the robot-import button."""
        self.task_orchestration.robot_coordinator.import_robot()


    def on_fill_current_pose(self: 'MainWindowActionView') -> None:
        """Fill the target pose editor from the latest FK result."""
        fk = self._runtime_ops().state.fk_result
        if fk is None:
            return
        self.target_panel.set_from_pose(fk.ee_pose)
        self.status_panel.append('已用当前位姿填充目标')

    def on_run_fk(self: 'MainWindowActionView') -> None:
        """Run a synchronous FK update from the current editor values."""
        robot_ops = self._robot_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            q = np.array(self.robot_panel.edited_home_q(), dtype=float)
            fk = robot_ops.run_fk(q=q)
            self.scene_controller.update_fk_projection(fk, runtime.state.target_pose)
            self.status_panel.summary.setText(f"FK 完成 | p = {np.array2string(fk.ee_pose.p, precision=4)}")
            self.status_panel.append('FK 更新成功')

        self._run_presented(action, title='错误')

    def on_play(self: 'MainWindowActionView') -> None:
        """Entry point wired to the playback play button."""
        self.task_orchestration.playback_task_coordinator.play()


    def on_pause(self: 'MainWindowActionView') -> None:
        """Entry point wired to the playback pause button."""
        self.task_orchestration.playback_task_coordinator.pause()


    def on_stop_playback(self: 'MainWindowActionView') -> None:
        """Entry point wired to the playback stop button."""
        self.task_orchestration.playback_task_coordinator.stop()


    def on_step(self: 'MainWindowActionView') -> None:
        """Advance playback by one frame."""
        playback_ops = self._playback_ops()

        def action() -> None:
            frame = playback_ops.next_playback_frame()
            if frame is not None:
                self._schedule_playback_frame(frame, immediate=True)

        self._run_presented(action, title='错误')

    def on_seek_frame(self: 'MainWindowActionView', idx: int) -> None:
        """Seek playback to an arbitrary frame index."""
        playback_ops = self._playback_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            if runtime.state.trajectory is None:
                return
            frame = playback_ops.set_playback_frame(int(idx))
            self._schedule_playback_frame(frame, live=False, immediate=False)

        self._run_status_projected(action, prefix='拖动播放游标失败')

    def on_playback_speed_changed(self: 'MainWindowActionView', value: float) -> None:
        """Update playback speed from the UI control."""
        self._playback_ops().set_playback_options(speed_multiplier=float(value))
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_loop_changed(self: 'MainWindowActionView', checked: bool) -> None:
        """Update playback looping from the UI control."""
        self._playback_ops().set_playback_options(loop_enabled=bool(checked))
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def _schedule_playback_frame(self: 'MainWindowActionView', frame, *, live: bool = False, immediate: bool = False) -> None:
        """Schedule playback-frame projection through the coalescing render scheduler."""
        scheduler = getattr(self.task_orchestration, 'playback_render_scheduler', None)
        if immediate or scheduler is None:
            self.project_playback_frame(frame, live=live)
            return
        scheduler.schedule(frame, live=live)

    def _apply_playback_frame(self: 'MainWindowActionView', frame) -> None:
        """Apply a single playback frame to the 3D view and playback widgets.

        Args:
            frame: Playback frame carrying cached geometry.

        Returns:
            None: Updates scene and playback widgets in place.

        Raises:
            RuntimeError: If the frame does not carry the cached geometry required by the
                playback contract.

        Boundary behavior:
            Live playback and seek projection no longer fall back to UI-thread FK evaluation.
            Missing cached geometry is treated as a contract violation and surfaced to the
            presentation error boundary instead of being silently recomputed.
        """
        runtime = self._runtime_ops()
        if getattr(frame, 'joint_positions', None) is None or getattr(frame, 'ee_position', None) is None:
            raise RuntimeError('playback frame missing cached geometry')
        self.scene_controller.update_playback_projection(frame.joint_positions, frame.ee_position, runtime.state.target_pose)
        runtime.state_store.dispatch(PlaybackFrameProjectedEvent(q_current=np.asarray(frame.q, dtype=float).copy()))
        total = runtime.state.playback.total_frames
        self.playback_panel.set_frame(frame.frame_idx, total)
        if hasattr(self.plots_manager, 'set_cursor'):
            self.plots_manager.set_cursor('joint_position', float(frame.t))
            self.plots_manager.set_cursor('joint_velocity', float(frame.t))
            self.plots_manager.set_cursor('joint_acceleration', float(frame.t))

    def on_playback_progress(self: 'MainWindowActionView', frame) -> None:
        """Project a streamed playback frame into the coalescing render scheduler."""
        self._schedule_playback_frame(frame, live=True, immediate=False)

    def on_playback_finished(self: 'MainWindowActionView', final_state) -> None:
        """Project playback completion into the UI state."""
        runtime = self._runtime_ops()
        self._set_playback_running(False)
        runtime.state_store.dispatch(PlaybackStateChangedEvent(playback=final_state.pause()))
        self.status_panel.append('播放完成')
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_cancelled(self: 'MainWindowActionView') -> None:
        """Project playback cancellation into the UI state."""
        runtime = self._runtime_ops()
        self._set_playback_running(False)
        if runtime.state.playback.total_frames > 0:
            runtime.state_store.dispatch(PlaybackStateChangedEvent(playback=runtime.state.playback.with_frame(runtime.state.playback.frame_idx).pause()))
        self.status_panel.append('播放已停止')
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_failed(self: 'MainWindowActionView', message: str) -> None:
        """Project playback failure through the shared error boundary."""
        self._set_playback_running(False)
        self._project_exception(message, title='播放失败')

    def on_fit_scene(self: 'MainWindowActionView') -> None:
        """Entry point wired to the scene-fit toolbar action."""
        self.task_orchestration.scene_coordinator.fit()


    def on_clear_scene_path(self: 'MainWindowActionView') -> None:
        """Entry point wired to the scene clear-path toolbar action."""
        self.task_orchestration.scene_coordinator.clear_path()


    def on_capture_scene(self: 'MainWindowActionView') -> None:
        """Entry point wired to the screenshot toolbar action."""
        self.task_orchestration.scene_coordinator.capture()

    def on_add_scene_obstacle(self: 'MainWindowActionView') -> None:
        """Entry point wired to the scene-toolbar add-obstacle action."""
        self.task_orchestration.scene_coordinator.add_obstacle()

    def on_clear_scene_obstacles(self: 'MainWindowActionView') -> None:
        """Entry point wired to the scene-toolbar clear-obstacles action."""
        self.task_orchestration.scene_coordinator.clear_obstacles()


    def on_export_trajectory_bundle(self: 'MainWindowActionView') -> None:
        """Entry point wired to the trajectory-bundle export button."""
        self.task_orchestration.export_task_coordinator.export_trajectory_bundle()

    def on_export_session(self: 'MainWindowActionView') -> None:
        """Entry point wired to the session-export button."""
        self.task_orchestration.export_task_coordinator.export_session()


    def on_export_package(self: 'MainWindowActionView') -> None:
        """Entry point wired to the package-export button."""
        self.task_orchestration.export_task_coordinator.export_package()


    def on_export_benchmark(self: 'MainWindowActionView') -> None:
        """Entry point wired to the benchmark-export button."""
        self.task_orchestration.export_task_coordinator.export_benchmark()

