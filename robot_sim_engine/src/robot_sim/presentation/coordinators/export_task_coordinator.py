from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, cast

from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS
from robot_sim.application.workers.export_worker import ExportWorker
from robot_sim.domain.errors import CancelledTaskError
from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import ExportTaskView


class ExportTaskCoordinator:
    """Own export orchestration for the main window.

    The coordinator routes all export work through the shared background task runtime so
    file-system writes, JSON serialization, and package assembly do not block the GUI thread.
    """

    def __init__(self, window: 'ExportTaskView', *, runtime=None, export=None, threader=None, metrics_service=None) -> None:
        self.window = window
        self.runtime = require_dependency(runtime, 'runtime_facade')
        self.export = require_dependency(export, 'export_workflow')
        self.threader = require_dependency(threader, 'threader')
        self.metrics_service = require_dependency(metrics_service, 'metrics_service')

    def export_trajectory_bundle(self) -> None:
        """Queue trajectory bundle + metrics export through the shared worker runtime."""
        self._start_export_task(
            title='导出失败',
            start_message='轨迹包导出任务已启动',
            worker_factory=lambda: ExportWorker(self._export_trajectory_artifacts),
            on_finished=self._project_export_messages,
        )

    def export_trajectory(self) -> None:
        """Compatibility alias for :meth:`export_trajectory_bundle`."""
        self.export_trajectory_bundle()

    def export_session(self) -> None:
        """Queue session export through the shared worker runtime."""
        self._start_export_task(
            title='导出失败',
            start_message='会话导出任务已启动',
            worker_factory=lambda: ExportWorker(self._export_session_artifact),
            on_finished=self._project_export_messages,
        )

    def export_package(self) -> None:
        """Queue package export through the shared worker runtime."""
        self._start_export_task(
            title='导出失败',
            start_message='完整导出包任务已启动',
            worker_factory=lambda: ExportWorker(self._export_package_artifact),
            on_finished=self._project_export_messages,
        )

    def export_benchmark(self) -> None:
        """Queue benchmark report export through the shared worker runtime."""
        self._start_export_task(
            title='导出失败',
            start_message='Benchmark 导出任务已启动',
            worker_factory=lambda: ExportWorker(self._export_benchmark_artifacts),
            on_finished=self._project_export_messages,
        )

    def _start_export_task(
        self,
        *,
        title: str,
        start_message: str,
        worker_factory: Callable[[], ExportWorker],
        on_finished,
    ) -> None:
        """Start an export worker and project the shared task lifecycle."""

        def action() -> None:
            require_view(self.window, 'project_task_started', 'export', start_message)
            task = self.threader.start(
                worker=worker_factory(),
                on_finished=on_finished,
                on_failed=self.window.on_worker_failed,
                on_cancelled=self.window.on_worker_cancelled,
                task_kind='export',
            )
            require_view(self.window, 'project_task_registered', task.task_id, task.task_kind)

        run_presented(self.window, action, title=title)

    @staticmethod
    def _ensure_not_cancelled(cancel_flag) -> None:
        if callable(cancel_flag) and bool(cancel_flag()):
            raise CancelledTaskError('export task cancelled')

    def _export_trajectory_artifacts(self, *, progress_cb=None, cancel_flag=None, correlation_id: str = '') -> dict[str, object]:
        """Export the active trajectory bundle and its derived metrics."""
        if callable(progress_cb):
            progress_cb(5.0, 'collecting trajectory export inputs', {'kind': 'trajectory_bundle', 'correlation_id': correlation_id})
        self._ensure_not_cancelled(cancel_flag)
        path = self.export.export_trajectory_bundle(DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name)
        if callable(progress_cb):
            progress_cb(55.0, 'computing trajectory metrics', {'path': str(path)})
        metrics = self.metrics_service.summarize_trajectory(self.runtime.state.trajectory)
        self._ensure_not_cancelled(cancel_flag)
        metrics_path = self.export.export_trajectory_metrics(DEFAULT_EXPORT_ARTIFACTS.trajectory_metrics_name, metrics)
        if callable(progress_cb):
            progress_cb(100.0, 'trajectory bundle export completed', {'path': str(path), 'metrics_path': str(metrics_path)})
        return {
            'paths': (path, metrics_path),
            'messages': (
                f'轨迹包已导出：{path}',
                f'轨迹指标已导出：{metrics_path}',
            ),
        }

    def _export_session_artifact(self, *, progress_cb=None, cancel_flag=None, correlation_id: str = '') -> dict[str, object]:
        if callable(progress_cb):
            progress_cb(10.0, 'serializing session state', {'kind': 'session', 'correlation_id': correlation_id})
        self._ensure_not_cancelled(cancel_flag)
        path = self.export.export_session(DEFAULT_EXPORT_ARTIFACTS.session_name)
        if callable(progress_cb):
            progress_cb(100.0, 'session export completed', {'path': str(path)})
        return {
            'paths': (path,),
            'messages': (f'会话已导出：{path}',),
        }

    def _export_package_artifact(self, *, progress_cb=None, cancel_flag=None, correlation_id: str = '') -> dict[str, object]:
        if callable(progress_cb):
            progress_cb(10.0, 'assembling package artifact list', {'kind': 'package', 'correlation_id': correlation_id})
        self._ensure_not_cancelled(cancel_flag)
        path = self.export.export_package(DEFAULT_EXPORT_ARTIFACTS.package_name)
        if callable(progress_cb):
            progress_cb(100.0, 'package export completed', {'path': str(path)})
        return {
            'paths': (path,),
            'messages': (f'完整导出包已生成：{path}',),
        }

    def _export_benchmark_artifacts(self, *, progress_cb=None, cancel_flag=None, correlation_id: str = '') -> dict[str, object]:
        if callable(progress_cb):
            progress_cb(5.0, 'serializing benchmark summary', {'kind': 'benchmark', 'correlation_id': correlation_id})
        self._ensure_not_cancelled(cancel_flag)
        json_path = self.export.export_benchmark(DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name)
        if callable(progress_cb):
            progress_cb(60.0, 'serializing benchmark cases csv', {'json_path': str(json_path)})
        self._ensure_not_cancelled(cancel_flag)
        csv_path = self.export.export_benchmark_cases_csv(DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name)
        if callable(progress_cb):
            progress_cb(100.0, 'benchmark export completed', {'json_path': str(json_path), 'csv_path': str(csv_path)})
        return {
            'paths': (json_path, csv_path),
            'messages': (
                f'Benchmark 报告已导出：{json_path}',
                f'Benchmark 明细已导出：{csv_path}',
            ),
        }

    def _project_export_messages(self, payload: dict[str, object]) -> None:
        raw_messages = cast(Iterable[Any], payload.get('messages', ()) or ())
        messages = tuple(str(item) for item in raw_messages)
        if messages:
            require_view(self.window, 'project_export_messages', *messages)
