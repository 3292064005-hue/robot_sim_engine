from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeServiceBundle:
    """Canonical runtime-service bundle exposed to the main window shell.

    This bundle groups the runtime façade, metrics service, and immutable window
    configuration so the window shell no longer owns dozens of peer attributes.
    Compatibility properties on :class:`WindowRuntime` preserve the legacy surface
    for existing mixins, tests, and limited out-of-repo automation.
    """

    runtime_facade: Any
    metrics_service: Any
    window_cfg: dict[str, object]


@dataclass(frozen=True)
class WorkflowFacadeBundle:
    """Canonical workflow façade bundle for robot / motion / export actions."""

    robot_facade: Any
    solver_facade: Any
    trajectory_facade: Any
    playback_facade: Any
    benchmark_facade: Any
    export_facade: Any


@dataclass(frozen=True)
class TaskOrchestrationBundle:
    """Canonical orchestration bundle for threads, schedulers, and coordinators."""

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
    """Grouped main-window runtime dependencies.

    The canonical ownership model is now three stable dependency bundles:
    runtime services, workflow façades, and task orchestration. Read-only
    compatibility properties preserve the historical attribute surface while the
    rest of the presentation layer migrates toward grouped bundle access.
    """

    runtime_services: RuntimeServiceBundle
    workflow_facades: WorkflowFacadeBundle
    task_orchestration: TaskOrchestrationBundle

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
    def robot_facade(self):
        return self.workflow_facades.robot_facade

    @property
    def solver_facade(self):
        return self.workflow_facades.solver_facade

    @property
    def trajectory_facade(self):
        return self.workflow_facades.trajectory_facade

    @property
    def playback_facade(self):
        return self.workflow_facades.playback_facade

    @property
    def benchmark_facade(self):
        return self.workflow_facades.benchmark_facade

    @property
    def export_facade(self):
        return self.workflow_facades.export_facade

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
