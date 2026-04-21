from __future__ import annotations

from robot_sim.core.collision.scene import PlanningScene
from robot_sim.domain.enums import CollisionLevel
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_geometry_model import RobotGeometryModel
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.scene_geometry_authority import SceneGeometryAuthority
from robot_sim.model.scene_graph_authority import GeometryRegistry, QueryContext, SceneFrame, SceneGraphAuthority


def build_planning_scene(
    *,
    backend_registry,
    experimental_collision_backends_enabled: bool,
    spec: RobotSpec,
    geometry_model: RobotGeometryModel,
    robot_geometry: RobotGeometry | None,
    collision_geometry: RobotGeometry | None,
) -> PlanningScene:
    requested_backend = requested_backend_for_geometry(robot_geometry=robot_geometry, collision_geometry=collision_geometry)
    runtime_model = spec.runtime_model
    articulated_model = spec.articulated_model
    execution_summary = spec.execution_summary
    scene_fidelity = resolve_scene_fidelity(spec, robot_geometry=robot_geometry, collision_geometry=collision_geometry)
    geometry_source = resolve_geometry_source(spec, robot_geometry=robot_geometry, collision_geometry=collision_geometry)
    metadata = {
        'edit_surface': 'stable_scene_editor',
        'stable_surface_version': 'v3',
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
        'runtime_semantic_family': str(articulated_model.semantic_family or runtime_model.semantic_family),
        'runtime_source_surface': str(runtime_model.source_surface),
        'runtime_source_format': str(runtime_model.source_format),
        'runtime_fidelity': str(runtime_model.fidelity),
        'geometry_available': bool(robot_geometry is not None),
        'collision_geometry_available': bool(collision_geometry is not None),
        'scene_fidelity': scene_fidelity,
        'robot_geometry_fidelity': '' if robot_geometry is None else str(getattr(robot_geometry, 'fidelity', '') or ''),
        'collision_geometry_fidelity': '' if collision_geometry is None else str(getattr(collision_geometry, 'fidelity', '') or ''),
        'collision_link_names': list(runtime_model.link_names[:-1]) if runtime_model.link_names else [],
        'collision_link_radii': link_radii(spec, collision_geometry=collision_geometry, robot_geometry=robot_geometry),
    }
    resolved_backend, metadata = backend_registry.normalize_backend(
        requested_backend,
        experimental_enabled=experimental_collision_backends_enabled,
        metadata=metadata,
    )
    collision_level = CollisionLevel.CAPSULE if resolved_backend == 'capsule' else CollisionLevel.AABB
    graph_seed = runtime_scene_graph_seed(spec, runtime_model=runtime_model, articulated_model=articulated_model)
    runtime_link_names = tuple(graph_seed['frame_ids']) or tuple(runtime_model.link_names) or tuple(f'link_{index}' for index in range(runtime_model.dof + 1))
    runtime_frames = [SceneFrame(frame_id='world', parent_frame='world', kind='root')]
    for frame_id, parent_frame in graph_seed['frames']:
        if frame_id == 'world':
            continue
        runtime_frames.append(SceneFrame(frame_id=frame_id, parent_frame=parent_frame, kind='robot_link'))
    runtime_edges = tuple((parent, child) for parent, child in graph_seed['edges'] if parent != child)
    metadata['robot_graph_key'] = str(graph_seed['robot_graph_key'])
    metadata['graph_seed'] = str(graph_seed['graph_seed'])
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
            'scene_fidelity': scene_fidelity,
            'graph_seed': str(graph_seed['graph_seed']),
            'robot_graph_key': str(metadata.get('robot_graph_key', '') or ''),
        },
    )
    scene = PlanningScene(
        collision_level=collision_level,
        geometry_source=geometry_source,
        collision_backend=resolved_backend,
        metadata=metadata,
        scene_graph_authority=scene_graph_authority,
    )
    refreshed = SceneGeometryAuthority.from_scene(scene)
    authority = SceneGeometryAuthority(
        authority='robot_runtime_asset_service',
        authority_kind='runtime_robot_scene',
        scene_geometry_contract='declaration_validation_render',
        declaration_geometry_source=geometry_source,
        validation_geometry_source='planning_scene_runtime_projection',
        render_geometry_source=geometry_source,
        supported_scene_shapes=('box', 'cylinder', 'sphere'),
        records=refreshed.records,
        metadata=dict(refreshed.metadata),
    )
    return scene.with_geometry_authority(authority)


def runtime_scene_graph_seed(spec: RobotSpec, *, runtime_model, articulated_model) -> dict[str, object]:
    """Build the robot scene-graph seed used by the planning-scene authority."""
    source_summary = dict(spec.source_model_summary or {})
    runtime_contract = dict(source_summary.get('runtime_fidelity_contract', {}) or {})
    articulated_layer = dict(runtime_contract.get('articulated_graph_layer', {}) or {})

    graph_edges = [tuple(item) for item in articulated_layer.get('graph_edge_pairs', ()) or () if isinstance(item, (list, tuple)) and len(item) == 2]
    graph_link_names = tuple(str(item) for item in articulated_layer.get('graph_link_names', ()) or () if str(item or '').strip())
    root_link = str(articulated_layer.get('root_link', getattr(articulated_model, 'root_link', '')) or getattr(articulated_model, 'root_link', ''))
    graph_seed = 'imported_articulated_graph'

    if not graph_edges:
        metadata_edges = [tuple(item) for item in getattr(articulated_model, 'metadata', {}).get('graph_edge_pairs', ()) or () if isinstance(item, (list, tuple)) and len(item) == 2]
        if metadata_edges:
            graph_edges = metadata_edges
            graph_link_names = tuple(str(item) for item in getattr(articulated_model, 'link_names', ()) or ())
            root_link = str(getattr(articulated_model, 'root_link', root_link) or root_link)
            graph_seed = 'articulated_model_metadata'

    if not graph_edges:
        articulated_edges = tuple(getattr(articulated_model, 'edge_pairs', ()) or ())
        if articulated_edges:
            graph_edges = [(str(parent), str(child)) for parent, child in articulated_edges]
            graph_link_names = tuple(str(item) for item in getattr(articulated_model, 'link_names', ()) or ())
            root_link = str(getattr(articulated_model, 'root_link', root_link) or root_link)
            graph_seed = 'articulated_model_edges'

    if not graph_edges:
        runtime_link_names = tuple(runtime_model.link_names) or tuple(f'link_{index}' for index in range(runtime_model.dof + 1))
        graph_link_names = runtime_link_names
        root_link = str(runtime_link_names[0]) if runtime_link_names else 'world'
        graph_edges = [(runtime_link_names[index - 1], runtime_link_names[index]) for index in range(1, len(runtime_link_names))]
        graph_seed = 'runtime_link_chain'

    ordered_frame_ids: list[str] = []
    if root_link:
        ordered_frame_ids.append(str(root_link))
    for link_name in graph_link_names:
        if link_name not in ordered_frame_ids:
            ordered_frame_ids.append(str(link_name))
    for parent, child in graph_edges:
        if parent not in ordered_frame_ids:
            ordered_frame_ids.append(str(parent))
        if child not in ordered_frame_ids:
            ordered_frame_ids.append(str(child))

    parent_map: dict[str, str] = {}
    for parent, child in graph_edges:
        parent_map.setdefault(str(child), str(parent))
    frames: list[tuple[str, str]] = []
    for frame_id in ordered_frame_ids:
        if frame_id == 'world':
            continue
        frames.append((str(frame_id), str(parent_map.get(frame_id, 'world' if frame_id != root_link else 'world'))))

    graph_key_parts = [spec.name, *ordered_frame_ids, *(f'{parent}>{child}' for parent, child in graph_edges)]
    return {
        'frame_ids': tuple(dict.fromkeys(str(item) for item in ordered_frame_ids if str(item or '').strip())),
        'frames': tuple((str(frame_id), str(parent_frame)) for frame_id, parent_frame in frames),
        'edges': tuple((str(parent), str(child)) for parent, child in graph_edges),
        'robot_graph_key': f"{spec.name}:{'|'.join(graph_key_parts[1:])}" if len(graph_key_parts) > 1 else str(spec.name),
        'graph_seed': str(graph_seed),
    }


def resolve_scene_fidelity(
    spec: RobotSpec,
    *,
    robot_geometry: RobotGeometry | None,
    collision_geometry: RobotGeometry | None,
) -> str:
    for geometry in (collision_geometry, robot_geometry):
        if geometry is None:
            continue
        fidelity = str(getattr(geometry, 'fidelity', '') or '').strip()
        if fidelity:
            return fidelity
    return str(spec.metadata.get('import_fidelity', spec.model_source or spec.kinematic_source or 'generated_proxy') or 'generated_proxy')


def requested_backend_for_geometry(*, robot_geometry: RobotGeometry | None, collision_geometry: RobotGeometry | None) -> str:
    for geometry in (collision_geometry, robot_geometry):
        if geometry is None:
            continue
        hint = str(getattr(geometry, 'collision_backend_hint', '') or '').strip().lower()
        if hint:
            return hint
    return 'aabb'


def resolve_geometry_source(
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


def link_radii(
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
