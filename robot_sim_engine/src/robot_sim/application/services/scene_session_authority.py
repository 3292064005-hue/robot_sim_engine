from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from robot_sim.core.collision.scene import PlanningScene


@dataclass(frozen=True)
class SceneSessionResolution:
    """Resolved planning-scene truth for one application/session workflow call."""

    scene: PlanningScene | None
    source: str
    truth_layer: str
    materialization_source: str
    materialization_revision_key: str

    def summary_patch(self) -> dict[str, object]:
        """Return stable metadata fields written to request/session/export summaries.

        Args:
            None.

        Returns:
            dict[str, object]: Scene-source and materialization metadata.

        Raises:
            None: Pure serialization of the already-resolved scene boundary.

        Boundary behavior:
            The revision key is both exported diagnostic evidence and the partition key supplied
            to runtime materialization caches when caller/session scene truth is present.
        """
        return {
            'planning_scene_source': self.source,
            'scene_truth_layer': self.truth_layer,
            'materialization_source': self.materialization_source,
            'scene_materialization_revision_key': self.materialization_revision_key,
        }


class SceneSessionAuthority:
    """Resolve session planning-scene truth independently from runtime materialization.

    The authority is intentionally small: it does not mutate obstacles or rebuild geometry. Its
    only responsibility is deciding whether caller/session scene truth or runtime-default baseline
    materialization crosses the application boundary, and recording that decision consistently for
    plan, validate, and export-session paths.
    """

    @staticmethod
    def _require_scene(value: object, *, field_name: str) -> PlanningScene:
        if not isinstance(value, PlanningScene):
            raise ValueError(f'{field_name} must be a PlanningScene instance or None')
        return value

    @classmethod
    def resolve(
        cls,
        *,
        planning_scene: PlanningScene | None,
        fallback_scene: PlanningScene | None,
    ) -> SceneSessionResolution:
        """Resolve scene truth and materialization metadata for one workflow boundary.

        Args:
            planning_scene: Explicit caller/session scene truth.
            fallback_scene: Runtime-default baseline scene produced by asset materialization.

        Returns:
            SceneSessionResolution: Resolved scene plus source/truth/materialization metadata.

        Raises:
            ValueError: If either non-empty scene argument is not a ``PlanningScene`` instance.

        Boundary behavior:
            Explicit caller scenes always win. Fallback scenes remain supported only for legacy
            requests that do not provide a scene payload.
        """
        if planning_scene is not None:
            scene = cls._require_scene(planning_scene, field_name='planning_scene')
            return SceneSessionResolution(
                scene=scene,
                source='caller_scene',
                truth_layer='session_planning_scene',
                materialization_source='caller_supplied_scene',
                materialization_revision_key=cls.revision_key(scene, source='caller_scene'),
            )
        if fallback_scene is not None:
            scene = cls._require_scene(fallback_scene, field_name='fallback planning scene')
            return SceneSessionResolution(
                scene=scene,
                source='runtime_default_scene',
                truth_layer='baseline_spec_scene',
                materialization_source='runtime_asset_service',
                materialization_revision_key=cls.revision_key(scene, source='runtime_default_scene'),
            )
        return SceneSessionResolution(
            scene=None,
            source='none',
            truth_layer='none',
            materialization_source='none',
            materialization_revision_key='none:rev:0',
        )

    @staticmethod
    def _scene_contract_payload(scene: PlanningScene) -> dict[str, object]:
        """Return the stable scene content used for materialization cache partitioning.

        Args:
            scene: Resolved planning scene to fingerprint.

        Returns:
            dict[str, object]: Replay-relevant scene content, including object geometry, ACM
            pairs, backend/fidelity settings, and mutation revision.

        Raises:
            None: Object summaries are already normalized by ``PlanningScene``.

        Boundary behavior:
            The payload intentionally includes content, not just ``scene.revision``. Two caller
            scenes with the same revision but different obstacles, attached objects, or allowed
            collision pairs must receive different materialization revision keys.
        """
        return {
            'revision': int(getattr(scene, 'revision', 0) or 0),
            'collision_backend': str(getattr(scene, 'collision_backend', '') or ''),
            'geometry_source': str(getattr(scene, 'geometry_source', '') or ''),
            'collision_level': getattr(getattr(scene, 'collision_level', ''), 'value', str(getattr(scene, 'collision_level', ''))),
            'self_collision_padding': float(getattr(scene, 'self_collision_padding', 0.0) or 0.0),
            'environment_collision_padding': float(getattr(scene, 'environment_collision_padding', 0.0) or 0.0),
            'ignore_adjacent_self_collisions': bool(getattr(scene, 'ignore_adjacent_self_collisions', False)),
            'clearance_policy': str(getattr(scene, 'clearance_policy', '') or ''),
            'obstacle_ids': [str(item) for item in getattr(scene, 'obstacle_ids', ()) or ()],
            'attached_object_ids': [str(item) for item in getattr(scene, 'attached_object_ids', ()) or ()],
            'allowed_collision_pairs': [list(pair) for pair in getattr(scene, 'allowed_collision_pairs', ()) or ()],
            'obstacles': [obj.summary(validation_backend=str(getattr(scene, 'collision_backend', '') or 'aabb')) for obj in getattr(scene, 'obstacles', ()) or ()],
            'attached_objects': [obj.summary(validation_backend=str(getattr(scene, 'collision_backend', '') or 'aabb')) for obj in getattr(scene, 'attached_objects', ()) or ()],
        }

    @classmethod
    def revision_key(cls, scene: PlanningScene | None, *, source: str) -> str:
        """Build a content-addressed materialization revision key for a scene boundary.

        Args:
            scene: Resolved scene, if available.
            source: Source label such as ``caller_scene`` or ``runtime_default_scene``.

        Returns:
            str: Deterministic key containing source, mutation revision, backend, geometry
            source, and a hash of replay-relevant scene content.

        Raises:
            None: Missing scene fields are normalized before hashing.

        Boundary behavior:
            ``scene.revision`` alone is not a unique scene identity across independently cloned or
            caller-supplied scenes. The content hash prevents runtime materialization/cache
            diagnostics from being reused across two scenes that share the same revision number but
            carry different obstacles, attached objects, or allowed collision pairs.
        """
        if scene is None:
            return f'{source}:rev:0:hash:none'
        backend = str(getattr(scene, 'collision_backend', '') or '')
        geometry_source = str(getattr(scene, 'geometry_source', '') or '')
        revision = int(getattr(scene, 'revision', 0) or 0)
        payload = cls._scene_contract_payload(scene)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:24]
        return f'{source}:rev:{revision}:backend:{backend}:geometry:{geometry_source}:hash:{digest}'
