from __future__ import annotations

<<<<<<< HEAD
from dataclasses import replace
from pathlib import Path

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
import numpy as np

from robot_sim.application.dto import FKRequest
from robot_sim.application.services.robot_registry import RobotRegistry
<<<<<<< HEAD
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.domain.enums import AppExecutionState
from robot_sim.model.imported_robot_result import ImportedRobotResult
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.robot_spec import RobotSpec
=======
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.domain.enums import AppExecutionState
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.validators.input_validator import InputValidator


class RobotController:
<<<<<<< HEAD
    def __init__(
        self,
        state_store: StateStore,
        registry: RobotRegistry,
        fk_uc: RunFKUseCase,
        import_robot_uc=None,
        *,
        runtime_asset_service: RobotRuntimeAssetService | None = None,
    ) -> None:
        self._state_store = state_store
        self._registry = registry
        self._fk_uc = fk_uc
        self._import_robot_uc = import_robot_uc
        self._runtime_asset_service = runtime_asset_service or RobotRuntimeAssetService()

    def _load_spec_into_runtime(
        self,
        spec: RobotSpec,
        *,
        robot_geometry=None,
        collision_geometry=None,
    ):
        """Load one robot specification into the presentation runtime.

        Args:
            spec: Canonical robot specification to project into runtime state.
            robot_geometry: Optional importer/runtime visual geometry bundle.
            collision_geometry: Optional importer/runtime collision geometry bundle.

        Returns:
            FKResult: FK projection at the robot home configuration.

        Raises:
            ValueError: Propagates FK request validation errors.

        Boundary behavior:
            Runtime geometry and planning-scene state are derived from one canonical asset
            service so validation/export/render share the same scene authority.
        """
        fk = self._fk_uc.execute(FKRequest(spec, spec.home_q.copy()))
        runtime_assets = self._runtime_asset_service.build_assets(
            spec,
            robot_geometry=robot_geometry,
            collision_geometry=collision_geometry,
        )
        scene_revision = max(
            int(self._state_store.state.scene_revision) + 1,
            int(getattr(runtime_assets.planning_scene, 'revision', 0)),
        )
=======
    def __init__(self, state_store: StateStore, registry: RobotRegistry, fk_uc: RunFKUseCase) -> None:
        self._state_store = state_store
        self._registry = registry
        self._fk_uc = fk_uc

    def load_robot(self, name: str):
        spec = self._registry.load(name)
        fk = self._fk_uc.execute(FKRequest(spec, spec.home_q.copy()))
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        self._state_store.patch(
            robot_spec=spec,
            q_current=spec.home_q.copy(),
            fk_result=fk,
            target_pose=None,
            ik_result=None,
            trajectory=None,
            benchmark_report=None,
            playback=PlaybackState(),
            last_error='',
            last_warning='',
            app_state=AppExecutionState.ROBOT_READY,
<<<<<<< HEAD
            scene_revision=scene_revision,
            robot_geometry=runtime_assets.robot_geometry,
            collision_geometry=runtime_assets.collision_geometry,
        )
        self._state_store.patch_scene(
            runtime_assets.scene_summary,
            planning_scene=runtime_assets.planning_scene,
            scene_revision=scene_revision,
        )
        return fk

    def load_robot(self, name: str):
        spec = self._registry.load(name)
        return self._load_spec_into_runtime(spec)

    def _editor_mutates_runtime_model(self, existing_spec: RobotSpec, rows) -> bool:
        if tuple(rows) == tuple(existing_spec.dh_rows):
            return False
        return bool(existing_spec.has_structured_model or existing_spec.has_canonical_model or existing_spec.kinematic_source in {'urdf_model', 'urdf_skeleton'})

    def _fork_runtime_metadata(self, existing_spec: RobotSpec, *, execution_row_count: int) -> tuple[dict[str, object], dict[str, object]]:
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
        """Build a persisted robot specification from editor rows/home state.

        Args:
            existing_spec: Currently loaded robot specification.
            rows: Edited DH rows from the UI table.
            home_q: Edited home-joint vector.

        Returns:
            RobotSpec: New immutable robot specification.

        Raises:
            RuntimeError: If no robot is currently loaded.
            ValueError: If the editor payload fails validation.

        Boundary behavior:
            Editing DH rows on top of an imported structured model forks runtime semantics:
            structured/source-model metadata is cleared so persistence/export paths do not
            falsely claim URDF/source fidelity after manual DH edits.
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
        """Return the canonical runtime/spec identity after a save or save-as operation.

        Args:
            path: Persisted registry path returned by ``RobotRegistry.save``.
            requested_name: Optional user-requested save target name.
            existing_spec: Spec being persisted.

        Returns:
            tuple[str, Optional[str]]: New canonical ``spec.name`` and optional display label.

        Boundary behavior:
            When no explicit name is requested, the existing runtime identity is preserved.
            Save-as operations adopt the written file stem immediately so runtime state and
            on-disk identity never diverge.
        """
        persisted_name = str(path.stem)
        requested = str(requested_name or '').strip()
        if not requested:
            return existing_spec.name, existing_spec.display_name
        display_name = requested
        if existing_spec.display_name not in (None, '', existing_spec.name, requested):
            display_name = existing_spec.display_name
        return persisted_name, display_name

=======
            scene_revision=self._state_store.state.scene_revision + 1,
        )
        return fk

    def build_robot_from_editor(self, existing_spec: RobotSpec | None, rows, home_q) -> RobotSpec:
        if existing_spec is None:
            raise RuntimeError('robot not loaded')
        home_q = np.asarray(home_q, dtype=float)
        home_q = InputValidator.validate_home_q(rows, home_q)
        return RobotSpec(
            name=existing_spec.name,
            dh_rows=tuple(rows),
            base_T=existing_spec.base_T,
            tool_T=existing_spec.tool_T,
            home_q=home_q,
            display_name=existing_spec.display_name,
            description=existing_spec.description,
            metadata=dict(existing_spec.metadata),
        )

>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        spec = self._state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        if rows is not None or home_q is not None:
            rows_in = rows if rows is not None else spec.dh_rows
            home_q_in = home_q if home_q is not None else spec.home_q
            spec = self.build_robot_from_editor(rows=rows_in, home_q=home_q_in, existing_spec=spec)
<<<<<<< HEAD
            path = self._registry.save(spec, name=name)
            persisted_name, display_name = self._normalized_persisted_name(path, name, spec)
            spec = replace(spec, name=persisted_name, display_name=display_name)
            self._load_spec_into_runtime(spec)
            return path
        path = self._registry.save(spec, name=name)
        persisted_name, display_name = self._normalized_persisted_name(path, name, spec)
        if persisted_name != spec.name or display_name != spec.display_name:
            self._load_spec_into_runtime(replace(spec, name=persisted_name, display_name=display_name))
        return path

    def import_robot(self, source: str, importer_id: str | None = None) -> ImportedRobotResult:
        """Import an external robot config, persist it safely, and load it into runtime state.

        Args:
            source: User-selected robot source path (YAML / URDF / plugin importer input).
            importer_id: Optional importer override selected from the UI.

        Returns:
            ImportedRobotResult: Structured import result containing the persisted path, the
                loaded FK projection, and bounded warning metadata.

        Raises:
            RuntimeError: If the controller was not configured with an import use case.
            FileNotFoundError: If the selected source path does not exist.
            Exception: Propagates importer parsing/validation errors.

        Boundary behavior:
            Imports are persisted into the canonical robot registry without overwriting an
            unrelated existing config silently. If the preferred slug is already occupied,
            the registry allocates a deterministic suffixed name before the imported robot is
            loaded into the live presentation state together with its canonical runtime
            geometry and planning-scene authority.
        """
        if self._import_robot_uc is None:
            raise RuntimeError('robot import use case is not configured')
        source_path = Path(source).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f'import source not found: {source_path}')
        bundle = self._import_robot_uc.execute_bundle(source_path, importer_id=importer_id)
        requested_id = importer_id or source_path.suffix.lower().lstrip('.')
        if requested_id == 'yml':
            requested_id = 'yaml'
        imported_spec = self._import_robot_uc.normalize_bundle_spec(bundle, requested_id=requested_id)
        preferred_name = str(getattr(imported_spec, 'name', '') or source_path.stem)
        exclude_path = source_path if source_path.parent.resolve() == self._registry.robots_dir.resolve() else None
        persisted_name = self._registry.next_available_name(preferred_name, exclude_path=exclude_path)
        persisted_spec = replace(imported_spec, name=persisted_name)
        persisted_path = self._registry.save(persisted_spec, name=persisted_name)
        fk = self._load_spec_into_runtime(
            persisted_spec,
            robot_geometry=bundle.geometry,
            collision_geometry=bundle.collision_geometry,
        )
        loaded_spec = self._state_store.state.robot_spec
        metadata = dict(getattr(loaded_spec, 'metadata', {}) or {})
        warnings = tuple(str(item) for item in metadata.get('warnings', ()) or ())
        importer_resolved = str(metadata.get('importer_resolved', importer_id or ''))
        fidelity = str(metadata.get('import_fidelity', 'unknown'))
        if warnings:
            self._state_store.patch(last_warning=' | '.join(warnings))
        return ImportedRobotResult(
            spec=loaded_spec,
            fk_result=fk,
            persisted_path=persisted_path,
            source_path=source_path,
            importer_id=importer_resolved,
            fidelity=fidelity,
            warnings=warnings,
            geometry_available=bool(metadata.get('geometry_available', False)),
            source_model_summary=dict(metadata.get('source_model_summary', {}) or {}),
        )
=======
            self._state_store.patch(robot_spec=spec)
        return self._registry.save(spec, name=name)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    def run_fk(self, q=None):
        spec = self._state_store.state.robot_spec
        q_current = self._state_store.state.q_current if q is None else np.asarray(q, dtype=float)
        if spec is None or q_current is None:
            raise RuntimeError('robot not loaded')
        q_current = InputValidator.validate_joint_vector(spec, q_current, clamp=False)
        self._state_store.patch(q_current=q_current.copy())
        fk = self._fk_uc.execute(FKRequest(spec, q_current))
        self._state_store.patch(fk_result=fk, scene_revision=self._state_store.state.scene_revision + 1)
        return fk

    def sample_ee_positions(self, q_samples) -> np.ndarray:
        spec = self._state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        pts = []
        for q in np.asarray(q_samples, dtype=float):
            fk = self._fk_uc.execute(FKRequest(spec, np.asarray(q, dtype=float)))
            pts.append(np.asarray(fk.ee_pose.p, dtype=float))
        return np.asarray(pts, dtype=float)
