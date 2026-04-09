from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

import numpy as np

from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene, SceneObject
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.model.scene_geometry_authority import SceneGeometryAuthority
from robot_sim.model.scene_graph_authority import SceneGraphAuthority
from robot_sim.application.services.scene_authority_support import (
    SUPPORTED_SCENE_SHAPES,
    coerce_int,
    normalize_collision_pairs,
    normalize_shape_size,
    normalize_vector,
)

_COLLISION_BACKEND_REGISTRY = default_collision_backend_registry()


def _declared_geometry_payload(*, shape: str, center: np.ndarray, size: np.ndarray) -> dict[str, object]:
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


def _resolved_geometry_payload(geometry: AABB) -> dict[str, object]:
    return {
        'kind': 'aabb',
        'minimum': [float(value) for value in geometry.minimum.tolist()],
        'maximum': [float(value) for value in geometry.maximum.tolist()],
    }


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
            summary = dict(scene_summary or {})
            normalized_backend, normalized_metadata = _COLLISION_BACKEND_REGISTRY.normalize_backend(
                str(summary.get('collision_backend', 'aabb') or 'aabb'),
                metadata={
                    'scene_authority': str(authority),
                    'edit_surface': str(edit_surface),
                    'scene_fidelity': str(summary.get('scene_fidelity', summary.get('geometry_source', 'generated')) or 'generated'),
                    'stable_surface_version': str(summary.get('stable_surface_version', 'v2') or 'v2'),
                },
            )
            acm = AllowedCollisionMatrix()
            for a, b in normalize_collision_pairs(summary.get('allowed_collision_pairs', ())):
                acm = acm.allow(a, b)
            scene = PlanningScene(
                revision=coerce_int(summary.get('revision', 0)),
                collision_backend=normalized_backend,
                geometry_source=str(summary.get('geometry_source', 'generated') or 'generated'),
                allowed_collision_matrix=acm,
                metadata=normalized_metadata,
            )
            geometry_authority = SceneGeometryAuthority.from_summary(
                summary,
                authority=str((summary.get('geometry_authority') or {}).get('authority', authority) if isinstance(summary.get('geometry_authority'), Mapping) else authority),
                authority_kind=str((summary.get('geometry_authority') or {}).get('authority_kind', 'planning_scene') if isinstance(summary.get('geometry_authority'), Mapping) else 'planning_scene'),
                declared_geometry_source=str(summary.get('declared_geometry_source', summary.get('geometry_source', 'generated')) or summary.get('geometry_source', 'generated')),
                resolved_geometry_source=str(summary.get('resolved_geometry_source', f"{summary.get('collision_backend', 'aabb')}_planning_scene") or f"{summary.get('collision_backend', 'aabb')}_planning_scene"),
                supported_scene_shapes=tuple(sorted(SUPPORTED_SCENE_SHAPES)),
                collision_backend=normalized_backend,
                scene_fidelity=str(summary.get('scene_fidelity', summary.get('geometry_source', 'generated')) or 'generated'),
            )
            seeded_scene = scene.with_geometry_authority(geometry_authority)
            return seeded_scene.with_scene_graph_authority(SceneGraphAuthority.from_scene(seeded_scene, previous=seeded_scene.scene_graph_authority))
        metadata_updates = {
            'scene_authority': str(authority),
            'edit_surface': str(edit_surface),
            'stable_surface_version': str(scene.metadata.get('stable_surface_version', 'v2') or 'v2'),
            'geometry_authority_scope': str(scene.metadata.get('geometry_authority_scope', authority) or authority),
        }
        if 'scene_fidelity' not in scene.metadata:
            metadata_updates['scene_fidelity'] = str(scene.geometry_source or 'generated')
        updated_scene = scene.with_metadata_patch(**metadata_updates)
        updated_scene = updated_scene.with_geometry_authority(SceneGeometryAuthority.from_scene(updated_scene))
        return updated_scene.with_scene_graph_authority(SceneGraphAuthority.from_scene(updated_scene, previous=updated_scene.scene_graph_authority))

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
        half = size * 0.5
        geometry = AABB(center - half, center + half)
        metadata = {
            'source': str(source),
            'shape': str(edit.shape),
            'size': [float(value) for value in size.tolist()],
            'editor': 'stable_scene_editor',
            'declared_geometry': _declared_geometry_payload(shape=edit.shape, center=center, size=size),
            'resolved_geometry': _resolved_geometry_payload(geometry),
            **dict(edit.metadata),
        }
        scene.geometry_authority.require_declared_and_resolved()
        scene.geometry_authority.require_supported_shape(edit.shape)
        if edit.attached:
            metadata['attach_link'] = str(edit.attach_link)
            updated_scene = self._upsert_attached_object(scene, edit.object_id, geometry, metadata=metadata, replace_existing=edit.replace_existing)
        else:
            obstacle_id = edit.object_id if edit.replace_existing else self.next_object_id(scene, edit.object_id)
            updated_scene = scene.upsert_obstacle(obstacle_id, geometry, metadata=metadata)
        updated_scene = self.apply_allowed_collision_pairs(
            updated_scene,
            edit.allowed_collision_pairs,
            clear_existing=edit.clear_allowed_collision_pairs,
        )
        last_edit_kind = 'attached_object' if edit.attached else 'obstacle'
        updated_scene = updated_scene.with_metadata_patch(
            last_edit_source=str(source),
            last_edit_kind=last_edit_kind,
        )
        refreshed = SceneGeometryAuthority.from_scene(updated_scene)
        authority = SceneGeometryAuthority(
            authority=refreshed.authority,
            authority_kind=refreshed.authority_kind,
            scene_geometry_contract='declared_and_resolved',
            declared_geometry_source='stable_scene_editor',
            resolved_geometry_source=f'{updated_scene.collision_backend}_planning_scene',
            supported_scene_shapes=tuple(sorted(SUPPORTED_SCENE_SHAPES)),
            records=refreshed.records,
            metadata=dict(refreshed.metadata),
        )
        updated_scene = updated_scene.with_geometry_authority(authority)
        return updated_scene.with_scene_graph_authority(SceneGraphAuthority.from_scene(updated_scene, previous=updated_scene.scene_graph_authority))

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
        geometry: AABB,
        *,
        metadata: dict[str, object],
        replace_existing: bool,
    ) -> PlanningScene:
        normalized_id = str(object_id or 'attached').strip() or 'attached'
        attached_objects = tuple(getattr(scene, 'attached_objects', ()) or ())
        existing_ids = {obj.object_id for obj in attached_objects}
        if not replace_existing and normalized_id in existing_ids:
            normalized_id = SceneAuthorityService.next_object_id(scene, normalized_id)
        replacement = SceneObject(object_id=normalized_id, geometry=geometry, metadata=dict(metadata))
        if normalized_id not in existing_ids:
            return scene._spawn(attached_objects=attached_objects + (replacement,), revision=scene.revision + 1)
        updated = tuple(replacement if obj.object_id == normalized_id else obj for obj in attached_objects)
        if updated == attached_objects:
            return scene
        return scene._spawn(attached_objects=updated, revision=scene.revision + 1)


