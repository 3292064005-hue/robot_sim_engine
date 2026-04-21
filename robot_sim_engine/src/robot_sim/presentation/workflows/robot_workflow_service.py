from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.application.dto import FKRequest, IKRequest
from robot_sim.application.request_builders import (
    build_execution_graph_descriptor,
    build_ik_config,
    build_ik_request as build_ik_request_contract,
    build_pose_from_values6,
    build_trajectory_request as build_trajectory_request_contract,
    normalize_validation_layers,
)
from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS
from robot_sim.application.services.playback_service import PlaybackFrame, PlaybackService
from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.domain.enums import AppExecutionState, IKSolverMode, TrajectoryMode
from robot_sim.model.imported_robot_result import ImportedRobotResult
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.pose import Pose
from robot_sim.model.runtime_snapshots import EnvironmentSnapshot
from robot_sim.model.solver_config import IKConfig, SolverSettings
from robot_sim.presentation.runtime_projection_service import RuntimeProjectionService
from robot_sim.presentation.trajectory_request_support import build_motion_trajectory_request
from robot_sim.presentation.state_events import (
    BenchmarkReportProjectedEvent,
    FKProjectedEvent,
    IKResultAppliedEvent,
    PlaybackStateChangedEvent,
    TrajectoryAppliedEvent,
    WarningProjectedEvent,
)
from robot_sim.presentation.validators.input_validator import InputValidator
from robot_sim.presentation.view_contracts import ExportWorkflowContract, MotionWorkflowContract, RobotWorkflowContract

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.application.registries.importer_registry import ImporterRegistry
    from robot_sim.application.services.export_service import ExportService
    from robot_sim.application.services.robot_registry import RobotRegistry
    from robot_sim.application.use_cases.export_package import ExportPackageUseCase
    from robot_sim.application.use_cases.export_report import ExportReportUseCase
    from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
    from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
    from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
    from robot_sim.application.use_cases.run_fk import RunFKUseCase
    from robot_sim.application.use_cases.run_ik import RunIKUseCase
    from robot_sim.application.use_cases.save_session import SaveSessionUseCase
    from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
    from robot_sim.app.workflow_facade import ApplicationWorkflowFacade
    from robot_sim.model.benchmark_report import BenchmarkReport
    from robot_sim.model.robot_spec import RobotSpec
    from robot_sim.model.trajectory import JointTrajectory
    from robot_sim.presentation.controllers.robot_controller import RobotController
    from robot_sim.presentation.facades import RuntimeFacade
    from robot_sim.presentation.state_store import StateStore


@dataclass(frozen=True)
class RobotWorkflowService(RobotWorkflowContract):
    """Canonical robot capability port for presentation and task coordinators.

    New presentation code depends on this workflow rather than calling the robot controller
    directly. Robot load/import/FK now resolve against registry/use-case/runtime-projection
    truth instead of acting as a pass-through façade.
    """

    registry: 'RobotRegistry'
    fk_uc: 'RunFKUseCase'
    state_store: 'StateStore'
    runtime_projection_service: RuntimeProjectionService
    importer_registry: 'ImporterRegistry | None' = None
    import_robot_uc: 'ImportRobotUseCase | None' = None
    editor_controller: 'RobotController | None' = None
    application_workflow: 'ApplicationWorkflowFacade | None' = None

    def _application_workflow_or_raise(self):
        if self.application_workflow is None:
            raise RuntimeError('application workflow facade is not configured')
        return self.application_workflow

    def robot_names(self) -> list[str]:
        return self.registry.list_names()

    def robot_entries(self):
        return self.registry.list_entries()

    def available_specs(self):
        return self.registry.list_specs()

    def importer_entries(self):
        if self.importer_registry is None:
            return []
        return list(self.importer_registry.descriptors())

    def import_robot(self, source: str, importer_id: str | None = None, *, persist: bool = False):
        """Import a robot through the canonical application workflow.

        Args:
            source: Import source path.
            importer_id: Optional importer override.
            persist: When ``True`` the imported robot is written into the registry before the
                runtime projection is refreshed.

        Returns:
            ImportedRobotResult: Canonical import result projected into presentation state.
        """
        workflow = self._application_workflow_or_raise()
        resolved = workflow.resolve_import(source, importer_id=importer_id, persist=bool(persist))
        fk_result = self.runtime_projection_service.load_robot_spec(
            resolved.spec,
            robot_geometry=resolved.robot_geometry,
            collision_geometry=resolved.collision_geometry,
        ).fk_result
        loaded_spec = self.state_store.state.robot_spec
        metadata = dict(getattr(loaded_spec, 'metadata', {}) or {})
        warnings = tuple(str(item) for item in metadata.get('warnings', ()) or ())
        if warnings:
            self.state_store.dispatch(WarningProjectedEvent(message=' | '.join(warnings), code='import_warnings'))
        return workflow.imported_robot_result_from_loaded(
            resolved,
            fk_result=fk_result,
            loaded_spec=loaded_spec,
        )

    def load_robot(self, name: str):
        spec = self._application_workflow_or_raise().load_robot_spec(name)
        return self.runtime_projection_service.load_robot_spec(spec).fk_result

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        if self.editor_controller is None:
            raise RuntimeError('robot editor workflow is not configured')
        return self.editor_controller.build_robot_from_editor(existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        if self.editor_controller is None:
            raise RuntimeError('robot editor workflow is not configured')
        return self.editor_controller.save_current_robot(rows=rows, home_q=home_q, name=name)

    def run_fk(self, q=None):
        spec = self.state_store.state.robot_spec
        q_current = self.state_store.state.q_current if q is None else np.asarray(q, dtype=float)
        if spec is None or q_current is None:
            raise RuntimeError('robot not loaded')
        q_current = InputValidator.validate_joint_vector(spec, q_current, clamp=False)
        workflow = self._application_workflow_or_raise()
        fk = workflow.run_fk(spec, q_current)
        self.state_store.dispatch(
            FKProjectedEvent(
                q_current=q_current.copy(),
                fk_result=fk,
                scene_revision=self.state_store.state.scene_revision + 1,
            )
        )
        return fk

    def sample_ee_positions(self, q_samples):
        spec = self.state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        points = []
        for q in np.asarray(q_samples, dtype=float):
            fk = self._application_workflow_or_raise().run_fk(spec, np.asarray(q, dtype=float))
            points.append(np.asarray(fk.ee_pose.p, dtype=float))
        return np.asarray(points, dtype=float)
