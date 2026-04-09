from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from robot_sim.core.collision.scene import PlanningScene
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import CollisionLevel
from robot_sim.model.robot_geometry import GeometryPrimitive, LinkGeometry, RobotGeometry
from robot_sim.model.robot_geometry_model import RobotGeometryModel
from robot_sim.model.scene_graph_authority import GeometryRegistry, QueryContext, SceneFrame, SceneGraphAuthority
from robot_sim.model.scene_geometry_authority import SceneGeometryAuthority
from robot_sim.model.robot_spec import RobotSpec




def serialize_robot_geometry(geometry: RobotGeometry | None) -> dict[str, object] | None:
    """Serialize a runtime robot-geometry bundle into YAML-safe primitives."""
    if geometry is None:
        return None
    return {
        'source': str(geometry.source),
        'fidelity': str(geometry.fidelity),
        'collision_backend_hint': str(geometry.collision_backend_hint),
        'metadata': dict(geometry.metadata),
        'links': [
            {
                'name': str(link.name),
                'radius': float(link.radius),
                'points_local': None if link.points_local is None else np.asarray(link.points_local, dtype=float).tolist(),
                'visual_primitives': [
                    {
                        'kind': str(primitive.kind),
                        'params': dict(primitive.params),
                        'local_transform': None if primitive.local_transform is None else np.asarray(primitive.local_transform, dtype=float).tolist(),
                    }
                    for primitive in link.visual_primitives
                ],
                'collision_primitives': [
                    {
                        'kind': str(primitive.kind),
                        'params': dict(primitive.params),
                        'local_transform': None if primitive.local_transform is None else np.asarray(primitive.local_transform, dtype=float).tolist(),
                    }
                    for primitive in link.collision_primitives
                ],
                'metadata': dict(link.metadata),
            }
            for link in geometry.links
        ],
    }


def deserialize_robot_geometry(payload: dict[str, object] | None) -> RobotGeometry | None:
    """Deserialize YAML-safe geometry payloads back into ``RobotGeometry``."""
    if not payload:
        return None
    links = []
    for link in payload.get('links', ()) or ():
        visual_primitives = []
        for primitive in link.get('visual_primitives', ()) or ():
            visual_primitives.append(
                GeometryPrimitive(
                    kind=str(primitive.get('kind', 'unknown')),
                    params=dict(primitive.get('params') or {}),
                    local_transform=None if primitive.get('local_transform') is None else np.asarray(primitive.get('local_transform'), dtype=float),
                )
            )
        collision_primitives = []
        for primitive in link.get('collision_primitives', ()) or ():
            collision_primitives.append(
                GeometryPrimitive(
                    kind=str(primitive.get('kind', 'unknown')),
                    params=dict(primitive.get('params') or {}),
                    local_transform=None if primitive.get('local_transform') is None else np.asarray(primitive.get('local_transform'), dtype=float),
                )
            )
        links.append(
            LinkGeometry(
                name=str(link.get('name', 'link')),
                radius=float(link.get('radius', 0.03)),
                points_local=None if link.get('points_local') is None else np.asarray(link.get('points_local'), dtype=float),
                visual_primitives=tuple(visual_primitives),
                collision_primitives=tuple(collision_primitives),
                metadata=dict(link.get('metadata') or {}),
            )
        )
    return RobotGeometry(
        links=tuple(links),
        source=str(payload.get('source', 'generated')),
        fidelity=str(payload.get('fidelity', 'approximate')),
        collision_backend_hint=str(payload.get('collision_backend_hint', 'aabb')),
        metadata=dict(payload.get('metadata') or {}),
    )

@dataclass(frozen=True)
class RobotRuntimeAssets:
    """Runtime projection assets derived from a robot specification.

    Attributes:
        robot_geometry: Geometry bundle projected into the scene widget and screenshots.
        collision_geometry: Geometry bundle used to declare collision/backend scene metadata.
        planning_scene: Canonical runtime planning-scene authority for validation/export.
        scene_summary: Stable summary derived from ``planning_scene``.
    """

    robot_geometry: RobotGeometry | None
    collision_geometry: RobotGeometry | None
    planning_scene: PlanningScene
    scene_summary: dict[str, object]


class RobotRuntimeAssetService:
    """Build stable runtime geometry and planning-scene assets from a robot spec.

    The V7 runtime now resolves kinematics through ``RobotSpec.runtime_model``. This
    service keeps the presentation/session/render layers honest by deriving one canonical
    runtime scene/geometry view from the loaded spec plus any importer-provided geometry bundle.
    """

    def __init__(self, *, experimental_collision_backends_enabled: bool = False) -> None:
        self._experimental_collision_backends_enabled = bool(experimental_collision_backends_enabled)
        self._backend_registry = default_collision_backend_registry()

    def build_assets(
        self,
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None = None,
        collision_geometry: RobotGeometry | None = None,
    ) -> RobotRuntimeAssets:
        """Derive runtime geometry and planning-scene state for one robot specification.

        Args:
            spec: Canonical runtime robot specification.
            robot_geometry: Optional importer-provided visual geometry bundle.
            collision_geometry: Optional importer-provided collision geometry bundle.

        Returns:
            RobotRuntimeAssets: Stable runtime assets bound to ``spec``.

        Raises:
            ValueError: Propagates invalid robot-spec invariants.

        Boundary behavior:
            When importer geometry is unavailable, the service deterministically falls back
            to generated capsule geometry so the scene/render/session chain still has one
            canonical runtime asset surface.
        """
        visual_geometry = self._resolve_robot_geometry(spec, explicit_geometry=robot_geometry)
        resolved_collision_geometry = self._resolve_collision_geometry(
            spec,
            robot_geometry=visual_geometry,
            explicit_geometry=collision_geometry,
        )
        planning_scene = self._build_planning_scene(
            spec,
            robot_geometry=visual_geometry,
            collision_geometry=resolved_collision_geometry,
        )
        return RobotRuntimeAssets(
            robot_geometry=visual_geometry,
            collision_geometry=resolved_collision_geometry,
            planning_scene=planning_scene,
            scene_summary=planning_scene.summary(),
        )

    def _resolve_robot_geometry(
        self,
        spec: RobotSpec,
        *,
        explicit_geometry: RobotGeometry | None,
    ) -> RobotGeometry | None:
        if explicit_geometry is not None:
            return explicit_geometry
        imported_package = spec.imported_package
        if imported_package is not None and imported_package.geometry_model is not None and imported_package.geometry_model.visual_geometry is not None:
            return imported_package.geometry_model.visual_geometry
        serialized = deserialize_robot_geometry(dict(spec.metadata.get('serialized_robot_geometry') or {}))
        if serialized is not None:
            return serialized
        fallback = RobotGeometry.simple_capsules(spec.dof)
        return replace(
            fallback,
            source=str(spec.model_source or spec.kinematic_source or fallback.source),
            fidelity=str(spec.metadata.get('import_fidelity', fallback.fidelity) or fallback.fidelity),
            metadata={
                **dict(fallback.metadata),
                'derived_from': 'robot_spec',
                'robot_name': spec.name,
                'geometry_available_from_source': bool(spec.geometry_available),
            },
        )

    def _resolve_collision_geometry(
        self,
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None,
        explicit_geometry: RobotGeometry | None,
    ) -> RobotGeometry | None:
        if explicit_geometry is not None:
            return explicit_geometry
        imported_package = spec.imported_package
        if imported_package is not None and imported_package.geometry_model is not None and imported_package.geometry_model.collision_geometry is not None:
            return imported_package.geometry_model.collision_geometry
        serialized = deserialize_robot_geometry(dict(spec.metadata.get('serialized_collision_geometry') or {}))
        if serialized is not None:
            return serialized
        if robot_geometry is not None:
            return replace(
                robot_geometry,
                metadata={
                    **dict(robot_geometry.metadata),
                    'collision_geometry_fallback': True,
                    'robot_name': spec.name,
                },
            )
        return None

    def _build_planning_scene(
        self,
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None,
        collision_geometry: RobotGeometry | None,
    ) -> PlanningScene:
        requested_backend = self._requested_backend(robot_geometry=robot_geometry, collision_geometry=collision_geometry)
        runtime_model = spec.runtime_model
        articulated_model = spec.articulated_model
        geometry_model = RobotGeometryModel(visual_geometry=robot_geometry, collision_geometry=collision_geometry)
        execution_summary = spec.execution_summary
        metadata = {
            'edit_surface': 'stable_scene_editor',
            'stable_surface_version': 'v2',
            'robot_name': spec.name,
            'robot_graph_key': '',
            'model_source': spec.model_source,
            'kinematic_source': spec.kinematic_source,
            'source_model_summary': dict(spec.source_model_summary or {}),
            'canonical_model_summary': None if spec.canonical_model is None else spec.canonical_model.summary(),
            'runtime_model_summary': runtime_model.summary(),
            'articulated_model_summary': articulated_model.summary(),
            'geometry_model_summary': geometry_model.summary(),
            'imported_package_summary': None if spec.imported_package is None else spec.imported_package.summary(),
            'imported_package_ref': 'spec.imported_package' if spec.imported_package is not None else '',
            'execution_summary': dict(execution_summary),
            'execution_adapter': str(execution_summary.get('execution_adapter', 'robot_spec_execution_rows') or 'robot_spec_execution_rows'),
            'execution_surface': str(execution_summary.get('execution_surface', 'robot_spec') or 'robot_spec'),
            'execution_row_count': int(execution_summary.get('execution_row_count', runtime_model.dof) or runtime_model.dof),
            'runtime_semantic_family': str(runtime_model.semantic_family),
            'runtime_source_surface': str(runtime_model.source_surface),
            'runtime_source_format': str(runtime_model.source_format),
            'runtime_fidelity': str(runtime_model.fidelity),
            'geometry_available': bool(robot_geometry is not None),
            'collision_geometry_available': bool(collision_geometry is not None),
            'scene_fidelity': self._scene_fidelity(spec, robot_geometry=robot_geometry, collision_geometry=collision_geometry),
            'robot_geometry_fidelity': '' if robot_geometry is None else str(getattr(robot_geometry, 'fidelity', '') or ''),
            'collision_geometry_fidelity': '' if collision_geometry is None else str(getattr(collision_geometry, 'fidelity', '') or ''),
            'collision_link_names': list(runtime_model.link_names[:-1]) if runtime_model.link_names else [],
            'collision_link_radii': self._link_radii(spec, collision_geometry=collision_geometry, robot_geometry=robot_geometry),
        }
        resolved_backend, metadata = self._backend_registry.normalize_backend(
            requested_backend,
            experimental_enabled=self._experimental_collision_backends_enabled,
            metadata=metadata,
        )
        collision_level = CollisionLevel.CAPSULE if resolved_backend == 'capsule' else CollisionLevel.AABB
        runtime_link_names = tuple(runtime_model.link_names) or tuple(f'link_{index}' for index in range(runtime_model.dof + 1))
        runtime_frames = [SceneFrame(frame_id='world', parent_frame='world', kind='root')]
        if runtime_link_names:
            root_frame = runtime_link_names[0]
            if root_frame != 'world':
                runtime_frames.append(SceneFrame(frame_id=root_frame, parent_frame='world', kind='robot_link'))
            for index in range(1, len(runtime_link_names)):
                runtime_frames.append(
                    SceneFrame(
                        frame_id=runtime_link_names[index],
                        parent_frame=runtime_link_names[index - 1],
                        kind='robot_link',
                    )
                )
        runtime_edges = tuple(
            (runtime_link_names[index - 1], runtime_link_names[index])
            for index in range(1, len(runtime_link_names))
        )
        metadata['robot_graph_key'] = f"{spec.name}:{'|'.join(runtime_link_names[:-1])}" if runtime_link_names else str(spec.name)
        provider = f'planning_scene_{resolved_backend}_provider'
        query_kinds = ('scene_summary', f'{resolved_backend}_intersection', 'allowed_collision_matrix', 'scene_diff')
        scene_graph_authority = SceneGraphAuthority(
            authority='robot_runtime_asset_service',
            provider=provider,
            frame_ids=tuple(dict.fromkeys(('world', *runtime_link_names))),
            attachment_edges=runtime_edges,
            query_kinds=query_kinds,
            backend=resolved_backend,
            frames=tuple(runtime_frames),
            geometry_registry=GeometryRegistry(provider=provider),
            query_context=QueryContext(backend=provider, supported_query_kinds=query_kinds, collision_backend=resolved_backend),
            metadata={
                'scene_fidelity': self._scene_fidelity(spec, robot_geometry=robot_geometry, collision_geometry=collision_geometry),
                'graph_seed': 'runtime_robot_links',
                'robot_graph_key': str(metadata.get('robot_graph_key', '') or ''),
            },
        )
        scene = PlanningScene(
            collision_level=collision_level,
            geometry_source=self._geometry_source(spec, robot_geometry=robot_geometry, collision_geometry=collision_geometry),
            collision_backend=resolved_backend,
            metadata=metadata,
            scene_graph_authority=scene_graph_authority,
        )
        refreshed = SceneGeometryAuthority.from_scene(scene)
        authority = SceneGeometryAuthority(
            authority='robot_runtime_asset_service',
            authority_kind='runtime_robot_scene',
            scene_geometry_contract='declared_and_resolved',
            declared_geometry_source=self._geometry_source(spec, robot_geometry=robot_geometry, collision_geometry=collision_geometry),
            resolved_geometry_source='planning_scene_runtime_projection',
            supported_scene_shapes=('box', 'cylinder', 'sphere'),
            records=refreshed.records,
            metadata=dict(refreshed.metadata),
        )
        return scene.with_geometry_authority(authority)


    @staticmethod
    def _scene_fidelity(
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None,
        collision_geometry: RobotGeometry | None,
    ) -> str:
        """Resolve the stable scene-fidelity label exported with runtime scene summaries.

        Args:
            spec: Canonical robot specification.
            robot_geometry: Visual runtime geometry bundle, if available.
            collision_geometry: Collision runtime geometry bundle, if available.

        Returns:
            str: Stable fidelity label describing the best geometry/collision fidelity that
                the runtime planning scene can currently claim.
        """
        for geometry in (collision_geometry, robot_geometry):
            if geometry is None:
                continue
            fidelity = str(getattr(geometry, 'fidelity', '') or '').strip()
            if fidelity:
                return fidelity
        return str(spec.metadata.get('import_fidelity', spec.model_source or spec.kinematic_source or 'generated_proxy') or 'generated_proxy')

    @staticmethod
    def _requested_backend(*, robot_geometry: RobotGeometry | None, collision_geometry: RobotGeometry | None) -> str:
        for geometry in (collision_geometry, robot_geometry):
            if geometry is None:
                continue
            hint = str(getattr(geometry, 'collision_backend_hint', '') or '').strip().lower()
            if hint:
                return hint
        return 'aabb'

    @staticmethod
    def _geometry_source(
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None,
        collision_geometry: RobotGeometry | None,
    ) -> str:
        for geometry in (collision_geometry, robot_geometry):
            if geometry is None:
                continue
            source = str(getattr(geometry, 'source', '') or '').strip()
            if source and source != 'generated':
                return source
        return str(spec.model_source or spec.kinematic_source or 'dh_config')

    @staticmethod
    def _link_radii(
        spec: RobotSpec,
        *,
        collision_geometry: RobotGeometry | None,
        robot_geometry: RobotGeometry | None,
    ) -> list[float]:
        geometry = collision_geometry or robot_geometry
        if geometry is not None and getattr(geometry, 'links', None):
            radii = [float(getattr(link, 'radius', 0.03) or 0.03) for link in geometry.links[:spec.dof]]
            if len(radii) == spec.dof:
                return radii
        return [0.03 for _ in range(spec.dof)]
