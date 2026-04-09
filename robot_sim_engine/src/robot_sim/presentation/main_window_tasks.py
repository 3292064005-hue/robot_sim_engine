from __future__ import annotations

from typing import TYPE_CHECKING

from robot_sim.application.workers.playback_worker import PlaybackWorker

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowTaskView


class MainWindowTaskMixin:
    """Task mixin that delegates orchestration to coordinators."""

    def _playback_worker_factory(self: 'MainWindowTaskView', traj):
        """Create the playback worker used by the playback coordinator."""
        playback_ops = self._playback_ops()
        runtime = self._runtime_ops()
        return PlaybackWorker(traj, runtime.state.playback, playback_ops.playback_service)

    def _build_ik_request(self: 'MainWindowTaskView'):
        """Build the current IK request from visible UI state."""
        values = self.target_panel.values6()
        return self._solver_ops().build_ik_request(values, **self._build_solver_kwargs())

    def on_run_ik(self: 'MainWindowTaskView') -> None:
        """Entry point wired to the IK run button."""
        self.ik_task_coordinator.run()


    def on_cancel_ik(self: 'MainWindowTaskView') -> None:
        """Request cooperative cancellation for the active IK task."""
        self.threader.cancel()
        self.status_panel.append('正在请求取消 IK')

    def on_ik_progress(self: 'MainWindowTaskView', log) -> None:
        """Project incremental IK diagnostics into the status panel."""
        self.status_panel.set_metrics(
            iterations=f"A{log.attempt_idx + 1} / {log.iter_idx + 1}",
            pos_err=f"{log.pos_err_norm:.4e}",
            ori_err=f"{log.ori_err_norm:.4e}",
            cond=f"{log.cond_number:.4e}",
            manip=f"{log.manipulability:.4e}",
            dq_norm=f"{log.dq_norm:.4e}",
            mode=log.effective_mode or '-',
            damping=f"{log.damping_lambda:.3e}",
            elapsed=f"{log.elapsed_ms:.1f}",
        )

    def on_ik_finished(self: 'MainWindowTaskView', result) -> None:
        """Handle the terminal IK result through the canonical coordinator path."""
        self.ik_task_coordinator.handle_finished(result)

    def _build_trajectory_request(self: 'MainWindowTaskView'):
        """Build the current trajectory request from visible UI state."""
        return self._trajectory_ops().build_trajectory_request(
            duration=self.solver_panel.traj_duration.value(),
            dt=self.solver_panel.traj_dt.value(),
            mode=self.solver_panel.traj_mode.currentText(),
            target_values6=self.target_panel.values6(),
            orientation_mode=self.target_panel.orientation_mode.currentText(),
            ik_kwargs=self._build_solver_kwargs(),
        )

    def on_plan(self: 'MainWindowTaskView') -> None:
        """Entry point wired to the trajectory-planning button."""
        self.trajectory_task_coordinator.run()


    def on_trajectory_finished(self: 'MainWindowTaskView', traj) -> None:
        """Handle the terminal trajectory result through the canonical coordinator path."""
        self.trajectory_task_coordinator.handle_finished(traj)

    def on_run_benchmark(self: 'MainWindowTaskView') -> None:
        """Entry point wired to the benchmark button."""
        self.benchmark_task_coordinator.run()


    def on_benchmark_finished(self: 'MainWindowTaskView', report) -> None:
        """Handle the terminal benchmark result through the canonical coordinator path."""
        self.benchmark_task_coordinator.handle_finished(report)

    def _on_task_state_changed(self: 'MainWindowTaskView', snapshot) -> None:
        """Route structured task snapshots through the status coordinator."""
        self.status_coordinator.apply_task_snapshot(snapshot)

    def on_worker_failed(self: 'MainWindowTaskView', failure) -> None:
        """Route worker failures through the canonical status coordinator path."""
        self._set_busy(False)
        self.status_coordinator.handle_worker_failure(failure)

    def on_worker_cancelled(self: 'MainWindowTaskView') -> None:
        """Project cooperative task cancellation into the UI state."""
        self._set_busy(False)
        self.status_panel.append('任务已取消')
