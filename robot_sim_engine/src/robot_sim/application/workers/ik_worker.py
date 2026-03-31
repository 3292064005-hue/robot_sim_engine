from __future__ import annotations
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.run_ik import RunIKUseCase

class IKWorker(BaseWorker):
    def __init__(self, request: IKRequest) -> None:
        super().__init__()
        self._request = request
        self._use_case = RunIKUseCase()

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            result = self._use_case.execute(
                self._request,
                cancel_flag=self.is_cancel_requested,
                progress_cb=self.progress.emit,
            )
            if result.message == "cancelled":
                self.cancelled.emit()
            else:
                self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
