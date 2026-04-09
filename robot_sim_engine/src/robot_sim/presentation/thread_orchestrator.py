from __future__ import annotations

from uuid import uuid4

from robot_sim.domain.enums import TaskState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.presentation.threading import (
    QtThreadRuntimeBridge,
    SubmissionPolicyEngine,
    TaskHandle,
    TaskLifecycleRegistry,
    TimeoutSupervisor,
    WorkerBindingService,
)
from robot_sim.presentation.thread_orchestrator_state import ThreadOrchestratorStateMixin
from robot_sim.presentation.threading.qt_compat import QObject, QThread, Signal


class _ModuleAwareRuntimeBridge(QtThreadRuntimeBridge):
    """Runtime bridge that preserves module-level QThread monkeypatch compatibility."""

    def create_thread(self):
        """Create a worker thread using the module-level QThread symbol."""
        return QThread()


class ThreadOrchestrator(ThreadOrchestratorStateMixin, QObject):  # pragma: no cover - GUI shell
    """Coordinate a single background worker and project structured task state."""

    task_state_changed = Signal(object)

    def __init__(self, parent=None, *, start_policy: str = 'cancel_and_replace'):
        """Initialize the thread orchestrator.

        Args:
            parent: Optional Qt parent object.
            start_policy: Policy used when a new task arrives while one is already active.

        Returns:
            None: Initializes orchestration state.

        Raises:
            None: Construction only initializes internal state.
        """
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._queued_start: dict[str, object] | None = None
        self._lifecycle = TaskLifecycleRegistry(self.task_state_changed.emit)
        self._submission_policy = SubmissionPolicyEngine(start_policy)
        self._timeout_supervisor = TimeoutSupervisor(self)
        self._runtime_bridge = _ModuleAwareRuntimeBridge()
        self._binding_service = WorkerBindingService()
        self.start_policy = str(start_policy)
        self.active_correlation_id: str = ''

    @property
    def worker(self):
        return self._worker

    @property
    def active_task(self) -> TaskHandle | None:
        return self._lifecycle.active_task

    @property
    def active_snapshot(self) -> TaskSnapshot | None:
        return self._lifecycle.last_snapshot

    @property
    def last_terminal_snapshot(self) -> TaskSnapshot | None:
        return self._lifecycle.last_terminal_snapshot

    def is_running(self, *, task_kind: str | None = None) -> bool:
        """Report whether an orchestrated worker is currently active.

        Args:
            task_kind: Optional task family filter.

        Returns:
            bool: ``True`` when a matching active task exists.

        Raises:
            None: The check reads cached in-memory state only.
        """
        if self._thread is None:
            return False
        if task_kind is None or self._lifecycle.active_task is None:
            return True
        return self._lifecycle.active_task.task_kind == str(task_kind)

    def start(
        self,
        worker,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        on_finished_event=None,
        on_failed_event=None,
        on_cancelled_event=None,
        on_started=None,
        *,
        task_kind: str = 'generic',
        task_id: str | None = None,
        correlation_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> TaskHandle:
        """Start a worker under the configured orchestration policy.

        Args:
            worker: Worker instance exposing the legacy/structured signal set.
            on_progress: Optional external progress callback.
            on_finished: Optional external finished callback receiving the legacy payload surface.
            on_failed: Optional external failure callback receiving the legacy message surface.
            on_cancelled: Optional external cancellation callback receiving the legacy no-arg surface.
            on_finished_event: Optional external structured success callback.
            on_failed_event: Optional external structured failure callback.
            on_cancelled_event: Optional external structured cancellation callback.
            on_started: Optional external started callback.
            task_kind: Logical task family.
            task_id: Optional explicit task identifier.
            correlation_id: Optional correlation identifier.
            timeout_ms: Optional timeout in milliseconds.

        Returns:
            TaskHandle: Handle for the active or queued task.

        Raises:
            RuntimeError: If the configured policy rejects the start request.
        """
        pending = {
            'worker': worker,
            'on_progress': on_progress,
            'on_finished': on_finished,
            'on_failed': on_failed,
            'on_cancelled': on_cancelled,
            'on_finished_event': on_finished_event,
            'on_failed_event': on_failed_event,
            'on_cancelled_event': on_cancelled_event,
            'on_started': on_started,
            'task_kind': task_kind,
            'task_id': task_id,
            'correlation_id': correlation_id,
            'timeout_ms': timeout_ms,
        }
        task = TaskHandle(
            task_id=str(task_id or getattr(worker, 'task_id', str(uuid4())) or str(uuid4())),
            task_kind=str(task_kind),
            correlation_id=str(correlation_id or getattr(worker, 'correlation_id', '') or task_id or ''),
        )
        decision = self._submission_policy.decide(is_running=self.is_running())
        if decision == 'reject':
            raise RuntimeError('task already running')
        if decision == 'queue_latest':
            self._queued_start = dict(pending)
            self._binding_service.apply_worker_identity(worker, task)
            return task
        if decision == 'cancel_and_replace':
            replaced_task_id = self._lifecycle.current_task_id()
            self._lifecycle.mark_terminal_locked(replaced_task_id)
            self.stop(wait=False, stop_reason='replaced')
        return self._start_now(task=task, **pending)

    def _start_now(
        self,
        *,
        task: TaskHandle,
        worker,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        on_finished_event=None,
        on_failed_event=None,
        on_cancelled_event=None,
        on_started=None,
        task_kind: str = 'generic',
        task_id: str | None = None,
        correlation_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> TaskHandle:
        """Wire a worker into a dedicated thread and start execution."""
        del task_kind, task_id, correlation_id
        thread = self._runtime_bridge.create_thread()
        self._binding_service.apply_worker_identity(worker, task)
        self._thread = thread
        self._worker = worker
        self._lifecycle.begin(task)
        self.active_correlation_id = self._lifecycle.active_task.correlation_id if self._lifecycle.active_task else ''
        self._timeout_supervisor.cancel()
        self._set_state(TaskState.QUEUED, message='queued')

        def _is_current(bound_task_id: str) -> bool:
            active = self._lifecycle.active_task
            return active is not None and active.task_id == str(bound_task_id)

        def _guard_simple(callback):
            if callback is None:
                return None

            def _wrapped(*args, _bound_task_id=task.task_id, **kwargs):
                if not _is_current(_bound_task_id):
                    return
                return callback(*args, **kwargs)

            return _wrapped

        def _guard_event(callback):
            if callback is None:
                return None

            def _wrapped(event, _bound_task_id=task.task_id):
                event_task_id = str(getattr(event, 'task_id', '') or '')
                if event_task_id and event_task_id != _bound_task_id:
                    return
                if not _is_current(_bound_task_id):
                    return
                return callback(event)

            return _wrapped

        self._binding_service.bind(
            worker=worker,
            thread=thread,
            on_started=_guard_simple(on_started),
            on_progress=_guard_simple(on_progress),
            on_finished=_guard_simple(on_finished),
            on_failed=_guard_simple(on_failed),
            on_cancelled=_guard_simple(on_cancelled),
            on_finished_event=_guard_event(on_finished_event),
            on_failed_event=_guard_event(on_failed_event),
            on_cancelled_event=_guard_event(on_cancelled_event),
            progress_event_callback=_guard_event(self._on_progress_event),
            state_changed_callback=_guard_simple(self._on_state_changed),
            failed_event_callback=_guard_event(self._handle_failed_event),
            finished_event_callback=_guard_event(self._handle_finished_event),
            cancelled_event_callback=_guard_event(self._handle_cancelled_event),
            failed_callback=_guard_simple(self._handle_failed),
            finished_callback=_guard_simple(self._handle_finished),
            cancelled_callback=_guard_simple(self._handle_cancelled),
            queued_callback=_guard_simple(lambda: self._set_state(TaskState.RUNNING, message='running')),
            cleanup_callback=lambda bound_thread=thread, bound_task_id=task.task_id: self._cleanup(
                expected_thread=bound_thread,
                expected_task_id=bound_task_id,
            ),
        )
        self._runtime_bridge.start(thread)
        self._timeout_supervisor.arm(timeout_ms, task_id=task.task_id, callback=self._on_timeout)
        return self._lifecycle.active_task

    def cancel(self) -> None:
        """Request cooperative cancellation from the active worker."""
        if self._worker is not None:
            self._set_state(TaskState.CANCELLING, message='cancelling')
            self._worker.request_cancel()

    def stop(self, wait: bool = True, *, stop_reason: str = 'cancelled') -> None:
        """Stop the active worker thread.

        Args:
            wait: Whether to block until the worker thread exits.
            stop_reason: Stop reason propagated to task snapshots when possible.

        Returns:
            None: Requests worker/thread shutdown and performs cleanup.

        Raises:
            None: Safe to call when no active task exists.
        """
        if self._thread is None:
            return
        active_thread = self._thread
        active_task_id = self._lifecycle.current_task_id()
        if self._worker is not None:
            self._set_state(TaskState.CANCELLING, message='cancelling', stop_reason=stop_reason)
            self._worker.request_cancel()
        self._runtime_bridge.stop(active_thread, wait=wait)
        self._cleanup(expected_thread=active_thread, expected_task_id=active_task_id)

