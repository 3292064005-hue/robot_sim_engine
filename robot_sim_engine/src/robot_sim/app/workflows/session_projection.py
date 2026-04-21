from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from robot_sim.model.imported_robot_result import ImportedRobotResult
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.session_state import SessionState
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.benchmark_report import BenchmarkReport

from .import_resolution import ResolvedImportBundle

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.app.workflows.application_workflow import ApplicationWorkflowFacade


def build_session_state(
    owner: 'ApplicationWorkflowFacade',
    spec: RobotSpec,
    *,
    q_current,
    trajectory: JointTrajectory | None = None,
    benchmark_report: BenchmarkReport | None = None,
    robot_geometry: RobotGeometry | None = None,
    collision_geometry: RobotGeometry | None = None,
) -> SessionState:
    """Construct one canonical session snapshot from runtime/application inputs."""
    q_vector = np.asarray(q_current, dtype=float).copy()
    fk_result = owner.run_fk(spec, q_vector)
    assets = owner.runtime_asset_service.build_assets(
        spec,
        robot_geometry=robot_geometry,
        collision_geometry=collision_geometry,
    )
    state = SessionState(
        robot_spec=spec,
        q_current=q_vector,
        fk_result=fk_result,
        planning_scene=assets.planning_scene,
        scene_summary=dict(assets.scene_summary),
        robot_geometry=assets.robot_geometry,
        collision_geometry=assets.collision_geometry,
    )
    state.trajectory = trajectory
    state.benchmark_report = benchmark_report
    return state


def imported_robot_result_from_loaded(
    resolved: ResolvedImportBundle,
    *,
    fk_result,
    loaded_spec: RobotSpec,
) -> ImportedRobotResult:
    """Project one resolved import bundle into the presentation/headless result surface."""
    metadata = dict(getattr(loaded_spec, 'metadata', {}) or {})
    warnings = tuple(str(item) for item in metadata.get('warnings', ()) or ())
    return ImportedRobotResult(
        spec=loaded_spec,
        fk_result=fk_result,
        source_path=resolved.source_path,
        importer_id=str(metadata.get('importer_resolved', resolved.importer_id or '')),
        fidelity=str(metadata.get('import_fidelity', resolved.fidelity or 'unknown')),
        warnings=warnings,
        geometry_available=bool(metadata.get('geometry_available', resolved.geometry_available)),
        source_model_summary=dict(metadata.get('source_model_summary', resolved.source_model_summary) or {}),
        persisted_path=resolved.persisted_path,
        suggested_name=resolved.suggested_name,
        staged_only=resolved.staged_only,
    )
