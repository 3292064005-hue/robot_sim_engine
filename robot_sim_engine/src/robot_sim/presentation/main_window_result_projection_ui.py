from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowUIContract


class MainWindowResultProjectionMixin:
    """Task/result projection helpers split out of the main window UI shell.

    The main window still exposes the same public projection methods, but the concrete
    result-handling logic now lives in this dedicated mixin so the stable UI shell can
    stay focused on dependency wiring and view-boundary helpers.
    """

    def _update_diagnostics_from_trajectory(self: 'MainWindowUIContract', metrics: dict[str, object]) -> None:
        """Refresh diagnostics widgets from trajectory summary metrics."""
        panel = self.diagnostics_panel
        collision_summary = metrics.get('collision_summary', {})
        if callable(getattr(panel, 'set_collision_summary', None)):
            panel.set_collision_summary(collision_summary)
        if callable(getattr(panel, 'set_trajectory_summary', None)):
            panel.set_trajectory_summary(metrics)
        if callable(getattr(panel, 'set_sampling_metrics', None)):
            panel.set_sampling_metrics(metrics)
        elif callable(getattr(panel, 'set_values', None)):
            panel.set_values(
                traj_mode=metrics.get('mode', '-'),
                traj_feasible=metrics.get('feasible', '-'),
                traj_reasons=metrics.get('feasibility_reasons', '-'),
                path_length=metrics.get('path_length', '-'),
                jerk_proxy=metrics.get('jerk_proxy', '-'),
                collision_summary=collision_summary,
            )

    def _update_diagnostics_from_benchmark(self: 'MainWindowUIContract', summary: dict[str, object]) -> None:
        """Refresh diagnostics widgets from benchmark summary metrics."""
        panel = self.diagnostics_panel
        if callable(getattr(panel, 'set_benchmark_summary', None)):
            panel.set_benchmark_summary(summary)
        if callable(getattr(panel, 'set_sampling_metrics', None)):
            panel.set_sampling_metrics(summary)
        elif callable(getattr(panel, 'set_values', None)):
            panel.set_values(
                bench_success=summary.get('success_rate', '-'),
                bench_p95=summary.get('p95_elapsed_ms', '-'),
                bench_restarts=summary.get('mean_restarts_used', '-'),
            )

    def _sync_status_after_snapshot(self: 'MainWindowUIContract') -> None:
        """Refresh the status-panel projection from current session state."""
        self._run_status_projected(self._sync_status_after_snapshot_impl, prefix='状态栏快照同步')

    def _sync_status_after_snapshot_impl(self: 'MainWindowUIContract') -> None:
        projection = self._build_status_panel_projection()
        self._apply_status_panel_projection(projection)

    def project_task_started(self: 'MainWindowUIContract', task_kind: str, message: str = '') -> None:
        """Project a task-start event into the status panel."""
        self._set_busy(True, str(task_kind))
        self.status_panel.append(str(message or f'{task_kind} 任务启动'))
        self._sync_status_after_snapshot()

    def project_task_registered(self: 'MainWindowUIContract', task_id: str = '', task_kind: str = '') -> None:
        """Project a task registration update into the status panel."""
        if task_id or task_kind:
            self.status_panel.append(f'任务已登记：{task_kind or "task"}#{task_id or "pending"}')
        self._sync_status_after_snapshot()

    def project_task_snapshot(self: 'MainWindowUIContract', snapshot) -> None:
        """Project a task snapshot refresh into the shared state store and status panel."""
        self._runtime_ops().state_store.patch_task(snapshot)
        self._sync_status_after_snapshot()

    def project_busy_state(self: 'MainWindowUIContract', busy: bool, reason: str = '') -> None:
        """Project the busy-state snapshot into the status panel."""
        self._set_busy(bool(busy), str(reason))
        self._sync_status_after_snapshot()

    def project_playback_started(self: 'MainWindowUIContract') -> None:
        """Project the start of playback into the status panel."""
        self.status_panel.append('播放开始')
        self._sync_status_after_snapshot()

    def project_playback_stopped(self: 'MainWindowUIContract', reason: str = 'stopped', *, reset_frame: bool = False) -> None:
        """Project the end of playback into widgets and diagnostics.

        Args:
            reason: Human-readable playback stop reason.

        Returns:
            None: Updates widgets and projections in place.

        Raises:
            None: This is a pure UI projection path.
        """
        runtime = self._runtime_ops()
        playback = self._playback_ops()
        status_getter = getattr(playback, 'playback_status', None)
        if callable(status_getter):
            status = dict(status_getter() or {})
            index = 0 if reset_frame else int(status.get('index', 0))
            total = int(status.get('total', 0))
        else:
            playback_state = runtime.state.playback
            index = 0 if reset_frame else int(getattr(playback_state, 'frame_idx', 0) or 0)
            total = int(getattr(playback_state, 'total_frames', 0) or 0)
        self.playback_panel.set_frame(index, total)
        frame = getattr(runtime.state, 'playback_frame', None)
        if frame is not None:
            self.scene_controller.update_fk_projection(frame.fk_result, runtime.state.target_pose)
            self.target_panel.set_from_pose(frame.fk_result.ee_pose)
            self.scene_controller.update_joint_markers(frame.joint_positions)
        self.status_panel.append(f'播放停止：{reason}')
        self._sync_status_after_snapshot()

    def project_playback_frame(self: 'MainWindowUIContract', frame, *, live: bool = False) -> None:
        """Project one playback frame into widgets and 3D state."""
        if hasattr(frame, 'fk_result') and getattr(frame, 'fk_result', None) is not None:
            self.scene_controller.update_fk_projection(frame.fk_result, self._runtime_ops().state.target_pose)
            self.target_panel.set_from_pose(frame.fk_result.ee_pose)
            self.scene_controller.update_joint_markers(frame.joint_positions)
            return
        apply_frame = getattr(self, '_apply_playback_frame', None)
        if callable(apply_frame):
            apply_frame(frame)
            return
        raise AttributeError('playback frame missing fk_result and no playback-frame applier is available')

    def project_worker_failure(self: 'MainWindowUIContract', presentation) -> None:
        """Project a mapped worker failure into shared state and UI surfaces."""
        runtime = self._runtime_ops()
        runtime.state_store.patch_error(presentation)
        self._patch_render_runtime_from_presentation(presentation)
        title = str(getattr(presentation, 'title', '') or '后台任务失败')
        message = str(getattr(presentation, 'user_message', '') or title)
        self._show_error(title, message)
        self.status_panel.append(f'{title}：{message}')
        self._sync_status_after_snapshot()

    def project_robot_loaded(self: 'MainWindowUIContract', fk) -> None:
        """Project a freshly loaded robot into the live widgets and scene."""
        runtime = self._runtime_ops()
        self.robot_panel.set_robot_spec(runtime.state.robot_spec)
        self.scene_controller.reset_path()
        self.scene_controller.update_robot_geometry_projection(runtime.state.robot_geometry)
        self.scene_controller.update_planning_scene_projection(runtime.state.planning_scene)
        self.scene_controller.update_fk_projection(fk)
        self.target_panel.set_from_pose(fk.ee_pose)
        self.playback_panel.set_total_frames(0)
        self.benchmark_panel.summary.setText('尚未运行 benchmark')
        self.benchmark_panel.log.clear()
        self.status_panel.summary.setText(f"已加载机器人：{runtime.state.robot_spec.label}")
        self._sync_status_after_snapshot()
        self.status_panel.append('机器人加载完成')

    def project_robot_imported(self: 'MainWindowUIContract', result) -> None:
        """Project a successful robot import into the stable UI shell.

        Args:
            result: Structured imported-robot result returned by the robot controller.

        Returns:
            None: Refreshes the robot catalog selector and projects the newly loaded robot.

        Raises:
            None: View projection is deterministic once the import succeeds.
        """
        if not bool(getattr(result, 'staged_only', False)):
            self.robot_panel.set_robot_entries(self._robot_ops().robot_entries(), selected_name=result.persisted_name)
        else:
            self.robot_panel.set_robot_entries(self._robot_ops().robot_entries())
        self.project_robot_loaded(result.fk_result)
        destination = result.persisted_path.name if getattr(result, 'persisted_path', None) is not None else f"staged:{result.persisted_name}"
        self.status_panel.append(
            f'机器人导入完成：{result.spec.label} -> {destination} | importer={result.importer_id or "auto"} | fidelity={result.fidelity}'
        )
        if bool(getattr(result, 'staged_only', False)):
            self.status_panel.append('当前导入结果仅已加载到运行时，会在后续“保存 YAML”时正式落库。')
        self.status_panel.append(f'导入源文件：{result.source_path}')
        scene_summary = dict(getattr(self._runtime_ops().state, 'scene_summary', {}) or {})
        if scene_summary:
            collision_fidelity = dict(scene_summary.get('collision_fidelity', {}) or {})
            self.status_panel.append(
                '运行时场景已重建：'
                f"backend={scene_summary.get('collision_backend', 'aabb')} "
                f"precision={collision_fidelity.get('precision', 'unknown')} "
                f"geometry_source={scene_summary.get('geometry_source', 'unknown')} "
                f"revision={scene_summary.get('revision', 0)}"
            )
        if not bool(getattr(result, 'geometry_available', False)):
            self.status_panel.append('导入结果未提供独立几何模型；当前场景已退化到运行时生成的近似几何。')
        for warning in getattr(result, 'warnings', ()) or ():
            self.status_panel.append(f'导入警告：{warning}')

    def project_robot_saved(self: 'MainWindowUIContract', path) -> None:
        """Project a successful robot-save result into the status panel."""
        runtime = self._runtime_ops()
        self.robot_panel.set_robot_spec(runtime.state.robot_spec)
        self.scene_controller.reset_path()
        self.scene_controller.update_robot_geometry_projection(runtime.state.robot_geometry)
        self.scene_controller.update_planning_scene_projection(runtime.state.planning_scene)
        if runtime.state.fk_result is not None:
            self.scene_controller.update_fk_projection(runtime.state.fk_result)
            self.target_panel.set_from_pose(runtime.state.fk_result.ee_pose)
        self.status_panel.summary.setText(f"已保存机器人：{runtime.state.robot_spec.label}")
        self._sync_status_after_snapshot()
        self.status_panel.append(f'机器人配置已保存：{path}')

    def project_ik_result(self: 'MainWindowUIContract', result, summary: dict[str, object]) -> None:
        """Project a completed IK solve into summary widgets."""
        runtime = self._runtime_ops()
        fk = runtime.state.fk_result
        self.scene_controller.update_fk_projection(fk, runtime.state.target_pose)
        self.status_panel.summary.setText(
            f"IK {'收敛' if result.success else '失败'} | iters={summary['iterations']} | pos={summary['final_pos_err']:.3e}"
        )
        self.status_panel.set_metrics(
            iterations=summary['iterations'],
            pos_err=f"{summary['final_pos_err']:.4e}",
            ori_err=f"{summary['final_ori_err']:.4e}",
            cond=f"{summary['final_cond']:.4e}",
            manip=f"{summary['final_manipulability']:.4e}",
            dq_norm=f"{summary['final_dq_norm']:.4e}",
            mode=summary['effective_mode'] or '-',
            damping=f"{summary['final_damping']:.3e}",
            stop_reason=summary['stop_reason'] or '-',
            elapsed=f"{summary['elapsed_ms']:.1f}",
            playback=self._playback_status_text(),
            **self._render_runtime_metric_payload(),
        )
        self.status_panel.append(result.message)

    def project_trajectory_result(self: 'MainWindowUIContract', traj, metrics: dict[str, object], ee_points) -> None:
        """Project a completed trajectory into playback widgets and diagnostics.

        Args:
            traj: Planned trajectory already committed into presentation state.
            metrics: Summarized trajectory metrics for status and diagnostics.
            ee_points: Cached end-effector samples when available.

        Returns:
            None: Updates widgets and diagnostics in place.

        Raises:
            RuntimeError: Does not fabricate missing playback caches; unplayable trajectories are
                left in a non-playing state with an explicit status message.

        Boundary behavior:
            This method never triggers action-layer seek callbacks. When playback caches are
            complete it applies frame zero directly; otherwise it keeps the cursor reset without
            performing UI-thread FK recomputation.
        """
        self.playback_panel.set_total_frames(traj.t.shape[0])
        self.playback_panel.set_frame(0, traj.t.shape[0])
        if ee_points is not None:
            import numpy as np

            arr = np.asarray(ee_points, dtype=float)
            if arr.size:
                self.scene_controller.set_trajectory_from_fk_samples(arr)
        self.status_panel.append(f'轨迹已生成：{traj.q.shape[0]} 个采样点')
        self.status_panel.summary.setText(
            f"轨迹完成 | mode={metrics['mode']} | samples={metrics['num_samples']} | duration={metrics['duration']:.2f}s"
        )
        self._sync_status_after_snapshot()
        self._update_diagnostics_from_trajectory(metrics)
        if bool(getattr(traj, 'is_playback_ready', False)):
            frame = self._playback_ops().set_playback_frame(0)
            self._schedule_playback_frame(frame, live=False, immediate=True)
        else:
            self.status_panel.append('轨迹已生成，但播放缓存未准备完成；已禁止实时播放。')

    def project_benchmark_result(self: 'MainWindowUIContract', report, summary: dict[str, object]) -> None:
        """Project a completed benchmark report into diagnostics widgets."""
        self.benchmark_panel.set_report({'num_cases': report.num_cases, 'success_rate': report.success_rate, 'cases': list(report.cases)})
        self._update_diagnostics_from_benchmark(summary)
        self.status_panel.summary.setText(
            f"Benchmark 完成 | cases={summary['num_cases']} | success={summary['success_rate']:.1%}"
        )
        self.status_panel.append('Benchmark 运行完成')

    def project_export_messages(self: 'MainWindowUIContract', *messages: str) -> None:
        """Append one or more export-status messages to the status panel."""
        for message in messages:
            self.status_panel.append(str(message))
