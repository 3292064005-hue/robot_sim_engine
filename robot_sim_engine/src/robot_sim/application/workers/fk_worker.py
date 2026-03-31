from __future__ import annotations
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.dto import FKRequest
from robot_sim.application.use_cases.run_fk import RunFKUseCase

class FKWorker(BaseWorker):
    def __init__(self, request: FKRequest) -> None:
        super().__init__()
        self._request = request
        self._use_case = RunFKUseCase()

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            result = self._use_case.execute(self._request)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
