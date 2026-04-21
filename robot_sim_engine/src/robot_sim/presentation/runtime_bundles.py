from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from robot_sim.presentation.view_contracts import ExportWorkflowContract, MotionWorkflowContract, RobotWorkflowContract, RuntimeViewContract

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.application.services.metrics_service import MetricsService
    from robot_sim.presentation.coordinators.benchmark_task_coordinator import BenchmarkTaskCoordinator
    from robot_sim.presentation.coordinators.export_task_coordinator import ExportTaskCoordinator
    from robot_sim.presentation.coordinators.ik_task_coordinator import IKTaskCoordinator
    from robot_sim.presentation.coordinators.playback_task_coordinator import PlaybackTaskCoordinator
    from robot_sim.presentation.coordinators.robot_coordinator import RobotCoordinator
    from robot_sim.presentation.coordinators.scene_coordinator import SceneCoordinator
    from robot_sim.presentation.coordinators.status_coordinator import StatusCoordinator
    from robot_sim.presentation.coordinators.trajectory_task_coordinator import TrajectoryTaskCoordinator


@dataclass(frozen=True)
class RuntimeServiceBundle:
    runtime_facade: RuntimeViewContract
    metrics_service: 'MetricsService'
    window_cfg: dict[str, object]


@dataclass(frozen=True)
class WorkflowServiceBundle:
    robot_workflow: RobotWorkflowContract
    motion_workflow: MotionWorkflowContract
    export_workflow: ExportWorkflowContract


@dataclass(frozen=True)
class TaskOrchestrationBundle:
    threader: object
    playback_threader: object
    playback_render_scheduler: object
    robot_coordinator: 'RobotCoordinator'
    ik_task_coordinator: 'IKTaskCoordinator'
    trajectory_task_coordinator: 'TrajectoryTaskCoordinator'
    benchmark_task_coordinator: 'BenchmarkTaskCoordinator'
    playback_task_coordinator: 'PlaybackTaskCoordinator'
    export_task_coordinator: 'ExportTaskCoordinator'
    scene_coordinator: 'SceneCoordinator'
    status_coordinator: 'StatusCoordinator'


@dataclass(frozen=True)
class WindowRuntime:
    runtime_services: RuntimeServiceBundle
    workflow_services: WorkflowServiceBundle
    task_orchestration: TaskOrchestrationBundle
