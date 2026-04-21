from __future__ import annotations

from datetime import datetime

from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent, WorkerFinishedEvent
from robot_sim.domain.enums import TaskState


class ThreadOrchestratorStateMixin:
    """Lifecycle/state transition helpers for the stable thread orchestrator."""

    def _on_progress_event(self, event) -> None:
        self._set_state(
            TaskState.RUNNING,
            stage=getattr(event, 'stage', ''),
            percent=float(getattr(event, 'percent', 0.0) or 0.0),
            message=str(getattr(event, 'message', '')),
        )

    def _on_state_changed(self, state: str) -> None:
        if state not in {item.value for item in TaskState}:
            return
        self._set_state(TaskState(state), message=state)

    def _handle_failed_event(self, event: WorkerFailedEvent) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(
            TaskState.FAILED,
            message=str(getattr(event, 'message', '')),
            stop_reason=str(getattr(event, 'stop_reason', '') or 'exception'),
            finished=True,
        )

    def _handle_finished_event(self, event: WorkerFinishedEvent) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(
            TaskState.SUCCEEDED,
            message=str(getattr(event, 'stop_reason', '') or 'completed'),
            stop_reason=str(getattr(event, 'stop_reason', '') or 'completed'),
            finished=True,
            finished_at=getattr(event, 'finished_at', None),
        )

    def _handle_cancelled_event(self, event: WorkerCancelledEvent) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(
            TaskState.CANCELLED,
            message=str(getattr(event, 'message', '') or 'cancelled'),
            stop_reason=str(getattr(event, 'stop_reason', '') or 'cancelled'),
            finished=True,
            finished_at=getattr(event, 'finished_at', None),
        )

    def _on_timeout(self, task_id: str) -> None:
        if self._lifecycle.active_task is None or self._lifecycle.active_task.task_id != str(task_id):
            return
        self._lifecycle.mark_terminal_locked(task_id)
        self._set_state(TaskState.CANCELLED, message='timeout', stop_reason='timeout', finished=True)
        if self._worker is not None:
            self._worker.request_cancel()
            if hasattr(self._worker, 'emit_cancelled'):
                self._worker.emit_cancelled(stop_reason='timeout', message='timeout')
        if self._thread is not None:
            self._runtime_bridge.stop(self._thread, wait=False)

    def _set_state(
        self,
        state: TaskState,
        *,
        stage: str = '',
        percent: float = 0.0,
        message: str = '',
        stop_reason: str = '',
        finished: bool = False,
        finished_at: datetime | None = None,
    ) -> None:
        self._lifecycle.set_state(
            state,
            stage=stage,
            percent=percent,
            message=message,
            stop_reason=stop_reason,
            finished=finished,
            finished_at=finished_at,
        )

    def _cleanup(self, *, expected_thread=None, expected_task_id: str | None = None) -> None:
        if expected_thread is not None and self._thread is not expected_thread:
            return
        if expected_task_id is not None:
            active = self._lifecycle.active_task
            if active is not None and active.task_id != str(expected_task_id):
                return
        self._timeout_supervisor.cancel()
        self._thread = None
        self._worker = None
        self.active_correlation_id = ''
        self._lifecycle.reset_runtime()
        queued = self._queued_start
        self._queued_start = None
        if queued:
            self.start(**queued)
