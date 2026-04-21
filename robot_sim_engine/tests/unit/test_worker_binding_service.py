from __future__ import annotations

from types import SimpleNamespace

from robot_sim.application.workers.base import BaseWorker
from robot_sim.presentation.threading.worker_binding import WorkerBindingService


class _DummyThreadSignal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback) -> None:
        self.callbacks.append(callback)


class _DummyThread:
    def __init__(self) -> None:
        self.started = _DummyThreadSignal()
        self.finished = _DummyThreadSignal()
        self.quit_calls = 0
        self.delete_later_calls = 0

    def quit(self) -> None:
        self.quit_calls += 1

    def deleteLater(self) -> None:
        self.delete_later_calls += 1


class _Worker(BaseWorker):
    def __init__(self) -> None:
        super().__init__(task_kind='demo')
        self.moved_to = None
        self.deleted = False

    def moveToThread(self, thread) -> None:
        self.moved_to = thread

    def deleteLater(self) -> None:
        self.deleted = True

    def run(self) -> None:
        return None


def test_worker_binding_prefers_structured_events_for_external_callbacks():
    worker = _Worker()
    thread = _DummyThread()
    service = WorkerBindingService()
    observed = {'progress': [], 'finished': [], 'failed': [], 'cancelled': 0, 'queued': 0, 'states': []}

    service.bind(
        worker=worker,
        thread=thread,
        on_progress=observed['progress'].append,
        on_finished=observed['finished'].append,
        on_failed=observed['failed'].append,
        on_cancelled=lambda: observed.__setitem__('cancelled', observed['cancelled'] + 1),
        progress_event_callback=lambda event: None,
        state_changed_callback=observed['states'].append,
        failed_event_callback=lambda event: None,
        finished_event_callback=lambda event: None,
        cancelled_event_callback=lambda event: None,
        queued_callback=lambda: observed.__setitem__('queued', observed['queued'] + 1),
        cleanup_callback=lambda: None,
    )

    assert worker.moved_to is thread
    worker.emit_progress(stage='demo', percent=50.0, message='half', payload={'value': 'payload'})
    worker.emit_finished({'done': True})
    worker.emit_failed('boom')
    worker.emit_cancelled()

    assert observed['progress'] == ['payload']
    assert observed['finished'] == [{'done': True}]
    assert observed['failed'] == ['boom']
    assert observed['cancelled'] == 1


class _StructuredSignal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback) -> None:
        self.callbacks.append(callback)

    def emit(self, *args, **kwargs) -> None:
        for callback in list(self.callbacks):
            callback(*args, **kwargs)


class _StructuredOnlyWorker:
    def __init__(self) -> None:
        self.started = _StructuredSignal()
        self.finished_event = _StructuredSignal()
        self.failed_event = _StructuredSignal()
        self.cancelled_event = _StructuredSignal()
        self.progress_event = _StructuredSignal()
        self.state_changed = _StructuredSignal()
        self.moved_to = None
        self.deleted = False
        self.run = lambda: None

    def moveToThread(self, thread) -> None:
        self.moved_to = thread

    def deleteLater(self) -> None:
        self.deleted = True


def test_worker_binding_quits_thread_for_structured_only_workers():
    worker = _StructuredOnlyWorker()
    thread = _DummyThread()
    service = WorkerBindingService()

    service.bind(
        worker=worker,
        thread=thread,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        progress_event_callback=lambda event: None,
        state_changed_callback=lambda state: None,
        failed_event_callback=lambda event: None,
        finished_event_callback=lambda event: None,
        cancelled_event_callback=lambda event: None,
        queued_callback=lambda: None,
        cleanup_callback=lambda: None,
    )

    worker.finished_event.emit(SimpleNamespace(payload='done'))
    assert thread.quit_calls == 1


def test_worker_binding_routes_external_structured_terminal_event_callbacks():
    worker = _Worker()
    thread = _DummyThread()
    service = WorkerBindingService()
    observed = {'finished': [], 'failed': [], 'cancelled': []}

    service.bind(
        worker=worker,
        thread=thread,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        on_finished_event=lambda event: observed['finished'].append(getattr(event, 'payload', None)),
        on_failed_event=lambda event: observed['failed'].append(getattr(event, 'message', '')),
        on_cancelled_event=lambda event: observed['cancelled'].append(getattr(event, 'stop_reason', '')),
        progress_event_callback=lambda event: None,
        state_changed_callback=lambda state: None,
        failed_event_callback=lambda event: None,
        finished_event_callback=lambda event: None,
        cancelled_event_callback=lambda event: None,
        queued_callback=lambda: None,
        cleanup_callback=lambda: None,
    )

    worker.emit_finished({'done': True})
    worker.emit_failed('boom')
    worker.emit_cancelled(stop_reason='cancelled')

    assert observed['finished'] == [{'done': True}]
    assert observed['failed'] == ['boom']
    assert observed['cancelled'] == ['cancelled']


def test_worker_binding_suppresses_cleanup_callback_failures(caplog):
    worker = _Worker()
    thread = _DummyThread()
    service = WorkerBindingService()
    cleanup_calls = {'count': 0}

    def failing_cleanup() -> None:
        cleanup_calls['count'] += 1
        raise RuntimeError('cleanup failed')

    service.bind(
        worker=worker,
        thread=thread,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        progress_event_callback=lambda event: None,
        state_changed_callback=lambda state: None,
        failed_event_callback=lambda event: None,
        finished_event_callback=lambda event: None,
        cancelled_event_callback=lambda event: None,
        queued_callback=lambda: None,
        cleanup_callback=failing_cleanup,
    )

    caplog.set_level('ERROR')
    for callback in thread.finished.callbacks:
        callback()

    assert cleanup_calls['count'] == 1
    assert worker.deleted is True
    assert thread.delete_later_calls == 1
    assert any('worker cleanup callback failed' in record.message for record in caplog.records)


def test_worker_binding_rejects_missing_structured_signals():
    class _MissingSignalsWorker:
        started = _StructuredSignal()

        def moveToThread(self, thread) -> None:
            self.thread = thread

        def deleteLater(self) -> None:
            return None

        def run(self) -> None:
            return None

    worker = _MissingSignalsWorker()
    thread = _DummyThread()
    service = WorkerBindingService()

    try:
        service.bind(
            worker=worker,
            thread=thread,
            on_progress=None,
            on_finished=None,
            on_failed=None,
            on_cancelled=None,
            progress_event_callback=lambda event: None,
            state_changed_callback=lambda state: None,
            failed_event_callback=lambda event: None,
            finished_event_callback=lambda event: None,
            cancelled_event_callback=lambda event: None,
            queued_callback=lambda: None,
            cleanup_callback=lambda: None,
        )
    except TypeError as exc:
        assert 'canonical lifecycle signals' in str(exc)
    else:  # pragma: no cover
        raise AssertionError('expected TypeError for missing structured signal surface')
