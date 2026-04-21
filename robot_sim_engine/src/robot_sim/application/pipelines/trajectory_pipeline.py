from __future__ import annotations

from dataclasses import dataclass, field, replace
import time

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.pipelines.trajectory_pipeline_registry import (
    TrajectoryPipelineRegistry,
    build_default_trajectory_pipeline_registry,
)
from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.model.trajectory import JointTrajectory


@dataclass(frozen=True)
class TrajectoryPipelineResult:
    """Structured result emitted by the trajectory execution pipeline.

    Attributes:
        planner_id: Planner identifier selected for execution.
        raw: Raw trajectory before retiming.
        retimed: Final retimed trajectory returned to callers.
        diagnostics: Validation diagnostics associated with the final trajectory.
        cache_status: Cache state projected onto the final trajectory metadata.
        scene_revision: Planning-scene revision used during validation.
        validation_stage: Name of the validation stage that produced diagnostics.
        phase_timings_ms: Per-stage timing measurements used by diagnostics and profiling.
        pipeline_id: Named pipeline that executed the request.
    """

    planner_id: str
    raw: JointTrajectory
    retimed: JointTrajectory
    diagnostics: object
    cache_status: str = 'none'
    scene_revision: int = 0
    validation_stage: str = 'validate_trajectory'
    phase_timings_ms: dict[str, float] = field(default_factory=dict)
    pipeline_id: str = 'default'


class TrajectoryExecutionPipeline:
    """Pipeline that resolves a named pipeline, retimes the result, and validates it."""

    def __init__(
        self,
        planner_registry,
        validate_uc: ValidateTrajectoryUseCase,
        pipeline_registry: TrajectoryPipelineRegistry | None = None,
    ) -> None:
        self._planner_registry = planner_registry
        self._validate_uc = validate_uc
        self._pipeline_registry = pipeline_registry or build_default_trajectory_pipeline_registry()

    def resolve_pipeline_id(self, req: TrajectoryRequest) -> str:
        return str(req.pipeline_id or 'default')

    def resolve_planner_id(self, req: TrajectoryRequest) -> str:
        pipeline = self._pipeline_registry.get(self.resolve_pipeline_id(req))
        return pipeline.planner_stage.resolve_planner_id(req)

    def execute(self, req: TrajectoryRequest) -> TrajectoryPipelineResult:
        started = time.perf_counter()
        pipeline = self._pipeline_registry.get(self.resolve_pipeline_id(req))

        planner_started = time.perf_counter()
        planner_id, raw = pipeline.planner_stage.run(req, self._planner_registry)
        planner_elapsed_ms = (time.perf_counter() - planner_started) * 1000.0

        retime_started = time.perf_counter()
        retimed = pipeline.retime_stage.run(req, raw)
        retime_elapsed_ms = (time.perf_counter() - retime_started) * 1000.0

        validate_started = time.perf_counter()
        diagnostics = pipeline.validate_stage.run(req, retimed, self._validate_uc)
        validate_elapsed_ms = (time.perf_counter() - validate_started) * 1000.0

        postprocess_elapsed_ms = 0.0
        final_traj = retimed
        for postprocessor in pipeline.postprocessors:
            stage_started = time.perf_counter()
            final_traj = postprocessor.run(req, final_traj, diagnostics)
            postprocess_elapsed_ms += (time.perf_counter() - stage_started) * 1000.0

        phase_timings_ms = {
            'planner': float(planner_elapsed_ms),
            'retime': float(retime_elapsed_ms),
            'validate': float(validate_elapsed_ms),
            'postprocess': float(postprocess_elapsed_ms),
            'total': float((time.perf_counter() - started) * 1000.0),
        }
        collision_summary = dict(diagnostics.metadata.get('collision_summary', {}))
        timing_summary = dict(diagnostics.metadata.get('timing_summary', {}))
        collision_summary.setdefault('phase_timings_ms', dict(phase_timings_ms))
        timing_summary.setdefault('phase_timings_ms', dict(phase_timings_ms))
        diagnostics.metadata['collision_summary'] = collision_summary
        diagnostics.metadata['timing_summary'] = timing_summary

        metadata = dict(final_traj.metadata)
        metadata.setdefault('pipeline_id', pipeline.pipeline_id)
        metadata.setdefault('path_stage', str(pipeline.metadata.get('path_stage', pipeline.planner_stage.stage_id) or pipeline.planner_stage.stage_id))
        metadata.setdefault('retimer_id', str(pipeline.metadata.get('retimer_id', pipeline.retime_stage.stage_id) or pipeline.retime_stage.stage_id))
        metadata.setdefault(
            'validation_stage',
            str(pipeline.metadata.get('validation_stage', pipeline.validate_stage.stage_id) or pipeline.validate_stage.stage_id),
        )
        if req.execution_graph is not None:
            metadata.setdefault('execution_graph', req.execution_graph.summary())
        final_traj = replace(final_traj, metadata=metadata)
        cache_status = str(final_traj.metadata.get('cache_status', 'none') or 'none')
        scene_revision = int(diagnostics.metadata.get('scene_revision', 0) or 0)
        return TrajectoryPipelineResult(
            planner_id=planner_id,
            raw=raw,
            retimed=final_traj,
            diagnostics=diagnostics,
            cache_status=cache_status,
            scene_revision=scene_revision,
            validation_stage=str(metadata.get('validation_stage', pipeline.validate_stage.stage_id)),
            phase_timings_ms=phase_timings_ms,
            pipeline_id=str(pipeline.pipeline_id),
        )
