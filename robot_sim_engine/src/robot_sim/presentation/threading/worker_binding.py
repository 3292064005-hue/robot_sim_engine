from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Callable

from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent, WorkerFinishedEvent
from robot_sim.presentation.threading.task_handle import TaskHandle


_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerSignalSurface:
    """Explicit description of the canonical worker lifecycle signal surface."""

    failed: object | None
    finished: object | None
    cancelled: object | None
    progress: object | None


class WorkerBindingService:
    """Bind worker/thread signals while keeping orchestration callbacks explicit."""

    def apply_worker_identity(self, worker, task: TaskHandle) -> None:
        """Populate worker identity attributes when they are available.

        Args:
            worker: Worker object that may expose identity attributes.
            task: Canonical orchestrator task handle.

        Returns:
            None: Mutates worker attributes in place.

        Raises:
            None: Missing identity attributes are ignored.
        """
        if getattr(worker, 'task_id', None) is not None:
            worker.task_id = task.task_id
        if getattr(worker, 'task_kind', None) is not None:
            worker.task_kind = task.task_kind
        if getattr(worker, 'correlation_id', None) is not None:
            worker.correlation_id = task.correlation_id or task.task_id

    def inspect_surface(self, worker) -> WorkerSignalSurface:
        """Return the canonical lifecycle signal surface exposed by ``worker``.

        Args:
            worker: Worker instance exposing structured lifecycle signals.

        Returns:
            WorkerSignalSurface: Stable view of the available signal endpoints.

        Raises:
            None: Missing signals simply map to ``None``.
        """
        return WorkerSignalSurface(
            failed=getattr(worker, 'failed_event', None),
            finished=getattr(worker, 'finished_event', None),
            cancelled=getattr(worker, 'cancelled_event', None),
            progress=getattr(worker, 'progress_event', None),
        )

    @staticmethod
    def _coerce_progress_payload(event: object) -> object:
        """Project a structured progress event onto the simple callback payload.

        Args:
            event: Structured progress event emitted by a worker.

        Returns:
            object: The canonical payload projected for ``on_progress`` callbacks.

        Raises:
            None: Unsupported payload shapes fall back to the event itself.

        Boundary behavior:
            When the structured payload contains only ``{'value': ...}``, the
            single value is unwrapped for the simple progress callback surface.
        """
        payload = getattr(event, 'payload', None)
        if isinstance(payload, dict) and 'value' in payload and len(payload) == 1:
            return payload['value']
        if payload is not None:
            return payload
        return event

    def bind(
        self,
        *,
        worker,
        thread,
        on_started=None,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        on_finished_event: Callable[[WorkerFinishedEvent], None] | None = None,
        on_failed_event: Callable[[WorkerFailedEvent], None] | None = None,
        on_cancelled_event: Callable[[WorkerCancelledEvent], None] | None = None,
        progress_event_callback: Callable[[object], None],
        state_changed_callback: Callable[[str], None],
        failed_event_callback: Callable[[WorkerFailedEvent], None],
        finished_event_callback: Callable[[WorkerFinishedEvent], None],
        cancelled_event_callback: Callable[[WorkerCancelledEvent], None],
        queued_callback: Callable[[], None],
        cleanup_callback: Callable[[], None],
    ) -> None:
        """Bind worker lifecycle signals to orchestrator callbacks.

        Args:
            worker: Background worker exposing the canonical structured signal set.
            thread: Dedicated worker thread.
            on_started: Optional external start callback.
            on_progress: Optional external simple progress callback.
            on_finished: Optional external simple success callback receiving ``event.payload``.
            on_failed: Optional external simple failure callback receiving ``event.message``.
            on_cancelled: Optional external simple cancellation callback.
            on_finished_event: Optional external structured success callback.
            on_failed_event: Optional external structured failure callback.
            on_cancelled_event: Optional external structured cancellation callback.
            progress_event_callback: Internal callback for structured progress events.
            state_changed_callback: Internal callback for worker state changes.
            failed_event_callback: Internal callback for structured failure events.
            finished_event_callback: Internal callback for structured success events.
            cancelled_event_callback: Internal callback for structured cancellation events.
            queued_callback: Internal callback invoked when the worker starts running.
            cleanup_callback: Cleanup callback invoked after thread shutdown.

        Returns:
            None: Mutates Qt signal bindings in place.

        Raises:
            TypeError: When the worker does not expose the canonical structured terminal signals.
        """
        try:
            worker.moveToThread(thread)
        except TypeError:
            _LOG.debug('worker.moveToThread skipped for non-QThread test double', exc_info=True)
        thread.started.connect(worker.run)
        worker.started.connect(queued_callback)
        surface = self.inspect_surface(worker)

        missing = [
            name
            for name, signal in {
                'finished_event': surface.finished,
                'failed_event': surface.failed,
                'cancelled_event': surface.cancelled,
                'progress_event': surface.progress,
            }.items()
            if signal is None
        ]
        if missing:
            raise TypeError(f'worker is missing canonical lifecycle signals: {", ".join(missing)}')

        surface.failed.connect(failed_event_callback)
        if on_failed_event is not None:
            surface.failed.connect(on_failed_event)

        surface.finished.connect(finished_event_callback)
        if on_finished_event is not None:
            surface.finished.connect(on_finished_event)

        surface.cancelled.connect(cancelled_event_callback)
        if on_cancelled_event is not None:
            surface.cancelled.connect(on_cancelled_event)

        surface.progress.connect(progress_event_callback)

        if on_progress is not None:
            surface.progress.connect(lambda event: on_progress(self._coerce_progress_payload(event)))

        if on_started is not None:
            worker.started.connect(on_started)
        if on_finished is not None:
            surface.finished.connect(lambda event: on_finished(getattr(event, 'payload', event)))
        if on_failed is not None:
            surface.failed.connect(lambda event: on_failed(getattr(event, 'message', str(event))))
        if on_cancelled is not None:
            surface.cancelled.connect(lambda _event: on_cancelled())
        if hasattr(worker, 'state_changed'):
            worker.state_changed.connect(state_changed_callback)

        terminal_state = {'quit_requested': False}

        def _quit_thread_once() -> None:
            if terminal_state['quit_requested']:
                return
            terminal_state['quit_requested'] = True
            thread.quit()

        surface.finished.connect(lambda _event: _quit_thread_once())
        surface.failed.connect(lambda _event: _quit_thread_once())
        surface.cancelled.connect(lambda _event: _quit_thread_once())

        def _safe_cleanup() -> None:
            """Run cleanup defensively when the worker thread finishes.

            Any cleanup exception is logged and suppressed so the terminal worker
            event that triggered shutdown remains the canonical task outcome.
            """
            try:
                cleanup_callback()
            except Exception:  # pragma: no cover - exercised in unit tests with the fallback signal shim
                _LOG.exception('worker cleanup callback failed')

        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(_safe_cleanup)
