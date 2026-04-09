from __future__ import annotations

from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.workers.invocation import build_structured_progress_callback, call_with_worker_support
from robot_sim.domain.errors import CancelledTaskError


class BenchmarkWorker(BaseWorker):
    """Qt worker wrapper for benchmark execution."""

    def __init__(self, spec, config, use_case: RunBenchmarkUseCase, cases=None) -> None:
        """Create a benchmark worker.

        Args:
            spec: Robot specification to benchmark.
            config: IK configuration used during benchmarking.
            use_case: Benchmark use case instance.
            cases: Optional benchmark case collection.

        Returns:
            None: Stores the benchmark inputs and explicit use-case dependency.

        Raises:
            ValueError: If ``use_case`` is not provided.
        """
        super().__init__(task_kind='benchmark')
        if use_case is None:
            raise ValueError('BenchmarkWorker requires an explicit benchmark use case')
        self._spec = spec
        self._config = config
        self._cases = cases
        self._uc = use_case

    @Slot()
    def run(self) -> None:
        """Execute the benchmark use case and emit terminal worker events.

        Returns:
            None: Emits started/progress/finished/cancelled/failed signals.

        Raises:
            None: Execution failures are projected through worker failure events.

        Boundary behavior:
            - Cooperative cancellation is checked before and after the use-case call.
            - ``CancelledTaskError`` is normalized to a cancellation event.
        """
        self.emit_started()
        try:
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            report = call_with_worker_support(
                self._uc.execute,
                self._spec,
                self._config,
                self._cases,
                cancel_flag=self.is_cancel_requested,
                correlation_id=self.correlation_id,
                progress_factory=lambda: build_structured_progress_callback(
                    emit_progress=self.emit_progress,
                    stage='benchmark',
                ),
            )
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(report)
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
        except Exception as exc:
            self.emit_failed(exc)
