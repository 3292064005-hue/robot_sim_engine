from __future__ import annotations
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase

class TrajectoryWorker(BaseWorker):
    def __init__(self, request: TrajectoryRequest) -> None:
        super().__init__()
        self._request = request
        self._use_case = PlanTrajectoryUseCase()

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            result = self._use_case.execute(self._request)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
