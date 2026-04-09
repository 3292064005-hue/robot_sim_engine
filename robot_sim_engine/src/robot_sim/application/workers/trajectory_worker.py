from __future__ import annotations

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.workers.invocation import build_structured_progress_callback, call_with_worker_support
from robot_sim.domain.errors import CancelledTaskError


class TrajectoryWorker(BaseWorker):
    """Qt worker wrapper for the trajectory planning use case."""

    def __init__(self, request: TrajectoryRequest, use_case: PlanTrajectoryUseCase) -> None:
        """Create a trajectory worker.

        Args:
            request: Immutable trajectory planning request.
            use_case: Planning use case invoked on the worker thread.

        Returns:
            None: Stores the request and explicit use-case dependency.

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
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
        except Exception as exc:
            self.emit_failed(exc)
