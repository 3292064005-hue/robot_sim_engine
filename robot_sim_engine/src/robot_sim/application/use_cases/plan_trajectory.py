from __future__ import annotations
from robot_sim.application.dto import TrajectoryRequest
from robot_sim.core.trajectory.quintic import QuinticTrajectoryPlanner

class PlanTrajectoryUseCase:
    def __init__(self) -> None:
        self._planner = QuinticTrajectoryPlanner()

    def execute(self, req: TrajectoryRequest):
        return self._planner.plan(req.q_start, req.q_goal, req.duration, req.dt)
