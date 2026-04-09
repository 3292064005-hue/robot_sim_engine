from __future__ import annotations

<<<<<<< HEAD
from typing import TYPE_CHECKING

from robot_sim.application.workers.trajectory_worker import TrajectoryWorker
from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented, set_plot_curves

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import TrajectoryTaskView

=======
from robot_sim.application.workers.trajectory_worker import TrajectoryWorker
from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented, set_plot_curves

>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

class TrajectoryTaskCoordinator:
    """Own the trajectory task orchestration previously embedded in the window shell."""

<<<<<<< HEAD
    def __init__(self, window: 'TrajectoryTaskView', *, trajectory=None, threader=None) -> None:
        self.window = window
        self.trajectory = require_dependency(trajectory, 'trajectory_facade')
        self.threader = require_dependency(threader, 'threader')
        self._pending_request = None

    def remember_request(self, request) -> object:
        """Store the active trajectory request until terminal projection."""
        self._pending_request = request
        return request

    def pop_pending_request(self):
        """Return and clear the active trajectory request, if any."""
        request = self._pending_request
        self._pending_request = None
        return request
=======
    def __init__(self, window, *, trajectory=None, threader=None) -> None:
        self.window = window
        self.trajectory = require_dependency(trajectory if trajectory is not None else getattr(window, 'trajectory_facade', None), 'trajectory_facade')
        self.threader = require_dependency(threader if threader is not None else getattr(window, 'threader', None), 'threader')
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    def run(self) -> None:
        """Public UI entrypoint for starting a trajectory task."""
        self.start_task()

    def start_task(self) -> None:
        """Start the trajectory worker using the shared background-thread orchestrator."""
        def action() -> None:
            req = require_view(self.window, 'read_trajectory_request')
<<<<<<< HEAD
            self.remember_request(req)
=======
            self.window._pending_traj_request = req
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            require_view(self.window, 'project_task_started', 'trajectory', '轨迹任务已启动')
            trajectory_use_case = require_dependency(getattr(self.trajectory, 'trajectory_use_case', None), 'trajectory_facade.trajectory_use_case')
            task = self.threader.start(
                worker=TrajectoryWorker(req, trajectory_use_case),
                on_finished=self.window.on_trajectory_finished,
                on_failed=self.window.on_worker_failed,
                on_cancelled=self.window.on_worker_cancelled,
                task_kind='trajectory',
            )
            require_view(self.window, 'project_task_registered', task.task_id, task.task_kind)

        run_presented(self.window, action, title='错误')

    def handle_finished(self, traj) -> None:
        """Project a completed trajectory into playback, plots, and diagnostics.

        Boundary behavior:
            - Applies the trajectory into presentation state.
            - Never performs synchronous FK resampling to fabricate missing playback caches.
            - Projects cached end-effector samples only when already present on the trajectory.
        """
        require_view(self.window, 'project_busy_state', False, '')

        def action() -> None:
<<<<<<< HEAD
            self.pop_pending_request()
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            self.trajectory.apply_trajectory(traj)
            ee_points = traj.ee_positions if getattr(traj, 'ee_positions', None) is not None else None
            metrics = self.window.metrics_service.summarize_trajectory(traj)
            require_view(self.window, 'project_trajectory_result', traj, metrics, ee_points)
            set_plot_curves(
                self.window,
                'joint_position',
                tuple((f'q{i}', traj.t, traj.q[:, i]) for i in range(traj.q.shape[1])),
                clear_first=True,
            )
            set_plot_curves(
                self.window,
                'joint_velocity',
                tuple((f'qd{i}', traj.t, traj.qd[:, i]) for i in range(traj.qd.shape[1])),
                clear_first=True,
            )
            set_plot_curves(
                self.window,
                'joint_acceleration',
                tuple((f'qdd{i}', traj.t, traj.qdd[:, i]) for i in range(traj.qdd.shape[1])),
                clear_first=True,
            )

        run_presented(self.window, action, title='错误')
