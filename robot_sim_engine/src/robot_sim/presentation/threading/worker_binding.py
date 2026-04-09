from __future__ import annotations

<<<<<<< HEAD
import logging

from dataclasses import dataclass
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from typing import Callable

from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent, WorkerFinishedEvent
from robot_sim.presentation.threading.task_handle import TaskHandle


<<<<<<< HEAD
_LOG = logging.getLogger(__name__)


def _coerce_progress_payload(event: object) -> object:
    payload = getattr(event, 'payload', None)
    if isinstance(payload, dict) and 'value' in payload and len(payload) == 1:
        return payload['value']
    if payload is not None:
        return payload
    return event


@dataclass(frozen=True)
class WorkerSignalSurface:
    """Explicit description of the structured worker lifecycle signal surface."""

    structured_failed: object | None
    structured_finished: object | None
    structured_cancelled: object | None
    structured_progress: object | None


class WorkerBindingService:
    """Bind worker/thread signals while keeping orchestration callbacks explicit."""

    def __init__(self) -> None:
        pass

=======
class WorkerBindingService:
    """Bind worker/thread signals while keeping orchestration callbacks explicit."""

>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def apply_worker_identity(self, worker, task: TaskHandle) -> None:
        """Populate worker identity attributes when they are available.

        Args:
            worker: Worker object that may expose identity attributes.
            task: Canonical orchestrator task handle.

        Returns:
            None: Mutates worker attributes in place.

        Raises:
            None: Missing identity attributes are ignored for compatibility.
        """
        if getattr(worker, 'task_id', None) is not None:
            worker.task_id = task.task_id
        if getattr(worker, 'task_kind', None) is not None:
            worker.task_kind = task.task_kind
        if getattr(worker, 'correlation_id', None) is not None:
            worker.correlation_id = task.correlation_id or task.task_id

<<<<<<< HEAD
    def inspect_surface(self, worker) -> WorkerSignalSurface:
        """Return the explicit lifecycle signal surface exposed by ``worker``.

        Args:
            worker: Worker instance exposing structured lifecycle signals.

        Returns:
            WorkerSignalSurface: Stable view of the available signal endpoints.

        Raises:
            None: Missing signals simply map to ``None``.
        """
        return WorkerSignalSurface(
            structured_failed=getattr(worker, 'failed_event', None),
            structured_finished=getattr(worker, 'finished_event', None),
            structured_cancelled=getattr(worker, 'cancelled_event', None),
            structured_progress=getattr(worker, 'progress_event', None),
        )

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
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
<<<<<<< HEAD
        on_finished_event: Callable[[WorkerFinishedEvent], None] | None = None,
        on_failed_event: Callable[[WorkerFailedEvent], None] | None = None,
        on_cancelled_event: Callable[[WorkerCancelledEvent], None] | None = None,
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        progress_event_callback: Callable[[object], None],
        state_changed_callback: Callable[[str], None],
        failed_event_callback: Callable[[WorkerFailedEvent], None],
        finished_event_callback: Callable[[WorkerFinishedEvent], None],
        cancelled_event_callback: Callable[[WorkerCancelledEvent], None],
        failed_callback: Callable[[str], None],
        finished_callback: Callable[[object], None],
        cancelled_callback: Callable[[], None],
        queued_callback: Callable[[], None],
        cleanup_callback: Callable[[], None],
        legacy_progress_adapter: Callable[[object], object] | None = None,
    ) -> None:
        """Bind worker lifecycle signals to orchestrator callbacks.

        Args:
            worker: Background worker exposing the legacy or structured signal set.
            thread: Dedicated worker thread.
            on_started: Optional external start callback.
<<<<<<< HEAD
            on_progress: Optional external progress callback receiving normalized structured payloads.
            on_finished: Optional external success callback receiving the structured event payload.
            on_failed: Optional external failure callback receiving the structured event message.
            on_cancelled: Optional external cancellation callback.
            on_finished_event: Optional external structured success callback.
            on_failed_event: Optional external structured failure callback.
            on_cancelled_event: Optional external structured cancellation callback.
=======
            on_progress: Optional external progress callback.
            on_finished: Optional external success callback.
            on_failed: Optional external failure callback.
            on_cancelled: Optional external cancellation callback.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            progress_event_callback: Internal callback for structured progress events.
            state_changed_callback: Internal callback for worker state changes.
            failed_event_callback: Internal callback for structured failure events.
            finished_event_callback: Internal callback for structured success events.
            cancelled_event_callback: Internal callback for structured cancellation events.
<<<<<<< HEAD
            failed_callback: Internal callback receiving structured failure messages.
            finished_callback: Internal callback receiving structured success payloads.
            cancelled_callback: Internal callback invoked for structured cancellations.
            queued_callback: Internal callback invoked when the worker starts running.
            cleanup_callback: Cleanup callback invoked after thread shutdown.
            legacy_progress_adapter: Optional adapter translating structured events to external callback payloads.
=======
            failed_callback: Internal callback for legacy failures.
            finished_callback: Internal callback for legacy success payloads.
            cancelled_callback: Internal callback for legacy cancellations.
            queued_callback: Internal callback invoked when the worker starts running.
            cleanup_callback: Cleanup callback invoked after thread shutdown.
            legacy_progress_adapter: Optional adapter translating structured events to legacy progress payloads.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

        Returns:
            None: Mutates Qt signal bindings in place.

        Raises:
            None: Binding is side-effect only.
        """
        try:
            worker.moveToThread(thread)
        except TypeError:
<<<<<<< HEAD
            _LOG.debug('worker.moveToThread skipped for non-QThread test double', exc_info=True)
        thread.started.connect(worker.run)
        worker.started.connect(queued_callback)
        surface = self.inspect_surface(worker)

        if surface.structured_failed is not None:
            surface.structured_failed.connect(failed_event_callback)
            surface.structured_failed.connect(lambda event: failed_callback(getattr(event, 'message', str(event))))
            if on_failed_event is not None:
                surface.structured_failed.connect(on_failed_event)

        if surface.structured_finished is not None:
            surface.structured_finished.connect(finished_event_callback)
            surface.structured_finished.connect(lambda event: finished_callback(getattr(event, 'payload', event)))
            if on_finished_event is not None:
                surface.structured_finished.connect(on_finished_event)

        if surface.structured_cancelled is not None:
            surface.structured_cancelled.connect(cancelled_event_callback)
            surface.structured_cancelled.connect(lambda _event: cancelled_callback())
            if on_cancelled_event is not None:
                surface.structured_cancelled.connect(on_cancelled_event)

        if surface.structured_progress is not None:
            surface.structured_progress.connect(progress_event_callback)

        adapter = legacy_progress_adapter or _coerce_progress_payload
        if on_progress is not None and surface.structured_progress is not None:
            surface.structured_progress.connect(lambda event: on_progress(adapter(event)))

        if on_started is not None:
            worker.started.connect(on_started)
        if on_finished is not None and surface.structured_finished is not None:
            surface.structured_finished.connect(lambda event: on_finished(getattr(event, 'payload', event)))
        if on_failed is not None and surface.structured_failed is not None:
            surface.structured_failed.connect(lambda event: on_failed(getattr(event, 'message', str(event))))
        if on_cancelled is not None and surface.structured_cancelled is not None:
            surface.structured_cancelled.connect(lambda _event: on_cancelled())
        if hasattr(worker, 'state_changed'):
            worker.state_changed.connect(state_changed_callback)

        terminal_state = {'quit_requested': False}

        def _quit_thread_once() -> None:
            if terminal_state['quit_requested']:
                return
            terminal_state['quit_requested'] = True
            thread.quit()

        if surface.structured_finished is not None:
            surface.structured_finished.connect(lambda _event: _quit_thread_once())
        if surface.structured_failed is not None:
            surface.structured_failed.connect(lambda _event: _quit_thread_once())
        if surface.structured_cancelled is not None:
            surface.structured_cancelled.connect(lambda _event: _quit_thread_once())

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
=======
            pass
        thread.started.connect(worker.run)
        worker.started.connect(queued_callback)
        if hasattr(worker, 'failed_event'):
            worker.failed_event.connect(failed_event_callback)
        else:
            worker.failed.connect(failed_callback)
        if hasattr(worker, 'finished_event'):
            worker.finished_event.connect(finished_event_callback)
        else:
            worker.finished.connect(finished_callback)
        if hasattr(worker, 'cancelled_event'):
            worker.cancelled_event.connect(cancelled_event_callback)
        else:
            worker.cancelled.connect(cancelled_callback)
        if hasattr(worker, 'progress_event'):
            worker.progress_event.connect(progress_event_callback)
        if on_progress is not None:
            if hasattr(worker, 'progress'):
                worker.progress.connect(on_progress)
            elif hasattr(worker, 'progress_event'):
                adapter = legacy_progress_adapter or self._coerce_legacy_progress
                worker.progress_event.connect(lambda event: on_progress(adapter(event)))
        if hasattr(worker, 'state_changed'):
            worker.state_changed.connect(state_changed_callback)
        if on_started is not None:
            worker.started.connect(on_started)
        if on_finished is not None:
            worker.finished.connect(on_finished)
        if on_failed is not None:
            worker.failed.connect(on_failed)
        if on_cancelled is not None:
            worker.cancelled.connect(on_cancelled)
        worker.finished.connect(lambda _payload: thread.quit())
        worker.failed.connect(lambda _message: thread.quit())
        worker.cancelled.connect(lambda: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(cleanup_callback)

    @staticmethod
    def _coerce_legacy_progress(event):
        """Translate structured progress events into legacy callback payloads."""
        payload = getattr(event, 'payload', None)
        if isinstance(payload, dict) and 'value' in payload and len(payload) == 1:
            return payload['value']
        if payload is not None:
            return payload
        return event
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
