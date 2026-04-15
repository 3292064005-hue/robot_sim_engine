from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from robot_sim.presentation.facades import BenchmarkFacade, ExportFacade, PlaybackFacade, RobotFacade, SolverFacade, TrajectoryFacade


@dataclass(frozen=True)
class RuntimeServiceBundle:
    runtime_facade: Any
    metrics_service: Any
    window_cfg: dict[str, object]


@dataclass(frozen=True)
class WorkflowFacadeBundle:
    """Compatibility facade adapters derived from canonical workflows."""

    robot_facade: RobotFacade
    solver_facade: SolverFacade
    trajectory_facade: TrajectoryFacade
    playback_facade: PlaybackFacade
    benchmark_facade: BenchmarkFacade
    export_facade: ExportFacade

    @classmethod
    def from_workflows(cls, workflows: 'WorkflowServiceBundle') -> 'WorkflowFacadeBundle':
        return cls(
            robot_facade=RobotFacade(workflows.robot_workflow),
            solver_facade=SolverFacade(workflows.motion_workflow),
            trajectory_facade=TrajectoryFacade(workflows.motion_workflow),
            playback_facade=PlaybackFacade(workflows.motion_workflow),
            benchmark_facade=BenchmarkFacade(workflows.motion_workflow),
            export_facade=ExportFacade(workflows.export_workflow),
        )


@dataclass(frozen=True)
class WorkflowServiceBundle:
    robot_workflow: Any
    motion_workflow: Any
    export_workflow: Any


@dataclass(frozen=True)
class TaskOrchestrationBundle:
    threader: Any
    playback_threader: Any
    playback_render_scheduler: Any
    robot_coordinator: Any
    ik_task_coordinator: Any
    trajectory_task_coordinator: Any
    benchmark_task_coordinator: Any
    playback_task_coordinator: Any
    export_task_coordinator: Any
    scene_coordinator: Any
    status_coordinator: Any


@dataclass(frozen=True)
class WindowRuntime:
    runtime_services: RuntimeServiceBundle
    workflow_services: WorkflowServiceBundle
    task_orchestration: TaskOrchestrationBundle
    workflow_facades: WorkflowFacadeBundle | None = None

    @property
    def runtime_facade(self):
        return self.runtime_services.runtime_facade

    @property
    def metrics_service(self):
        return self.runtime_services.metrics_service

    @property
    def window_cfg(self) -> dict[str, object]:
        return self.runtime_services.window_cfg

    @property
    def robot_workflow(self):
        return self.workflow_services.robot_workflow

    @property
    def motion_workflow(self):
        return self.workflow_services.motion_workflow

    @property
    def export_workflow(self):
        return self.workflow_services.export_workflow

    def _compatibility_facades(self) -> WorkflowFacadeBundle:
        """Return lazily materialized compatibility facades.

        Returns:
            WorkflowFacadeBundle: Compatibility adapters derived from the canonical
                workflow services only when a legacy surface actually requests them.

        Boundary behavior:
            The canonical presentation surface is the workflow bundle itself. Compatibility
            facades remain available for migration, but they are instantiated lazily so the
            clean mainline no longer pays their construction cost by default.
        """
        if self.workflow_facades is None:
            object.__setattr__(self, 'workflow_facades', WorkflowFacadeBundle.from_workflows(self.workflow_services))
        assert self.workflow_facades is not None
        return self.workflow_facades

    @property
    def robot_facade(self):
        return self._compatibility_facades().robot_facade

    @property
    def solver_facade(self):
        return self._compatibility_facades().solver_facade

    @property
    def trajectory_facade(self):
        return self._compatibility_facades().trajectory_facade

    @property
    def playback_facade(self):
        return self._compatibility_facades().playback_facade

    @property
    def benchmark_facade(self):
        return self._compatibility_facades().benchmark_facade

    @property
    def export_facade(self):
        return self._compatibility_facades().export_facade

    @property
    def threader(self):
        return self.task_orchestration.threader

    @property
    def playback_threader(self):
        return self.task_orchestration.playback_threader

    @property
    def playback_render_scheduler(self):
        return self.task_orchestration.playback_render_scheduler

    @property
    def robot_coordinator(self):
        return self.task_orchestration.robot_coordinator

    @property
    def ik_task_coordinator(self):
        return self.task_orchestration.ik_task_coordinator

    @property
    def trajectory_task_coordinator(self):
        return self.task_orchestration.trajectory_task_coordinator

    @property
    def benchmark_task_coordinator(self):
        return self.task_orchestration.benchmark_task_coordinator

    @property
    def playback_task_coordinator(self):
        return self.task_orchestration.playback_task_coordinator

    @property
    def export_task_coordinator(self):
        return self.task_orchestration.export_task_coordinator

    @property
    def scene_coordinator(self):
        return self.task_orchestration.scene_coordinator

    @property
    def status_coordinator(self):
        return self.task_orchestration.status_coordinator
