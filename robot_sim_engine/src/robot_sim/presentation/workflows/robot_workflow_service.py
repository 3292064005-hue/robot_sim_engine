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
from robot_sim.model.robot_spec import RobotSpec
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
    from robot_sim.model.trajectory import JointTrajectory
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

    @staticmethod
    def _editor_mutates_runtime_model(existing_spec: RobotSpec, rows) -> bool:
        """Return whether a manual DH edit invalidates structured/imported runtime semantics.

        Args:
            existing_spec: Currently loaded robot specification.
            rows: Candidate DH rows from the editor.

        Returns:
            bool: ``True`` when the edit forks from a structured/source model into edited DH
            runtime semantics.

        Raises:
            None: Pure metadata/row comparison.

        Boundary behavior:
            Unchanged rows never fork the runtime model. Plain DH robots can still be edited
            without clearing structured-source metadata because they do not claim such fidelity.
        """
        if tuple(rows) == tuple(existing_spec.dh_rows):
            return False
        return bool(
            existing_spec.has_structured_model
            or existing_spec.has_canonical_model
            or existing_spec.kinematic_source in {'urdf_model', 'urdf_skeleton'}
        )

    @staticmethod
    def _fork_runtime_metadata(existing_spec: RobotSpec, *, execution_row_count: int) -> tuple[dict[str, object], dict[str, object]]:
        """Build metadata for a robot whose imported/source model was manually DH-edited.

        Args:
            existing_spec: Source robot specification being edited.
            execution_row_count: Number of DH execution rows in the edited runtime model.

        Returns:
            tuple[dict[str, object], dict[str, object]]: Updated spec metadata and source-model
            summary for the forked runtime model.

        Raises:
            None: Metadata is defensively copied and normalized.

        Boundary behavior:
            Source-model fidelity is explicitly invalidated so exports and runtime projections do
            not claim URDF/source geometry after manual DH edits.
        """
        metadata = dict(existing_spec.metadata or {})
        warnings = [str(item) for item in metadata.get('warnings', ()) or ()]
        fork_warning = (
            'Robot editor modified DH rows derived from an imported structured/source model; '
            'runtime now follows the edited DH configuration and no longer claims source-model fidelity.'
        )
        if fork_warning not in warnings:
            warnings.append(fork_warning)
        original_source = str(existing_spec.model_source or existing_spec.kinematic_source or 'unknown')
        metadata.update({
            'model_source': 'edited_runtime_dh',
            'import_fidelity': 'edited_runtime_dh',
            'import_semantics': 'edited_runtime_dh',
            'geometry_available': False,
            'collision_model': 'generated_proxy',
            'geometry_ref': '',
            'collision_geometry_ref': '',
            'serialized_robot_geometry': None,
            'serialized_collision_geometry': None,
            'warnings': warnings,
            'notes': (
                'Structured/imported source semantics were invalidated after DH edits. '
                'Runtime execution and scene projection now follow the edited DH configuration.'
            ),
            'source_model_retained': False,
            'source_model_invalidated': True,
            'forked_from_model_source': original_source,
            'canonical_model_summary': None,
            'execution_adapter': 'robot_spec_execution_rows',
            'execution_surface': 'robot_spec',
            'execution_row_count': int(execution_row_count),
            'execution_summary': {
                'execution_adapter': 'robot_spec_execution_rows',
                'execution_surface': 'robot_spec',
                'execution_row_count': int(execution_row_count),
            },
        })
        source_model_summary = {
            'forked_runtime_model': True,
            'forked_from_model_source': original_source,
            'joint_count': int(len(existing_spec.dh_rows)),
            'link_count': int(max(len(existing_spec.runtime_link_names), len(existing_spec.dh_rows) + 1)),
            'has_visual': False,
            'has_collision': False,
        }
        return metadata, source_model_summary

    def build_robot_from_editor(self, existing_spec: RobotSpec | None, rows, home_q) -> RobotSpec:
        """Build a robot specification from editor rows without using legacy controllers.

        Args:
            existing_spec: Currently loaded robot specification.
            rows: Edited DH rows from the UI table.
            home_q: Edited home joint vector.

        Returns:
            RobotSpec: New immutable robot specification.

        Raises:
            RuntimeError: If no robot is currently loaded.
            ValueError: If the editor payload is malformed.

        Boundary behavior:
            Structured/imported robot specs are explicitly forked into edited DH runtime semantics
            when DH rows change, preventing exported sessions from falsely claiming source-model
            fidelity after manual edits.
        """
        if existing_spec is None:
            raise RuntimeError('robot not loaded')
        home_q_array = np.asarray(home_q, dtype=float)
        home_q_array = InputValidator.validate_home_q(rows, home_q_array)
        rows_tuple = tuple(rows)
        metadata = dict(existing_spec.metadata)
        joint_names = existing_spec.joint_names
        link_names = existing_spec.link_names
        joint_types = existing_spec.joint_types
        joint_axes = existing_spec.joint_axes
        joint_limits = existing_spec.joint_limits
        structured_joints = existing_spec.structured_joints
        structured_links = existing_spec.structured_links
        kinematic_source = existing_spec.kinematic_source
        geometry_bundle_ref = existing_spec.geometry_bundle_ref
        collision_bundle_ref = existing_spec.collision_bundle_ref
        source_model_summary = dict(existing_spec.source_model_summary)
        canonical_model = existing_spec.canonical_model

        if self._editor_mutates_runtime_model(existing_spec, rows_tuple):
            metadata, source_model_summary = self._fork_runtime_metadata(existing_spec, execution_row_count=len(rows_tuple))
            structured_joints = ()
            structured_links = ()
            kinematic_source = 'dh_config'
            geometry_bundle_ref = ''
            collision_bundle_ref = ''
            canonical_model = None

        return RobotSpec(
            name=existing_spec.name,
            dh_rows=rows_tuple,
            base_T=existing_spec.base_T,
            tool_T=existing_spec.tool_T,
            home_q=home_q_array,
            display_name=existing_spec.display_name,
            description=existing_spec.description,
            metadata=metadata,
            joint_names=joint_names,
            link_names=link_names,
            joint_types=joint_types,
            joint_axes=joint_axes,
            joint_limits=joint_limits,
            structured_joints=structured_joints,
            structured_links=structured_links,
            kinematic_source=kinematic_source,
            geometry_bundle_ref=geometry_bundle_ref,
            collision_bundle_ref=collision_bundle_ref,
            source_model_summary=source_model_summary,
            canonical_model=canonical_model,
        )

    @staticmethod
    def _normalized_persisted_name(path: Path, requested_name: str | None, existing_spec: RobotSpec) -> tuple[str, str | None]:
        """Resolve canonical runtime/spec identity after save or save-as.

        Args:
            path: Registry path returned by ``RobotRegistry.save``.
            requested_name: Optional user-requested save target name.
            existing_spec: Spec being persisted.

        Returns:
            tuple[str, str | None]: Canonical ``spec.name`` and optional display label.

        Raises:
            None: Pure string normalization.

        Boundary behavior:
            Save-as operations adopt the written file stem immediately; ordinary saves preserve the
            current runtime identity.
        """
        persisted_name = str(path.stem)
        requested = str(requested_name or '').strip()
        if not requested:
            return existing_spec.name, existing_spec.display_name
        display_name = requested
        if existing_spec.display_name not in (None, '', existing_spec.name, requested):
            display_name = existing_spec.display_name
        return persisted_name, display_name

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        """Persist the current robot through the canonical workflow service.

        Args:
            rows: Optional edited DH rows to apply before saving.
            home_q: Optional edited home joint vector to apply before saving.
            name: Optional save-as target name.

        Returns:
            pathlib.Path: Registry path written by ``RobotRegistry.save``.

        Raises:
            RuntimeError: If no robot is currently loaded.
            ValueError: If editor payload validation fails.

        Boundary behavior:
            Persistence updates runtime projection only when the saved spec identity or edited
            runtime model changes, preserving active scene/export semantics through the canonical
            runtime projection service rather than a legacy controller.
        """
        spec = self.state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        if rows is not None or home_q is not None:
            rows_in = rows if rows is not None else spec.dh_rows
            home_q_in = home_q if home_q is not None else spec.home_q
            spec = self.build_robot_from_editor(rows=rows_in, home_q=home_q_in, existing_spec=spec)
            path = self.registry.save(spec, name=name)
            persisted_name, display_name = self._normalized_persisted_name(path, name, spec)
            spec = replace(spec, name=persisted_name, display_name=display_name)
            self.runtime_projection_service.load_robot_spec(spec)
            return path
        path = self.registry.save(spec, name=name)
        persisted_name, display_name = self._normalized_persisted_name(path, name, spec)
        if persisted_name != spec.name or display_name != spec.display_name:
            self.runtime_projection_service.load_robot_spec(replace(spec, name=persisted_name, display_name=display_name))
        return path

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
