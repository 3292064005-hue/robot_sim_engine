from __future__ import annotations

from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.workers.invocation import build_payload_progress_callback, call_with_worker_support
from robot_sim.domain.errors import CancelledTaskError


class IKWorker(BaseWorker):
    """Qt worker wrapper for inverse-kinematics execution."""

    def __init__(self, request: IKRequest, use_case: RunIKUseCase) -> None:
        """Create an IK worker.

        Args:
            request: Immutable inverse-kinematics request.
            use_case: IK use case invoked on the worker thread.

        Returns:
            None: Stores the request and explicit use-case dependency.

        Raises:
            ValueError: If ``use_case`` is not provided.
        """
        super().__init__(task_kind='ik')
        if use_case is None:
            raise ValueError('IKWorker requires an explicit IK use case')
        self._request = request
        self._use_case = use_case

    @Slot()
    def run(self) -> None:
        """Execute the IK use case and emit canonical worker lifecycle events.

        Returns:
            None: Emits started/progress/finished/cancelled/failed signals.

        Raises:
            None: Execution failures are projected through worker failure events.

        Boundary behavior:
            - Cooperative cancellation is checked before and after the use-case call.
            - ``CancelledTaskError`` is normalized to a cancellation event.
            - Legacy results with ``message == 'cancelled'`` remain supported for compatibility.
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
                progress_factory=lambda: build_payload_progress_callback(
                    emit_progress=self.emit_progress,
                    stage='ik',
                    default_message='iterating',
                ),
            )
            if self.is_cancel_requested() or str(getattr(result, 'message', '')).strip().lower() == 'cancelled':
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(result)
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
        except Exception as exc:
            self.emit_failed(exc)
