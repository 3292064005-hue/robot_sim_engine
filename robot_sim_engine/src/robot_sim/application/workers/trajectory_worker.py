from __future__ import annotations

<<<<<<< HEAD
from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.workers.invocation import build_structured_progress_callback, call_with_worker_support
=======
import inspect

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.workers.base import BaseWorker, Slot
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from robot_sim.domain.errors import CancelledTaskError


class TrajectoryWorker(BaseWorker):
    """Qt worker wrapper for the trajectory planning use case."""

    def __init__(self, request: TrajectoryRequest, use_case: PlanTrajectoryUseCase) -> None:
        """Create a trajectory worker.

        Args:
            request: Immutable trajectory planning request.
            use_case: Planning use case invoked on the worker thread.

<<<<<<< HEAD
        Returns:
            None: Stores the request and explicit use-case dependency.

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        Raises:
            ValueError: If ``use_case`` is not provided.
        """
        super().__init__(task_kind='trajectory')
        if use_case is None:
            raise ValueError('TrajectoryWorker requires an explicit trajectory use case')
        self._request = request
        self._use_case = use_case

    @Slot()
    def run(self) -> None:
<<<<<<< HEAD
        """Execute the planning use case and emit terminal worker events.

        Returns:
            None: Emits started/progress/finished/cancelled/failed signals.

        Raises:
            None: Execution failures are projected through worker failure events.

        Boundary behavior:
            - Cooperative cancellation is checked before and after the use-case call.
            - ``CancelledTaskError`` is normalized to a cancellation event.
            - The finished event includes planner metadata when available.
        """
        self.emit_started()
        try:
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            result = call_with_worker_support(
                self._use_case.execute,
                self._request,
                cancel_flag=self.is_cancel_requested,
                correlation_id=self.correlation_id,
                progress_factory=lambda: build_structured_progress_callback(
                    emit_progress=self.emit_progress,
                    stage='trajectory',
                ),
            )
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            result_metadata = getattr(result, 'metadata', {})
            metadata = {'planner_id': str(result_metadata.get('planner_id', ''))} if isinstance(result_metadata, dict) else {}
            self.emit_finished(result, metadata=metadata)
=======
        """Execute the planning use case and emit terminal worker events."""
        self.emit_started()
        try:
            execute = self._use_case.execute
            accepted = set(inspect.signature(execute).parameters)
            kwargs = {}
            if 'cancel_flag' in accepted:
                kwargs['cancel_flag'] = self.is_cancel_requested
            if 'progress_cb' in accepted:
                kwargs['progress_cb'] = lambda percent, message='', payload=None: self.emit_progress(
                    stage='trajectory',
                    percent=float(percent),
                    message=str(message),
                    payload=dict(payload or {}),
                )
            if 'correlation_id' in accepted:
                kwargs['correlation_id'] = self.correlation_id
            result = execute(self._request, **kwargs)
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(result, metadata={'planner_id': getattr(result, 'metadata', {}).get('planner_id', '')})
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
        except Exception as exc:
            self.emit_failed(exc)
