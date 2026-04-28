from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_geometry_serialization import serialize_robot_geometry
from robot_sim.model.robot_spec import RobotSpec

from .geometry_support import GeometryProjectionService
from .models import (
    KinematicRuntimeSurface,
    RobotRuntimeAssets,
    RuntimeAssetCacheStore,
    RuntimeAssetInvalidationEvent,
    RuntimeAssetInvalidationJournal,
)
from .planning_scene_support import build_planning_scene


@dataclass(frozen=True)
class KinematicRuntimeService:
    """Resolve runtime-model and articulated-model summaries for asset projection."""

    def describe(self, spec: RobotSpec) -> KinematicRuntimeSurface:
        return KinematicRuntimeSurface(
            runtime_model_summary=spec.runtime_model.summary(),
            articulated_model_summary=spec.articulated_model.summary(),
            execution_summary=dict(spec.execution_summary or {}),
        )


class RobotRuntimeAssetService:
    """Build stable runtime geometry and planning-scene assets from a robot spec."""

    def __init__(self, *, experimental_collision_backends_enabled: bool = False) -> None:
        self._experimental_collision_backends_enabled = bool(experimental_collision_backends_enabled)
        self._backend_registry = default_collision_backend_registry()
        self._kinematic_runtime_service = KinematicRuntimeService()
        self._geometry_projection_service = GeometryProjectionService()
        self._cache_store = RuntimeAssetCacheStore()
        self._runtime_context_signature = self._context_signature(
            profile_id='default',
            collision_backend_scope='experimental' if bool(experimental_collision_backends_enabled) else 'stable',
            experimental_collision_backends_enabled=bool(experimental_collision_backends_enabled),
        )
        self._invalidation_journal = RuntimeAssetInvalidationJournal()

    def build_assets(
        self,
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None = None,
        collision_geometry: RobotGeometry | None = None,
        scene_materialization_revision_key: str | None = None,
    ) -> RobotRuntimeAssets:
        """Derive runtime geometry and planning-scene materialization assets.

        Args:
            spec: Robot specification used to derive kinematics and baseline geometry.
            robot_geometry: Optional visual/runtime geometry override.
            collision_geometry: Optional collision-geometry override.
            scene_materialization_revision_key: Optional session scene materialization revision.
                When a caller/session scene is being planned, validated, or exported, this key is
                included in the runtime cache key so materialized diagnostics cannot be reused
                across incompatible scene revisions. Omit it for legacy baseline-only requests.

        Returns:
            RobotRuntimeAssets: Runtime geometry, baseline planning scene, and materialization
            summary tagged with the scene materialization cache partition.

        Raises:
            ValueError: Propagated from geometry projection or planning-scene construction.

        Boundary behavior:
            The cached assets still represent baseline runtime materialization. Session scene truth
            is resolved by ``SceneSessionAuthority`` at the application boundary; the revision key
            partitions materialization/cache diagnostics without silently replacing caller scenes.
        """
        normalized_scene_revision_key = str(scene_materialization_revision_key or 'baseline_spec_scene:rev:0')
        cache_key = self._cache_key(
            spec,
            robot_geometry=robot_geometry,
            collision_geometry=collision_geometry,
            scene_materialization_revision_key=normalized_scene_revision_key,
        )
        cached = self._cache_store.get(cache_key)
        if cached is not None:
            return cached.assets
        kinematic_surface = self._kinematic_runtime_service.describe(spec)
        geometry_projection = self._geometry_projection_service.project(
            spec,
            robot_geometry=robot_geometry,
            collision_geometry=collision_geometry,
        )
        planning_scene = build_planning_scene(
            backend_registry=self._backend_registry,
            experimental_collision_backends_enabled=self._experimental_collision_backends_enabled,
            spec=spec,
            geometry_model=geometry_projection.geometry_model,
            robot_geometry=geometry_projection.robot_geometry,
            collision_geometry=geometry_projection.collision_geometry,
        )
        assets = RobotRuntimeAssets(
            robot_geometry=geometry_projection.robot_geometry,
            collision_geometry=geometry_projection.collision_geometry,
            geometry_model=geometry_projection.geometry_model,
            planning_scene=planning_scene,
            scene_summary={
                **planning_scene.summary(),
                'runtime_model_summary': dict(kinematic_surface.runtime_model_summary),
                'articulated_model_summary': dict(kinematic_surface.articulated_model_summary),
                'execution_summary': dict(kinematic_surface.execution_summary),
                'scene_materialization_revision_key': normalized_scene_revision_key,
                'runtime_cache_key': cache_key,
            },
        )
        self._cache_store.put(cache_key, assets)
        return assets

    def bind_runtime_context(
        self,
        *,
        profile_id: str,
        collision_backend_scope: str,
        experimental_collision_backends_enabled: bool,
    ) -> None:
        """Bind the active runtime context and invalidate stale cache state when it changes."""
        signature = self._context_signature(
            profile_id=profile_id,
            collision_backend_scope=collision_backend_scope,
            experimental_collision_backends_enabled=experimental_collision_backends_enabled,
        )
        self._experimental_collision_backends_enabled = bool(experimental_collision_backends_enabled)
        if signature == self._runtime_context_signature:
            return
        removed_entries = self._cache_store.clear()
        self._runtime_context_signature = signature
        self._record_invalidation(reason='runtime_context_changed', spec_name=None, removed_entries=removed_entries)

    def invalidate(self, spec: RobotSpec | None = None, *, reason: str = 'manual') -> None:
        """Invalidate cached runtime assets globally or for one robot specification."""
        if spec is None:
            removed_entries = self._cache_store.clear()
            self._record_invalidation(reason=reason, spec_name=None, removed_entries=removed_entries)
            return
        removed_entries = self._cache_store.remove_for_spec(str(spec.name))
        self._record_invalidation(reason=reason, spec_name=str(spec.name), removed_entries=removed_entries)

    def cache_stats(self) -> dict[str, int]:
        """Return stable cache diagnostics used by tests and runtime summaries."""
        invalidation_count = self._invalidation_journal.count()
        return {
            'entries': self._cache_store.entry_count(),
            'invalidations': invalidation_count,
            'invalidation_events': invalidation_count,
        }

    def invalidation_log(self) -> tuple[RuntimeAssetInvalidationEvent, ...]:
        """Return immutable structured invalidation records for diagnostics/tests."""
        return self._invalidation_journal.snapshot()

    def _record_invalidation(self, *, reason: str, spec_name: str | None, removed_entries: int) -> None:
        self._invalidation_journal.record(
            reason=reason,
            spec_name=spec_name,
            removed_entries=removed_entries,
            context_signature=self._runtime_context_signature,
        )

    @staticmethod
    def _context_signature(*, profile_id: str, collision_backend_scope: str, experimental_collision_backends_enabled: bool) -> str:
        payload = {
            'profile_id': str(profile_id),
            'collision_backend_scope': str(collision_backend_scope),
            'experimental_collision_backends_enabled': bool(experimental_collision_backends_enabled),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()

    def _cache_key(
        self,
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None,
        collision_geometry: RobotGeometry | None,
        scene_materialization_revision_key: str,
    ) -> str:
        payload = {
            'spec_name': spec.name,
            'spec_display_name': spec.display_name,
            'dh_rows': [
                {
                    'a': float(row.a),
                    'alpha': float(row.alpha),
                    'd': float(row.d),
                    'theta_offset': float(row.theta_offset),
                    'joint_type': getattr(row.joint_type, 'value', str(row.joint_type)),
                    'q_min': float(row.q_min),
                    'q_max': float(row.q_max),
                }
                for row in spec.dh_rows
            ],
            'home_q': np.asarray(spec.home_q, dtype=float).tolist(),
            'model_source': str(spec.model_source or ''),
            'kinematic_source': str(spec.kinematic_source or ''),
            'execution_summary': dict(spec.execution_summary or {}),
            'source_model_summary': dict(spec.source_model_summary or {}),
            'robot_geometry_override': serialize_robot_geometry(robot_geometry),
            'collision_geometry_override': serialize_robot_geometry(collision_geometry),
            'scene_materialization_revision_key': str(scene_materialization_revision_key or 'baseline_spec_scene:rev:0'),
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()
        return f"{spec.name}:{digest}"
