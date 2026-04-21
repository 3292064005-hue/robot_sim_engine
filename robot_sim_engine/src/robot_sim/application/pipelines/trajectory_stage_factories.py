from __future__ import annotations

from collections.abc import Mapping

from robot_sim.application.pipelines.trajectory_pipeline_registry import NoopPostprocessorStage, ValidateTrajectoryStage


def build_validate_stage(*, stage_id: str, metadata: Mapping[str, object] | None = None, **_: object) -> ValidateTrajectoryStage:
    """Build a configurable validation stage from stage-catalog metadata.

    Args:
        stage_id: Stable stage identifier declared by the external stage catalog.
        metadata: Optional metadata containing ``layer_override`` as an iterable of validation
            layer ids.

    Returns:
        ValidateTrajectoryStage: Runtime validation stage honoring any configured layer override.

    Raises:
        ValueError: Propagated when the built stage receives invalid layer override values.
    """
    payload = dict(metadata or {})
    layer_override = payload.get('layer_override')
    normalized_layers = None if layer_override in (None, (), []) else tuple(str(item) for item in layer_override)
    return ValidateTrajectoryStage(layer_override=normalized_layers, stage_id=str(stage_id))


def build_noop_postprocessor_stage(*, stage_id: str, **_: object) -> NoopPostprocessorStage:
    """Build a no-op postprocessor stage for externally declared pipeline chains."""
    stage = NoopPostprocessorStage()
    stage.stage_id = str(stage_id)
    return stage
