from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robot_sim.app.container import AppContainer
from robot_sim.presentation.coordinators import (
    BenchmarkTaskCoordinator,
    ExportTaskCoordinator,
    IKTaskCoordinator,
    PlaybackTaskCoordinator,
    RobotCoordinator,
    SceneCoordinator,
    StatusCoordinator,
    TrajectoryTaskCoordinator,
)
from robot_sim.presentation.main_controller import MainController
from robot_sim.presentation.playback_render_scheduler import PlaybackRenderScheduler
from robot_sim.presentation.runtime_bundles import (
    RuntimeServiceBundle,
    TaskOrchestrationBundle,
    WindowRuntime,
    WorkflowFacadeBundle,
)
from robot_sim.presentation.thread_orchestrator import ThreadOrchestrator


@dataclass(frozen=True)
class PresentationAssembly:
    """Composition bundle used by the Qt shell.

    This bundle centralizes presentation-layer object-graph construction so the main window
    consumes a stable assembly instead of constructing controllers, orchestrators, façades,
    and coordinators inline.
    """

    controller: MainController
    window_runtime: WindowRuntime


def build_presentation_assembly(project_root: str | Path, *, container: AppContainer, window_parent=None) -> PresentationAssembly:
    """Build the presentation object graph consumed by ``MainWindow``.

    Args:
        project_root: Runtime project root forwarded to the presentation controller.
        container: Explicitly constructed application container.
        window_parent: Optional Qt parent object used by thread/scheduler helpers.

    Returns:
        PresentationAssembly: Fully wired presentation composition bundle.

    Raises:
        ValueError: If ``container`` is not provided.
    """
    if container is None:
        raise ValueError('build_presentation_assembly requires an explicit application container')
    controller = MainController(project_root, container=container)
    runtime_facade = controller.runtime_facade
    workflow_facades = WorkflowFacadeBundle(
        robot_facade=controller.robot_facade,
        solver_facade=controller.solver_facade,
        trajectory_facade=controller.trajectory_facade,
        playback_facade=controller.playback_facade,
        benchmark_facade=controller.benchmark_facade,
        export_facade=controller.export_facade,
    )
    runtime_services = RuntimeServiceBundle(
        runtime_facade=runtime_facade,
        metrics_service=runtime_facade.metrics_service,
        window_cfg=dict(runtime_facade.app_config.get('window', {})),
    )
    threader = ThreadOrchestrator(window_parent)
    playback_threader = ThreadOrchestrator(window_parent, start_policy='queue_latest')
    playback_render_scheduler = PlaybackRenderScheduler(window_parent)
    task_orchestration = TaskOrchestrationBundle(
        threader=threader,
        playback_threader=playback_threader,
        playback_render_scheduler=playback_render_scheduler,
        robot_coordinator=RobotCoordinator(window_parent, robot=workflow_facades.robot_facade),
        ik_task_coordinator=IKTaskCoordinator(window_parent, solver=workflow_facades.solver_facade, threader=threader),
        trajectory_task_coordinator=TrajectoryTaskCoordinator(window_parent, trajectory=workflow_facades.trajectory_facade, threader=threader),
        benchmark_task_coordinator=BenchmarkTaskCoordinator(
            window_parent,
            runtime=runtime_facade,
            benchmark=workflow_facades.benchmark_facade,
            threader=threader,
        ),
        playback_task_coordinator=PlaybackTaskCoordinator(
            window_parent,
            runtime=runtime_facade,
            playback=workflow_facades.playback_facade,
            playback_threader=playback_threader,
        ),
        export_task_coordinator=ExportTaskCoordinator(
            window_parent,
            runtime=runtime_facade,
            export=workflow_facades.export_facade,
            threader=threader,
            metrics_service=runtime_facade.metrics_service,
        ),
        scene_coordinator=SceneCoordinator(
            window_parent,
            runtime=runtime_facade,
            threader=threader,
        ),
        status_coordinator=StatusCoordinator(window_parent, runtime=runtime_facade),
    )
    return PresentationAssembly(
        controller=controller,
        window_runtime=WindowRuntime(
            runtime_services=runtime_services,
            workflow_facades=workflow_facades,
            task_orchestration=task_orchestration,
        ),
    )
