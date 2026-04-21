from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

import numpy as np

from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.model.scene_geometry_authority import SceneGeometryAuthority
from robot_sim.model.scene_graph_authority import SceneGraphAuthority
from robot_sim.model.scene_command import SceneCommand, SceneMutationResult
from robot_sim.application.services.scene_backend_runtime import default_scene_backend_runtime
from robot_sim.model.scene_geometry_projection import project_declaration_geometry
from robot_sim.application.services.scene_authority_support import (
    SUPPORTED_SCENE_SHAPES,
    coerce_int,
    normalize_collision_pairs,
    normalize_shape_size,
    normalize_vector,
)

_COLLISION_BACKEND_REGISTRY = default_collision_backend_registry()


def _declaration_geometry_payload(*, shape: str, center: np.ndarray, size: np.ndarray) -> dict[str, object]:
    payload: dict[str, object] = {
        'kind': str(shape),
        'center': [float(value) for value in center.tolist()],
        'size': [float(value) for value in size.tolist()],
    }
    if str(shape) == 'sphere':
        payload['radius'] = float(size[0] * 0.5)
    elif str(shape) == 'cylinder':
        payload['radius'] = float(size[0] * 0.5)
        payload['height'] = float(size[2])
    return payload


def _validation_geometry_payload(geometry: AABB) -> dict[str, object]:
    return {
        'kind': 'aabb',
        'minimum': [float(value) for value in geometry.minimum.tolist()],
        'maximum': [float(value) for value in geometry.maximum.tolist()],
    }


def _render_geometry_payload(*, shape: str, center: np.ndarray, size: np.ndarray) -> dict[str, object]:
    return _declaration_geometry_payload(shape=shape, center=center, size=size)


@dataclass(frozen=True)
class SceneObstacleEdit:
    """Canonical stable scene-editor request for one obstacle or attached object.

    Attributes:
        object_id: Stable object identifier requested by the user.
        center: Object center in world coordinates.
        size: Canonical box-equivalent size in world coordinates.
        shape: Declared primitive shape. Stable runtime validation still consumes the derived AABB,
            while render/export/diagnostics preserve the original primitive metadata.
        replace_existing: Whether an existing object with the same id should be replaced instead of
            being deterministically suffixed.
        attached: Whether the object should be stored under ``PlanningScene.attached_objects``.
        attach_link: Optional link/tool identifier recorded for attached objects.
        allowed_collision_pairs: Optional collision-filter pairs to store in the ACM.
        clear_allowed_collision_pairs: Whether the current ACM should be cleared before any new pairs.
        metadata: Additional object-scoped metadata projected into the scene object.
    """

    object_id: str
    center: tuple[float, float, float]
    size: tuple[float, float, float]
    shape: str = 'box'
    replace_existing: bool = False
    attached: bool = False
    attach_link: str = ''
    allowed_collision_pairs: tuple[tuple[str, str], ...] = ()
    clear_allowed_collision_pairs: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> 'SceneObstacleEdit':
        """Build a typed edit request from a UI/service payload.

        Args:
            payload: User-provided mapping containing obstacle, attachment, and ACM fields.

        Returns:
            SceneObstacleEdit: Typed request with normalized tuples.

        Raises:
            ValueError: If numeric vectors, primitive fields, or pair payloads are malformed.
        """
        center = normalize_vector(payload.get('center'), field_name='center')
        shape = str(payload.get('shape', 'box') or 'box').strip().lower()
        size = normalize_shape_size(
            shape=shape,
            size_payload=payload.get('size'),
            radius_payload=payload.get('radius'),
            height_payload=payload.get('height'),
        )
        object_id = str(payload.get('object_id') or 'obstacle').strip() or 'obstacle'
        replace_existing = bool(payload.get('replace_existing', False))
        clear_pairs = bool(payload.get('clear_allowed_collision_pairs', False))
        attached = bool(payload.get('attached', False) or payload.get('attach_link'))
        attach_link = str(payload.get('attach_link', '') or '').strip()
        pairs = normalize_collision_pairs(payload.get('allowed_collision_pairs', ()))
        metadata_payload = payload.get('metadata')
        metadata = dict(metadata_payload) if isinstance(metadata_payload, Mapping) else {}
        return cls(
            object_id=object_id,
            center=center,
            size=size,
            shape=shape,
            replace_existing=replace_existing,
            attached=attached,
            attach_link=attach_link,
            allowed_collision_pairs=pairs,
            clear_allowed_collision_pairs=clear_pairs,
            metadata=metadata,
        )


class SceneAuthorityService:
    """Own canonical planning-scene mutations for the stable UI and runtime services.

    The service centralizes scene bootstrap, obstacle-id policy, collision-filter updates,
    attachment metadata, and summary metadata so presentation coordinators remain thin and all
    scene mutations travel through one explicit authority surface.
    """

    def __init__(self, *, scene_backend_runtime=None) -> None:
        """Create the canonical scene-authority service.

        Args:
            scene_backend_runtime: Optional executable scene-backend runtime. When omitted
                the shipped planning-scene backend runtime is used.

        Returns:
            None: Stores runtime collaborators only.

        Raises:
            None: Stateless collaborator wiring.
        """
        self._scene_backend_runtime = scene_backend_runtime or default_scene_backend_runtime()

    def ensure_scene(
        self,
        scene: PlanningScene | None,
        *,
        scene_summary: Mapping[str, object] | None = None,
        authority: str,
        edit_surface: str = 'stable_scene_editor',
    ) -> PlanningScene:
        """Return a canonical planning-scene authority instance.

        Args:
            scene: Existing planning scene, if any.
            scene_summary: Stable scene summary used as a bootstrap fallback when ``scene`` is
                absent but revision/backend data already exists in session state.
            authority: Stable authority label stored into scene metadata.
            edit_surface: Stable UI/editing surface label stored into scene metadata.

        Returns:
            PlanningScene: Canonical scene authority carrying stable metadata.

        Raises:
            ValueError: If a non-``PlanningScene`` object is supplied as ``scene``.
        """
        if scene is not None and not isinstance(scene, PlanningScene):
            raise ValueError('scene authority must be a PlanningScene instance or None')
        if scene is None:
            return self._scene_backend_runtime.bootstrap_scene(
                scene_summary=scene_summary,
                authority=str(authority),
                edit_surface=str(edit_surface),
            )
        metadata_updates = {
            'scene_authority': str(authority),
            'edit_surface': str(edit_surface),
            'stable_surface_version': str(scene.metadata.get('stable_surface_version', 'v3') or 'v3'),
            'geometry_authority_scope': str(scene.metadata.get('geometry_authority_scope', authority) or authority),
            'declaration_geometry_source': str(scene.metadata.get('declaration_geometry_source', scene.geometry_source) or scene.geometry_source),
            'validation_geometry_source': str(scene.metadata.get('validation_geometry_source', f'{scene.collision_backend}_planning_scene') or f'{scene.collision_backend}_planning_scene'),
            'render_geometry_source': str(scene.metadata.get('render_geometry_source', scene.geometry_source) or scene.geometry_source),
            'scene_geometry_contract_version': 'v1',
            'scene_validation_capability_matrix_version': 'v1',
        }
        if 'scene_fidelity' not in scene.metadata:
            metadata_updates['scene_fidelity'] = str(scene.geometry_source or 'generated')
        updated_scene = scene.with_metadata_patch(**metadata_updates)
        updated_scene = updated_scene.with_geometry_authority(SceneGeometryAuthority.from_scene(updated_scene))
        return updated_scene.with_scene_graph_authority(SceneGraphAuthority.from_scene(updated_scene, previous=updated_scene.scene_graph_authority))

    @staticmethod
    def _append_scene_command(scene: PlanningScene, command: SceneCommand) -> PlanningScene:
        """Attach replayable environment history without fabricating an extra mutation revision."""
        metadata = dict(scene.metadata or {})
        command_summary = command.summary()
        tail_limit = coerce_int(metadata.get('scene_command_log_tail_limit'), default=10, minimum=1, maximum=1024)
        history_limit = coerce_int(metadata.get('scene_command_history_limit'), default=256, minimum=1, maximum=4096)
        tail_history = list(metadata.get('scene_command_log_tail', ()) or ())
        full_history = list(metadata.get('scene_command_history', ()) or ())
        revision_history = list(metadata.get('scene_revision_history', ()) or ())
        tail_history.append(command_summary)
        full_history.append(command_summary)
        revision_history.append(
            {
                'revision': int(getattr(scene, 'revision', 0) or 0),
                'command_kind': str(command.command_kind or ''),
                'source': str(command.source or ''),
            }
        )
        replication_cursor = f"rev:{int(getattr(scene, 'revision', 0) or 0)}"
        metadata['last_scene_command'] = command_summary
        metadata['scene_command_log_tail'] = tail_history[-tail_limit:]
        metadata['scene_command_history'] = full_history[-history_limit:]
        metadata['scene_revision_history'] = revision_history[-history_limit:]
        metadata['scene_replay_cursor'] = replication_cursor
        metadata['scene_command_log_policy'] = {
            'retention_model': 'bounded_tail_plus_history',
            'history_limit': int(history_limit),
            'tail_limit': int(tail_limit),
            'intended_use': 'diagnostic_log_and_replay',
            'supports_replay': True,
            'supports_clone': True,
            'supports_diff_replication': True,
            'supports_concurrent_snapshots': True,
        }
        metadata['environment_contract'] = {
            'version': 'v2',
            'supports_clone': True,
            'supports_replay': True,
            'supports_diff_replication': True,
            'supports_concurrent_snapshots': True,
        }
        metadata['scene_replication_state'] = {
            'cursor': replication_cursor,
            'base_revision': int(getattr(scene, 'revision', 0) or 0),
            'history_size': int(len(metadata['scene_command_history'])),
        }
        return scene._spawn(metadata=metadata, revision=scene.revision)

    @staticmethod
    def _build_scene_command(
        *,
        scene_before: PlanningScene,
        scene_after: PlanningScene,
        command_kind: str,
        source: str,
        object_id: str = '',
        metadata: Mapping[str, object] | None = None,
    ) -> SceneCommand:
        scene_metadata = dict(getattr(scene_after, 'metadata', {}) or {})
        return SceneCommand(
            command_kind=str(command_kind),
            source=str(source),
            object_id=str(object_id or ''),
            revision_before=int(getattr(scene_before, 'revision', 0) or 0),
            revision_after=int(getattr(scene_after, 'revision', 0) or 0),
            scene_graph_diff=dict(scene_metadata.get('scene_graph_diff', {}) or {}),
            metadata=dict(metadata or {}),
        )

    def execute_obstacle_edit(
        self,
        scene: PlanningScene,
        edit: SceneObstacleEdit,
        *,
        source: str,
    ) -> SceneMutationResult:
        """Apply one stable obstacle/attachment mutation and emit the command projection."""
        scene_before = scene
        updated_scene = self.apply_obstacle_edit(scene, edit, source=source)
        command_kind = 'upsert_attached_object' if edit.attached else 'upsert_obstacle'
        actual_object_id = str(getattr(updated_scene, 'metadata', {}).get('last_edit_object_id', edit.object_id) or edit.object_id)
        command = self._build_scene_command(
            scene_before=scene_before,
            scene_after=updated_scene,
            command_kind=command_kind,
            source=source,
            object_id=actual_object_id,
            metadata={
                'shape': str(edit.shape),
                'center': [float(value) for value in edit.center],
                'size': [float(value) for value in edit.size],
                'replace_existing': bool(edit.replace_existing),
                'attached': bool(edit.attached),
                'attach_link': str(edit.attach_link),
                'allowed_collision_pairs': [list(pair) for pair in edit.allowed_collision_pairs],
                'clear_allowed_collision_pairs': bool(edit.clear_allowed_collision_pairs),
                'allowed_collision_pair_count': int(len(edit.allowed_collision_pairs)),
            },
        )
        return SceneMutationResult(scene=self._append_scene_command(updated_scene, command), command=command)

    def execute_clear_obstacles(
        self,
        scene: PlanningScene,
        *,
        source: str,
    ) -> SceneMutationResult:
        """Clear scene obstacles through the command-based scene-authority surface."""
        scene_before = scene
        updated_scene = scene.clear_obstacles()
        command = self._build_scene_command(
            scene_before=scene_before,
            scene_after=updated_scene,
            command_kind='clear_obstacles',
            source=source,
            metadata={'cleared_obstacle_count': int(len(getattr(scene_before, 'obstacles', ()) or ()))},
        )
        return SceneMutationResult(scene=self._append_scene_command(updated_scene, command), command=command)

    def apply_obstacle_edit(
        self,
        scene: PlanningScene,
        edit: SceneObstacleEdit,
        *,
        source: str,
    ) -> PlanningScene:
        """Apply one stable scene-editor mutation.

        Args:
            scene: Current canonical planning scene.
            edit: Typed user request describing object, attachment, and ACM changes.
            source: Stable source label written into object metadata.

        Returns:
            PlanningScene: Updated planning scene.

        Raises:
            ValueError: If the numeric vectors are not finite.

        Boundary behavior:
            Duplicate identifiers are either replaced or deterministically suffixed depending on
            ``edit.replace_existing``. ACM updates happen in the same mutation path so UI and
            validation consume one consistent authority snapshot.
        """
        center = np.asarray(edit.center, dtype=float).reshape(3)
        size = np.asarray(edit.size, dtype=float).reshape(3)
        if not np.isfinite(center).all() or not np.isfinite(size).all() or np.any(size <= 0.0):
            raise ValueError('scene obstacle center/size must be finite positive vectors')
        declaration_geometry = _declaration_geometry_payload(shape=edit.shape, center=center, size=size)
        projection = project_declaration_geometry(
            declaration_geometry,
            backend_id=scene.collision_backend,
            attached=bool(edit.attached),
        )
        metadata = {
            'source': str(source),
            'shape': str(edit.shape),
            'size': [float(value) for value in size.tolist()],
            'editor': 'stable_scene_editor',
            'declaration_geometry': dict(projection.declaration_geometry),
            'validation_geometry': dict(projection.validation_geometry),
            'render_geometry': dict(projection.render_geometry),
            'validation_query_geometry': _validation_geometry_payload(projection.query_aabb),
            'validation_backend': str(projection.validation_backend),
            'validation_adapter_kind': str(projection.adapter_kind),
            'declaration_geometry_source': 'stable_scene_editor',
            'validation_geometry_source': str(projection.validation_geometry_source),
            'render_geometry_source': 'stable_scene_editor',
            'scene_geometry_contract_version': 'v1',
            'scene_validation_capability_matrix_version': 'v1',
            **dict(edit.metadata),
        }
        scene.geometry_authority.require_declared_and_resolved()
        scene.geometry_authority.require_three_layer_contract()
        scene.geometry_authority.require_supported_shape(edit.shape)
        if edit.attached:
            metadata['attach_link'] = str(edit.attach_link)
            updated_scene = self._upsert_attached_object(scene, edit.object_id, declaration_geometry, metadata=metadata, collision_backend=scene.collision_backend, replace_existing=edit.replace_existing)
            actual_object_id = str(getattr(updated_scene, 'attached_object_ids', ())[-1] if getattr(updated_scene, 'attached_object_ids', ()) else edit.object_id)
        else:
            obstacle_id = edit.object_id if edit.replace_existing else self.next_object_id(scene, edit.object_id)
            replacement = self._scene_backend_runtime.build_scene_object(
                object_id=obstacle_id,
                declaration_geometry=declaration_geometry,
                metadata=metadata,
                collision_backend=scene.collision_backend,
                attached=False,
            )
            if obstacle_id in set(scene.obstacle_ids):
                updated_scene = scene.replace_obstacles(tuple(replacement if obj.object_id == obstacle_id else obj for obj in scene.obstacles))
            else:
                updated_scene = scene._spawn(obstacles=scene.obstacles + (replacement,), revision=scene.revision + 1)
            actual_object_id = str(obstacle_id)
        updated_scene = self.apply_allowed_collision_pairs(
            updated_scene,
            edit.allowed_collision_pairs,
            clear_existing=edit.clear_allowed_collision_pairs,
        )
        last_edit_kind = 'attached_object' if edit.attached else 'obstacle'
        updated_scene = updated_scene.with_metadata_patch(
            last_edit_source=str(source),
            last_edit_kind=last_edit_kind,
            last_edit_object_id=str(actual_object_id),
            declaration_geometry_source='stable_scene_editor',
            validation_geometry_source=f'{updated_scene.collision_backend}_planning_scene',
            render_geometry_source='stable_scene_editor',
            scene_geometry_contract='declaration_validation_render',
            environment_contract_version='v2',
        )
        refreshed = SceneGeometryAuthority.from_scene(updated_scene)
        authority = SceneGeometryAuthority(
            authority=refreshed.authority,
            authority_kind=refreshed.authority_kind,
            scene_geometry_contract='declaration_validation_render',
            declaration_geometry_source='stable_scene_editor',
            validation_geometry_source=f'{updated_scene.collision_backend}_planning_scene',
            render_geometry_source='stable_scene_editor',
            supported_scene_shapes=tuple(sorted(SUPPORTED_SCENE_SHAPES)),
            records=refreshed.records,
            metadata=dict(refreshed.metadata),
        )
        updated_scene = updated_scene.with_geometry_authority(authority)
        return self._scene_backend_runtime.refresh_scene_authority(updated_scene)

    def apply_allowed_collision_pairs(
        self,
        scene: PlanningScene,
        pairs: Iterable[tuple[str, str]],
        *,
        clear_existing: bool,
    ) -> PlanningScene:
        """Apply explicit collision-filter pairs to the ACM.

        Args:
            scene: Current planning scene.
            pairs: Normalized pair identifiers to allow.
            clear_existing: Whether to clear the ACM before adding ``pairs``.

        Returns:
            PlanningScene: Updated scene with the requested ACM state.

        Raises:
            ValueError: If any pair does not contain exactly two non-empty identifiers.
        """
        normalized_pairs = normalize_collision_pairs(pairs)
        acm = AllowedCollisionMatrix() if clear_existing else scene.allowed_collision_matrix
        for a, b in normalized_pairs:
            acm = acm.allow(a, b)
        if acm == scene.allowed_collision_matrix:
            return scene
        return scene.with_acm(acm)

    def clone_scene(
        self,
        scene: PlanningScene,
        *,
        planner_id: str = '',
        clone_reason: str = 'concurrent_snapshot',
    ) -> PlanningScene:
        """Create a read-only clone marker for concurrent planners/validators.

        The clone shares immutable scene content while projecting independent snapshot metadata
        used by export/session/diagnostics surfaces.
        """
        metadata = dict(scene.metadata or {})
        clone_generation = coerce_int(metadata.get('clone_generation'), default=0, minimum=0, maximum=1_000_000) + 1
        clone_token = f"scene:{int(scene.revision)}:clone:{clone_generation}:{str(planner_id or 'anonymous')}"
        concurrent_tokens = list(metadata.get('concurrent_snapshot_tokens', ()) or ())
        concurrent_tokens.append(clone_token)
        metadata.update(
            {
                'clone_generation': int(clone_generation),
                'latest_clone_token': clone_token,
                'latest_clone_reason': str(clone_reason or 'concurrent_snapshot'),
                'latest_clone_planner_id': str(planner_id or ''),
                'concurrent_snapshot_tokens': concurrent_tokens[-64:],
                'environment_contract_version': 'v2',
            }
        )
        return scene._spawn(metadata=metadata, revision=scene.revision)

    def apply_scene_command(self, scene: PlanningScene, command: Mapping[str, object], *, source: str = 'scene_replay') -> SceneMutationResult:
        """Replay one canonical scene command onto a planning scene.

        Args:
            scene: Base scene used as replay input.
            command: Machine-readable command payload previously emitted by this service.
            source: Source label recorded for replayed mutations.

        Returns:
            SceneMutationResult: Replayed scene plus the emitted canonical command.

        Raises:
            ValueError: If the command payload is malformed or unsupported.
        """
        payload = dict(command or {})
        command_kind = str(payload.get('command_kind', '') or '').strip()
        object_id = str(payload.get('object_id', '') or '').strip()
        metadata = dict(payload.get('metadata', {}) or {})
        if command_kind in {'upsert_obstacle', 'upsert_attached_object'}:
            center = metadata.get('center')
            size = metadata.get('size')
            if center in (None, '') or size in (None, ''):
                raise ValueError('scene replay command is missing center/size payload')
            edit = SceneObstacleEdit(
                object_id=object_id or 'replayed_object',
                center=tuple(float(value) for value in center),
                size=tuple(float(value) for value in size),
                shape=str(metadata.get('shape', 'box') or 'box'),
                replace_existing=bool(metadata.get('replace_existing', True)),
                attached=command_kind == 'upsert_attached_object' or bool(metadata.get('attached', False)),
                attach_link=str(metadata.get('attach_link', '') or ''),
                allowed_collision_pairs=tuple(tuple(str(part) for part in pair) for pair in metadata.get('allowed_collision_pairs', ()) or ()),
                clear_allowed_collision_pairs=bool(metadata.get('clear_allowed_collision_pairs', False)),
            )
            return self.execute_obstacle_edit(scene, edit, source=str(source))
        if command_kind == 'clear_obstacles':
            return self.execute_clear_obstacles(scene, source=str(source))
        raise ValueError(f'unsupported scene replay command: {command_kind}')

    def replay_scene(
        self,
        scene: PlanningScene,
        commands: Iterable[Mapping[str, object]],
        *,
        source: str = 'scene_replay',
        planner_id: str = '',
    ) -> PlanningScene:
        """Replay a sequence of canonical commands onto a cloned scene snapshot."""
        recorded_commands = tuple(dict(item) for item in commands)
        replay_scene = self.clone_scene(scene, planner_id=planner_id, clone_reason='replay')
        current = replay_scene
        for item in recorded_commands:
            current = self.apply_scene_command(current, item, source=source).scene
        metadata = dict(current.metadata or {})
        metadata['last_replay_source'] = str(source)
        metadata['last_replay_command_count'] = int(len(recorded_commands))
        return current._spawn(metadata=metadata, revision=current.revision)

    @staticmethod
    def next_object_id(scene: PlanningScene, requested_id: str) -> str:
        """Return a stable scene-object identifier that does not collide with existing ids."""
        base = str(requested_id or 'obstacle').strip() or 'obstacle'
        existing = set(getattr(scene, 'obstacle_ids', ()) or ()) | set(getattr(scene, 'attached_object_ids', ()) or ())
        if base not in existing:
            return base
        suffix = 2
        while f'{base}_{suffix}' in existing:
            suffix += 1
        return f'{base}_{suffix}'

    @staticmethod
    def _upsert_attached_object(
        scene: PlanningScene,
        object_id: str,
        declaration_geometry: Mapping[str, object],
        *,
        metadata: dict[str, object],
        collision_backend: str,
        replace_existing: bool,
    ) -> PlanningScene:
        normalized_id = str(object_id or 'attached').strip() or 'attached'
        attached_objects = tuple(getattr(scene, 'attached_objects', ()) or ())
        existing_ids = {obj.object_id for obj in attached_objects}
        if not replace_existing and normalized_id in existing_ids:
            normalized_id = SceneAuthorityService.next_object_id(scene, normalized_id)
        replacement = default_scene_backend_runtime().build_scene_object(
            object_id=normalized_id,
            declaration_geometry=declaration_geometry,
            metadata=dict(metadata),
            collision_backend=collision_backend,
            attached=True,
        )
        if normalized_id not in existing_ids:
            return scene._spawn(attached_objects=attached_objects + (replacement,), revision=scene.revision + 1)
        updated = tuple(replacement if obj.object_id == normalized_id else obj for obj in attached_objects)
        if updated == attached_objects:
            return scene
        return scene._spawn(attached_objects=updated, revision=scene.revision + 1)


