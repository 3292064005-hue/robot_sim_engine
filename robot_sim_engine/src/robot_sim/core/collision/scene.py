from __future__ import annotations

from dataclasses import dataclass, field, replace

from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import AABB
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.collision_fidelity import summarize_collision_fidelity, validation_backend_capability_matrix
from robot_sim.domain.enums import CollisionLevel
from robot_sim.model.scene_geometry_authority import (
    SceneGeometryAuthority,
    default_scene_geometry_authority,
    summarize_scene_geometry_authority,
)
from robot_sim.model.scene_geometry_projection import declaration_geometry_from_aabb, project_declaration_geometry
from robot_sim.model.scene_graph_authority import SceneGraphAuthority
from robot_sim.model.scene_validation_surface import summarize_record_validation_surface, summarize_scene_validation_surface, summarize_scene_validation_projection, summarize_validation_projection

_COLLISION_BACKEND_REGISTRY = default_collision_backend_registry()
_COLLISION_BACKEND_FALLBACK = _COLLISION_BACKEND_REGISTRY.default_backend


def _serialize_aabb(geometry: AABB) -> dict[str, object]:
    return {
        'kind': 'aabb',
        'minimum': [float(value) for value in geometry.minimum],
        'maximum': [float(value) for value in geometry.maximum],
    }


def _scene_geometry_payload_from_metadata(metadata: dict[str, object], key: str, fallback: dict[str, object]) -> dict[str, object]:
    payload = metadata.get(key)
    if isinstance(payload, dict):
        return dict(payload)
    return dict(fallback)


def _normalize_scene_shapes(payload: object) -> list[str]:
    if isinstance(payload, (list, tuple, set)):
        return [str(item) for item in payload]
    return []


def _normalize_scene_object_sequence(objects: tuple['SceneObject', ...], *, validation_backend: str) -> list[dict[str, object]]:
    return [obj.summary(validation_backend=validation_backend) for obj in objects]


def _stable_scene_object_metadata(metadata: dict[str, object]) -> dict[str, object]:
    stable_keys = {'source', 'shape', 'size', 'editor', 'attach_link'}
    normalized: dict[str, object] = {}
    for key in stable_keys:
        if key not in metadata:
            continue
        value = metadata[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            normalized[str(key)] = value
        elif isinstance(value, (list, tuple)):
            normalized[str(key)] = list(value)
    return normalized


def _normalize_collision_backend(backend_id: str, metadata: dict[str, object] | None = None) -> tuple[str, dict[str, object]]:
    """Normalize a requested collision backend against the canonical registry."""
    return _COLLISION_BACKEND_REGISTRY.normalize_backend(str(backend_id), metadata=metadata)


@dataclass(frozen=True)
class SceneObject:
    object_id: str
    geometry: AABB
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        metadata = dict(self.metadata or {})
        declaration_geometry = _scene_geometry_payload_from_metadata(
            metadata,
            'declaration_geometry',
            _scene_geometry_payload_from_metadata(metadata, 'declaration_geometry', declaration_geometry_from_aabb(self.geometry)),
        )
        validation_backend = str(metadata.get('validation_backend', metadata.get('resolved_collision_backend', 'aabb')) or 'aabb')
        projection = project_declaration_geometry(
            declaration_geometry,
            backend_id=validation_backend,
            attached=bool('attach_link' in metadata),
            fallback_geometry=self.geometry,
        )
        metadata.setdefault('declaration_geometry', dict(projection.declaration_geometry))
        metadata.setdefault('validation_geometry', dict(projection.validation_geometry))
        metadata.setdefault('render_geometry', dict(projection.render_geometry))
        metadata.setdefault('validation_query_geometry', _serialize_aabb(projection.query_aabb))
        metadata.setdefault('validation_backend', str(projection.validation_backend))
        metadata.setdefault('validation_adapter_kind', str(projection.adapter_kind))
        metadata.setdefault('validation_geometry_source', str(projection.validation_geometry_source))
        metadata.setdefault('render_geometry_source', str(metadata.get('render_geometry_source', metadata.get('source', '')) or metadata.get('source', '')))
        metadata.setdefault('declaration_geometry_source', str(metadata.get('declaration_geometry_source', metadata.get('source', '')) or metadata.get('source', '')))
        object.__setattr__(self, 'metadata', metadata)

    def summary(self, *, validation_backend: str | None = None) -> dict[str, object]:
        metadata = dict(self.metadata or {})
        declared_backend = str(validation_backend or metadata.get('validation_backend', metadata.get('resolved_collision_backend', 'aabb')) or 'aabb')
        declaration_geometry = _scene_geometry_payload_from_metadata(
            metadata,
            'declaration_geometry',
            _scene_geometry_payload_from_metadata(metadata, 'declaration_geometry', declaration_geometry_from_aabb(self.geometry)),
        )
        projection = project_declaration_geometry(
            declaration_geometry,
            backend_id=declared_backend,
            attached=bool('attach_link' in metadata),
            fallback_geometry=self.geometry,
        )
        validation_geometry = dict(projection.validation_geometry)
        render_geometry = _scene_geometry_payload_from_metadata(
            metadata,
            'render_geometry',
            dict(projection.render_geometry),
        )
        validation_geometry_source = str(metadata.get('validation_geometry_source', projection.validation_geometry_source) or projection.validation_geometry_source)
        validation_surface = summarize_record_validation_surface(
            validation_geometry_source=validation_geometry_source,
            validation_geometry=validation_geometry,
            attached=bool('attach_link' in metadata),
        )
        validation_projection = summarize_validation_projection(
            declaration_geometry=declaration_geometry,
            validation_geometry=validation_geometry,
            validation_geometry_source=validation_geometry_source,
            attached=bool('attach_link' in metadata),
        )
        return {
            'object_id': str(self.object_id),
            'metadata': _stable_scene_object_metadata(metadata),
            'declaration_geometry': declaration_geometry,
            'validation_geometry': validation_geometry,
            'render_geometry': render_geometry,
            'validation_surface': validation_surface,
            'validation_projection': validation_projection,
            'declaration_geometry_source': str(metadata.get('declaration_geometry_source', metadata.get('source', '')) or metadata.get('source', '')),
            'validation_geometry_source': validation_geometry_source,
            'render_geometry_source': str(metadata.get('render_geometry_source', metadata.get('source', '')) or metadata.get('source', '')),
            'validation_backend': str(projection.validation_backend),
            'validation_adapter_kind': str(projection.adapter_kind),
            'validation_query_geometry': _serialize_aabb(projection.query_aabb),
            **validation_surface,
        }


@dataclass(frozen=True)
class PlanningScene:
    """Immutable planning-scene authority used by validation, export, and stable scene UI.

    The scene now carries a first-class ``geometry_authority`` contract instead of reconstructing
    authority summaries only at export time. Scene editing, validation summaries, session export,
    and diagnostics therefore read one structured geometry truth source.
    """

    obstacles: tuple[SceneObject, ...] = ()
    allowed_collision_matrix: AllowedCollisionMatrix = field(default_factory=AllowedCollisionMatrix)
    revision: int = 0
    collision_level: CollisionLevel = CollisionLevel.AABB
    self_collision_padding: float = 0.03
    environment_collision_padding: float = 0.02
    ignore_adjacent_self_collisions: bool = True
    geometry_source: str = 'generated'
    collision_backend: str = _COLLISION_BACKEND_FALLBACK
    attached_objects: tuple[SceneObject, ...] = ()
    clearance_policy: str = 'min_distance'
    metadata: dict[str, object] = field(default_factory=dict)
    geometry_authority: SceneGeometryAuthority = field(default_factory=default_scene_geometry_authority)
    scene_graph_authority: SceneGraphAuthority = field(default_factory=SceneGraphAuthority)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        authority = self.geometry_authority
        if not isinstance(authority, SceneGeometryAuthority):
            authority = default_scene_geometry_authority()
        object.__setattr__(self, 'geometry_authority', authority)
        scene_graph_authority = self.scene_graph_authority
        if not isinstance(scene_graph_authority, SceneGraphAuthority):
            scene_graph_authority = SceneGraphAuthority.from_scene(self)
        elif (
            not tuple(scene_graph_authority.frame_ids)
            or 'query:allowed_collision_matrix' not in set(scene_graph_authority.capability_badges)
        ):
            scene_graph_authority = SceneGraphAuthority.from_scene(self, previous=scene_graph_authority)
        object.__setattr__(self, 'scene_graph_authority', scene_graph_authority)

    @property
    def obstacle_ids(self) -> tuple[str, ...]:
        return tuple(obj.object_id for obj in self.obstacles)

    @property
    def attached_object_ids(self) -> tuple[str, ...]:
        """Return the canonical attached-object identifiers in insertion order."""
        return tuple(obj.object_id for obj in self.attached_objects)

    @property
    def allowed_collision_pairs(self) -> tuple[tuple[str, str], ...]:
        """Return normalized ACM pairs as a stable, sorted tuple."""
        return tuple(sorted(self.allowed_collision_matrix.allowed_pairs))

    @property
    def scene_authority(self) -> str:
        """Return the canonical runtime authority label for this scene."""
        return str(self.geometry_authority.authority or 'planning_scene')

    @property
    def scene_fidelity(self) -> str:
        """Return the stable scene-fidelity label surfaced to diagnostics/export."""
        return str(
            self.geometry_authority.metadata.get('scene_fidelity', self.metadata.get('scene_fidelity', self.geometry_source))
            or self.metadata.get('scene_fidelity', self.geometry_source)
            or self.geometry_source
        )

    @property
    def edit_surface(self) -> str:
        """Return the stable UI surface allowed to mutate this scene."""
        return str(self.metadata.get('edit_surface', 'stable_scene_editor') or 'stable_scene_editor')

    def _spawn(self, **updates) -> 'PlanningScene':
        """Return a new scene with copied metadata and caller-supplied field updates."""
        explicit_geometry_authority = 'geometry_authority' in updates
        updates.setdefault('metadata', dict(self.metadata))
        updates.setdefault('geometry_authority', self.geometry_authority)
        spawned = replace(self, **updates)
        if {'obstacles', 'attached_objects', 'collision_backend', 'geometry_source'} & set(updates):
            if not explicit_geometry_authority:
                refreshed = summarize_scene_geometry_authority(spawned)
                if refreshed != spawned.geometry_authority:
                    spawned = replace(spawned, geometry_authority=refreshed)
            refreshed_graph = SceneGraphAuthority.from_scene(spawned, previous=self.scene_graph_authority)
            refreshed_diff = refreshed_graph.diff_from(self.scene_graph_authority).summary()
            refreshed_metadata = dict(spawned.metadata)
            refreshed_metadata['scene_graph_diff'] = refreshed_diff
            if refreshed_metadata != spawned.metadata:
                spawned = replace(spawned, metadata=refreshed_metadata)
            if refreshed_graph != spawned.scene_graph_authority:
                spawned = replace(spawned, scene_graph_authority=refreshed_graph)
        return spawned

    def add_obstacle(self, object_id: str, geometry: AABB, *, metadata: dict[str, object] | None = None) -> 'PlanningScene':
        return self._spawn(
            obstacles=self.obstacles + (SceneObject(object_id=object_id, geometry=geometry, metadata=dict(metadata or {})),),
            revision=self.revision + 1,
        )

    def upsert_obstacle(self, object_id: str, geometry: AABB, *, metadata: dict[str, object] | None = None) -> 'PlanningScene':
        normalized_id = str(object_id)
        replacement = SceneObject(object_id=normalized_id, geometry=geometry, metadata=dict(metadata or {}))
        if normalized_id not in set(self.obstacle_ids):
            return self.add_obstacle(normalized_id, geometry, metadata=metadata)
        updated: list[SceneObject] = []
        for obstacle in self.obstacles:
            updated.append(replacement if obstacle.object_id == normalized_id else obstacle)
        return self._spawn(obstacles=tuple(updated), revision=self.revision + 1)

    def remove_obstacle(self, object_id: str) -> 'PlanningScene':
        remaining = tuple(obj for obj in self.obstacles if obj.object_id != str(object_id))
        if remaining == self.obstacles:
            return self
        return self._spawn(obstacles=remaining, revision=self.revision + 1)

    def clear_obstacles(self) -> 'PlanningScene':
        if not self.obstacles:
            return self
        return self._spawn(obstacles=(), revision=self.revision + 1)

    def replace_obstacles(self, obstacles: tuple[SceneObject, ...] | list[SceneObject]) -> 'PlanningScene':
        normalized = tuple(obstacles)
        if normalized == self.obstacles:
            return self
        return self._spawn(obstacles=normalized, revision=self.revision + 1)

    def with_acm(self, allowed_collision_matrix: AllowedCollisionMatrix) -> 'PlanningScene':
        if allowed_collision_matrix == self.allowed_collision_matrix:
            return self
        return self._spawn(allowed_collision_matrix=allowed_collision_matrix, revision=self.revision + 1)

    def allow_collision(self, a: str, b: str) -> 'PlanningScene':
        updated = self.allowed_collision_matrix.allow(a, b)
        return self.with_acm(updated)

    def forbid_collision(self, a: str, b: str) -> 'PlanningScene':
        updated = self.allowed_collision_matrix.forbid(a, b)
        return self.with_acm(updated)

    def clear_allowed_collisions(self) -> 'PlanningScene':
        if not self.allowed_collision_pairs:
            return self
        return self.with_acm(AllowedCollisionMatrix())

    def with_revision_bump(self) -> 'PlanningScene':
        return self._spawn(revision=self.revision + 1)

    def with_collision_backend(self, backend_id: str) -> 'PlanningScene':
        resolved_backend, metadata = _normalize_collision_backend(str(backend_id), metadata=self.metadata)
        return self._spawn(collision_backend=resolved_backend, revision=self.revision + 1, metadata=metadata)

    def with_metadata_patch(self, **metadata_updates: object) -> 'PlanningScene':
        merged = dict(self.metadata)
        merged.update({str(key): value for key, value in metadata_updates.items()})
        if merged == self.metadata:
            return self
        return self._spawn(metadata=merged, revision=self.revision + 1)

    def with_geometry_authority(self, geometry_authority: SceneGeometryAuthority) -> 'PlanningScene':
        if not isinstance(geometry_authority, SceneGeometryAuthority):
            raise ValueError('geometry_authority must be a SceneGeometryAuthority instance')
        if geometry_authority == self.geometry_authority:
            return self
        return replace(self, geometry_authority=geometry_authority)

    def with_scene_graph_authority(self, scene_graph_authority: SceneGraphAuthority) -> 'PlanningScene':
        """Return a scene with an explicit scene-graph/query authority override.

        Args:
            scene_graph_authority: Explicit scene-graph/query authority to attach.

        Returns:
            PlanningScene: Updated immutable planning scene.

        Raises:
            ValueError: If ``scene_graph_authority`` is not a ``SceneGraphAuthority`` instance.

        Boundary behavior:
            When the graph authority changes, the method also refreshes
            ``metadata['scene_graph_diff']`` against the previously attached graph so summary and
            diagnostics surfaces continue to project one consistent diff snapshot. Metadata-only
            updates no longer recompute scene-graph state through :meth:`_spawn`.
        """
        if not isinstance(scene_graph_authority, SceneGraphAuthority):
            raise ValueError('scene_graph_authority must be a SceneGraphAuthority instance')
        if scene_graph_authority == self.scene_graph_authority:
            return self
        refreshed_metadata = dict(self.metadata)
        refreshed_metadata['scene_graph_diff'] = scene_graph_authority.diff_from(self.scene_graph_authority).summary()
        return replace(self, scene_graph_authority=scene_graph_authority, metadata=refreshed_metadata)

    def attach_object(self, object_id: str, geometry: AABB, *, metadata: dict[str, object] | None = None) -> 'PlanningScene':
        return self._spawn(
            attached_objects=self.attached_objects + (SceneObject(object_id=object_id, geometry=geometry, metadata=dict(metadata or {})),),
            revision=self.revision + 1,
        )

    def detach_object(self, object_id: str) -> 'PlanningScene':
        remaining = tuple(obj for obj in self.attached_objects if obj.object_id != str(object_id))
        if remaining == self.attached_objects:
            return self
        return self._spawn(attached_objects=remaining, revision=self.revision + 1)

    def clone(self, *, planner_id: str = '', clone_reason: str = 'concurrent_snapshot') -> 'PlanningScene':
        """Return a clone-marked scene preserving immutable geometry and revision state."""
        metadata = dict(self.metadata or {})
        clone_generation = int(metadata.get('clone_generation', 0) or 0) + 1
        clone_token = f"scene:{int(self.revision)}:clone:{clone_generation}:{str(planner_id or 'anonymous')}"
        concurrent_tokens = list(metadata.get('concurrent_snapshot_tokens', ()) or ())
        concurrent_tokens.append(clone_token)
        metadata.update(
            {
                'clone_generation': clone_generation,
                'latest_clone_token': clone_token,
                'latest_clone_reason': str(clone_reason or 'concurrent_snapshot'),
                'latest_clone_planner_id': str(planner_id or ''),
                'concurrent_snapshot_tokens': concurrent_tokens[-64:],
                'environment_contract_version': 'v2',
            }
        )
        return self._spawn(metadata=metadata, revision=self.revision)

    def diff_replication_summary(self, previous: 'PlanningScene | None' = None) -> dict[str, object]:
        """Return a stable diff-replication summary between two immutable scene revisions."""
        baseline = previous or self
        added_obstacles = sorted(set(self.obstacle_ids) - set(getattr(baseline, 'obstacle_ids', ()) or ()))
        removed_obstacles = sorted(set(getattr(baseline, 'obstacle_ids', ()) or ()) - set(self.obstacle_ids))
        added_attached = sorted(set(self.attached_object_ids) - set(getattr(baseline, 'attached_object_ids', ()) or ()))
        removed_attached = sorted(set(getattr(baseline, 'attached_object_ids', ()) or ()) - set(self.attached_object_ids))
        return {
            'base_revision': int(getattr(baseline, 'revision', self.revision) or self.revision),
            'target_revision': int(self.revision),
            'added_obstacle_ids': added_obstacles,
            'removed_obstacle_ids': removed_obstacles,
            'added_attached_object_ids': added_attached,
            'removed_attached_object_ids': removed_attached,
            'obstacle_delta': int(len(added_obstacles) - len(removed_obstacles)),
            'attached_object_delta': int(len(added_attached) - len(removed_attached)),
            'change_count': int(len(added_obstacles) + len(removed_obstacles) + len(added_attached) + len(removed_attached)),
            'scene_graph_diff': dict(self.metadata.get('scene_graph_diff', {}) or {}),
        }

    def summary(self) -> dict[str, object]:
        geometry_authority = self.geometry_authority.summary()
        validation_projection = summarize_scene_validation_projection([*(_normalize_scene_object_sequence(self.obstacles, validation_backend=self.collision_backend)), *(_normalize_scene_object_sequence(self.attached_objects, validation_backend=self.collision_backend))])
        collision_fidelity = summarize_collision_fidelity(
            collision_level=self.collision_level,
            collision_backend=self.collision_backend,
            scene_fidelity=self.scene_fidelity,
            experimental_backends_enabled=bool(self.metadata.get('experimental_backends_enabled', self.collision_backend != 'capsule')),
        )
        capability_badges = [
            f'collision_backend:{self.collision_backend}',
            f'collision_level:{getattr(self.collision_level, "value", str(self.collision_level))}',
            f'collision_precision:{collision_fidelity["precision"]}',
            f'scene_authority:{self.scene_authority}',
            f'scene_fidelity:{self.scene_fidelity}',
            f'edit_surface:{self.edit_surface}',
        ]
        capability_badges.extend(item for item in geometry_authority.get('capability_badges', []) if item not in capability_badges)
        scene_graph_authority = self.scene_graph_authority.summary()
        capability_badges.extend(item for item in scene_graph_authority.get('capability_badges', []) if item not in capability_badges)
        validation_surface = summarize_scene_validation_surface(
            collision_backend=str(self.collision_backend),
            scene_fidelity=self.scene_fidelity,
            scene_authority=self.scene_authority,
            scene_geometry_contract=str(self.geometry_authority.scene_geometry_contract or 'declaration_validation_render'),
            attached_object_count=len(self.attached_objects),
            source=str(self.metadata.get('scene_source', 'planning_scene') or 'planning_scene'),
        )
        summary = {
            'revision': int(self.revision),
            'collision_backend': str(self.collision_backend),
            'requested_collision_backend': str(self.metadata.get('requested_collision_backend', self.collision_backend)),
            'resolved_collision_backend': str(self.metadata.get('resolved_collision_backend', self.collision_backend)),
            'obstacle_ids': list(self.obstacle_ids),
            'attached_object_ids': list(self.attached_object_ids),
            'allowed_collision_pairs': [list(pair) for pair in self.allowed_collision_pairs],
            'collision_filter_pair_count': int(len(self.allowed_collision_pairs)),
            'collision_level': getattr(self.collision_level, 'value', str(self.collision_level)),
            'self_collision_padding': float(self.self_collision_padding),
            'environment_collision_padding': float(self.environment_collision_padding),
            'ignore_adjacent_self_collisions': bool(self.ignore_adjacent_self_collisions),
            'geometry_source': str(self.geometry_source),
            'scene_authority': self.scene_authority,
            'scene_fidelity': self.scene_fidelity,
            'collision_fidelity': collision_fidelity,
            'edit_surface': self.edit_surface,
            'clearance_policy': str(self.clearance_policy),
            'obstacle_count': int(len(self.obstacles)),
            'attached_object_count': int(len(self.attached_objects)),
            'stable_surface_version': str(self.metadata.get('stable_surface_version', 'v3')), 
            'scene_geometry_contract': str(self.geometry_authority.scene_geometry_contract or 'declaration_validation_render'),
            'scene_geometry_contract_version': str(self.metadata.get('scene_geometry_contract_version', 'v1') or 'v1'),
            'scene_validation_capability_matrix_version': str(self.metadata.get('scene_validation_capability_matrix_version', 'v1') or 'v1'),
            'validation_backend_capabilities': validation_backend_capability_matrix(
                experimental_enabled=bool(self.metadata.get('experimental_backends_enabled', self.collision_backend != 'capsule'))
            ),
            'declaration_geometry_source': str(self.geometry_authority.declaration_geometry_source or ''),
            'validation_geometry_source': str(self.geometry_authority.validation_geometry_source or ''),
            'render_geometry_source': str(self.geometry_authority.render_geometry_source or ''),
            'capability_badges': capability_badges,
            'geometry_authority': geometry_authority,
            'validation_projection': validation_projection,
            'scene_graph_authority': scene_graph_authority,
            'validation_surface': validation_surface,
            'scene_graph_diff': dict(self.metadata.get('scene_graph_diff', {}) or {}),
            'last_scene_command': dict(self.metadata.get('last_scene_command', {}) or {}),
            'scene_command_log_tail': [dict(item) for item in self.metadata.get('scene_command_log_tail', ()) or () if isinstance(item, dict)],
            'scene_command_history': [dict(item) for item in self.metadata.get('scene_command_history', ()) or () if isinstance(item, dict)],
            'scene_revision_history': [dict(item) for item in self.metadata.get('scene_revision_history', ()) or () if isinstance(item, dict)],
            'replay_cursor': str(self.metadata.get('scene_replay_cursor', f'rev:{int(self.revision)}') or f'rev:{int(self.revision)}'),
            'clone_token': str(self.metadata.get('latest_clone_token', '') or ''),
            'concurrent_snapshot_tokens': [str(item) for item in self.metadata.get('concurrent_snapshot_tokens', ()) or ()],
            'diff_replication': self.diff_replication_summary(),
            'environment_contract': {
                'version': str(self.metadata.get('environment_contract_version', 'v2') or 'v2'),
                'supports_clone': True,
                'supports_replay': True,
                'supports_diff_replication': True,
                'supports_concurrent_snapshots': True,
            },
            'log_policy': dict(self.metadata.get('scene_command_log_policy', {
                'retention_model': 'bounded_tail_plus_history',
                'intended_use': 'diagnostic_log_and_replay',
                'supports_replay': True,
                'supports_clone': True,
                'supports_diff_replication': True,
                'supports_concurrent_snapshots': True,
            }) or {}),
            'runtime_model_summary': dict(self.metadata.get('runtime_model_summary', {}) or {}),
            'execution_summary': dict(self.metadata.get('execution_summary', {}) or {}),
            'source_model_summary': dict(self.metadata.get('source_model_summary', {}) or {}),
            'canonical_model_summary': self.metadata.get('canonical_model_summary'),
            'obstacles': _normalize_scene_object_sequence(self.obstacles, validation_backend=self.collision_backend),
            'attached_objects': _normalize_scene_object_sequence(self.attached_objects, validation_backend=self.collision_backend),
            'supported_scene_shapes': list(self.geometry_authority.supported_scene_shapes),
            'backend_metadata': {
                key: value
                for key, value in dict(self.metadata).items()
                if key in {
                    'requested_collision_backend',
                    'resolved_collision_backend',
                    'fallback_backend',
                    'backend_capability_status',
                    'backend_capability_reason',
                    'backend_capability_error_code',
                    'experimental_backend_requested',
                    'declared_backend_family',
                }
            },
            **validation_surface,
        }
        return summary
