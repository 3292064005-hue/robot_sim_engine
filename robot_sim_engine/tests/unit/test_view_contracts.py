from __future__ import annotations

from types import SimpleNamespace

from robot_sim.presentation.view_contracts import MainWindowTaskView, RuntimeViewContract


class _RuntimeStub:
    state = SimpleNamespace()
    state_store = SimpleNamespace()
    export_root = '/tmp/exports'
    task_error_mapper = SimpleNamespace()


class _TaskViewStub:
    threader = object()
    status_panel = object()
    target_panel = object()
    solver_panel = object()
    benchmark_panel = object()
    scene_controller = object()
    plots_manager = object()
    metrics_service = object()
    ik_task_coordinator = object()
    trajectory_task_coordinator = object()
    benchmark_task_coordinator = object()
    status_coordinator = object()

    def _runtime_ops(self):
        return _RuntimeStub()

    def _solver_ops(self):
        return object()

    def _trajectory_ops(self):
        return object()

    def _playback_ops(self):
        return object()

    def _run_presented(self, callback, *, title: str = '错误'):
        return callback()

    def _set_busy(self, busy: bool, reason: str = '') -> None:
        self.busy = (busy, reason)

    def _build_solver_kwargs(self) -> dict[str, object]:
        return {'mode': 'dls'}

    def _playback_status_text(self) -> str:
        return 'idle'

    def _update_diagnostics_from_benchmark(self, summary: dict[str, object]) -> None:
        self.summary = summary

    def _project_exception(self, exc: Exception | str, *, title: str = '错误') -> None:
        self.last_error = (title, str(exc))

    def project_trajectory_result(self, traj, metrics: dict[str, object], ee_points) -> None:
        self.last_result = (traj, metrics, ee_points)


def test_runtime_view_contract_is_runtime_checkable() -> None:
    assert isinstance(_RuntimeStub(), RuntimeViewContract)


def test_main_window_task_view_protocol_surface_is_runtime_checkable() -> None:
    assert isinstance(_TaskViewStub(), MainWindowTaskView)
