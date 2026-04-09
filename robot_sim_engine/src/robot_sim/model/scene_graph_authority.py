from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.core.collision.scene import PlanningScene


@dataclass(frozen=True)
class SceneFrame:
    frame_id: str
    parent_frame: str
    kind: str

    def summary(self) -> dict[str, str]:
        return {'frame_id': str(self.frame_id), 'parent_frame': str(self.parent_frame), 'kind': str(self.kind)}


@dataclass(frozen=True)
class GeometryRegistry:
    provider: str
    registered_geometry_ids: tuple[str, ...] = ()
    declared_shape_kinds: tuple[str, ...] = ()

    def summary(self) -> dict[str, object]:
        return {
            'provider': str(self.provider),
            'registered_geometry_ids': [str(v) for v in self.registered_geometry_ids],
            'declared_shape_kinds': [str(v) for v in self.declared_shape_kinds],
        }


@dataclass(frozen=True)
class QueryContext:
    backend: str
    supported_query_kinds: tuple[str, ...] = ()
    collision_backend: str = 'aabb'

    def require_query_kind(self, query_kind: str) -> None:
        expected = str(query_kind or '').strip()
        if expected not in set(self.supported_query_kinds):
            raise ValueError(f'query context does not support query kind {query_kind!r}; supported={list(self.supported_query_kinds)!r}')

    def summary(self) -> dict[str, object]:
        return {
            'backend': str(self.backend),
            'collision_backend': str(self.collision_backend),
            'supported_query_kinds': [str(v) for v in self.supported_query_kinds],
        }


@dataclass(frozen=True)
class SceneDiff:
    added_frames: tuple[str, ...] = ()
    removed_frames: tuple[str, ...] = ()
    added_edges: tuple[tuple[str, str], ...] = ()
    removed_edges: tuple[tuple[str, str], ...] = ()

    def summary(self) -> dict[str, object]:
        return {
            'added_frames': [str(v) for v in self.added_frames],
            'removed_frames': [str(v) for v in self.removed_frames],
            'added_edges': [[str(a), str(b)] for a, b in self.added_edges],
            'removed_edges': [[str(a), str(b)] for a, b in self.removed_edges],
        }


@dataclass(frozen=True)
class SceneGraphAuthority:
    """Stable scene-graph/query authority for the planning scene.

    The authority must survive routine scene edits without dropping the robot link graph that was
    injected by the runtime asset builder. Obstacles and attached objects are therefore merged onto
    the preserved robot/root frames rather than fully reconstructing the graph from obstacle state.
    """

    authority: str = 'planning_scene'
    provider: str = 'planning_scene_aabb_provider'
    frame_ids: tuple[str, ...] = ()
    attachment_edges: tuple[tuple[str, str], ...] = ()
    query_kinds: tuple[str, ...] = ('aabb_intersection', 'scene_summary', 'allowed_collision_matrix', 'scene_diff')
    backend: str = 'aabb'
    frames: tuple[SceneFrame, ...] = ()
    geometry_registry: GeometryRegistry = field(default_factory=lambda: GeometryRegistry(provider='planning_scene_aabb_provider'))
    query_context: QueryContext = field(default_factory=lambda: QueryContext(backend='planning_scene_aabb_provider', supported_query_kinds=('scene_summary', 'aabb_intersection', 'allowed_collision_matrix', 'scene_diff')))
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def capability_badges(self) -> tuple[str, ...]:
        return (
            f'authority:{self.authority}',
            f'provider:{self.provider}',
            f'backend:{self.backend}',
            *(f'query:{item}' for item in self.query_kinds),
        )

    def require_query_kind(self, query_kind: str) -> None:
        self.query_context.require_query_kind(query_kind)

    def diff_from(self, previous: 'SceneGraphAuthority | None') -> SceneDiff:
        if previous is None:
            return SceneDiff(added_frames=tuple(self.frame_ids), added_edges=tuple(self.attachment_edges))
        prev_frames = set(previous.frame_ids)
        now_frames = set(self.frame_ids)
        prev_edges = set(previous.attachment_edges)
        now_edges = set(self.attachment_edges)
        return SceneDiff(
            added_frames=tuple(sorted(now_frames - prev_frames)),
            removed_frames=tuple(sorted(prev_frames - now_frames)),
            added_edges=tuple(sorted(now_edges - prev_edges)),
            removed_edges=tuple(sorted(prev_edges - now_edges)),
        )

    def summary(self) -> dict[str, object]:
        return {
            'authority': str(self.authority),
            'provider': str(self.provider),
            'backend': str(self.backend),
            'frame_ids': [str(item) for item in self.frame_ids],
            'attachment_edges': [[str(a), str(b)] for a, b in self.attachment_edges],
            'query_kinds': [str(item) for item in self.query_kinds],
            'capability_badges': list(self.capability_badges),
            'frames': [frame.summary() for frame in self.frames],
            'geometry_registry': self.geometry_registry.summary(),
            'query_context': self.query_context.summary(),
            'metadata': dict(self.metadata or {}),
        }

    @staticmethod
    def _robot_graph_key_from_scene(scene: 'PlanningScene') -> str:
        metadata = dict(getattr(scene, 'metadata', {}) or {})
        explicit = str(metadata.get('robot_graph_key', '') or '').strip()
        if explicit:
            return explicit
        robot_name = str(metadata.get('robot_name', '') or '').strip()
        collision_link_names = tuple(str(item) for item in metadata.get('collision_link_names', ()) or ())
        if robot_name and collision_link_names:
            return f"{robot_name}:{'|'.join(collision_link_names)}"
        return ''

    @classmethod
    def _should_preserve_robot_graph(cls, scene: 'PlanningScene', previous: 'SceneGraphAuthority | None') -> bool:
        if previous is None:
            return False
        scene_robot_graph_key = cls._robot_graph_key_from_scene(scene)
        if not scene_robot_graph_key:
            return False
        previous_robot_graph_key = str(dict(previous.metadata or {}).get('robot_graph_key', '') or '').strip()
        return bool(previous_robot_graph_key) and previous_robot_graph_key == scene_robot_graph_key

    @classmethod
    def _preserved_robot_frames(cls, scene: 'PlanningScene', previous: 'SceneGraphAuthority | None') -> tuple[SceneFrame, ...]:
        if not cls._should_preserve_robot_graph(scene, previous):
            return (SceneFrame(frame_id='world', parent_frame='world', kind='root'),)
        preserved = [frame for frame in tuple(previous.frames or ()) if frame.kind in {'root', 'robot_link'}]
        if not any(frame.frame_id == 'world' for frame in preserved):
            preserved.insert(0, SceneFrame(frame_id='world', parent_frame='world', kind='root'))
        return tuple(preserved)

    @classmethod
    def _preserved_robot_edges(cls, scene: 'PlanningScene', previous: 'SceneGraphAuthority | None', robot_frame_ids: set[str]) -> tuple[tuple[str, str], ...]:
        if not cls._should_preserve_robot_graph(scene, previous):
            return ()
        return tuple(
            edge for edge in tuple(previous.attachment_edges or ())
            if str(edge[0]) in robot_frame_ids and str(edge[1]) in robot_frame_ids
        )

    @classmethod
    def from_scene(cls, scene: 'PlanningScene', previous: 'SceneGraphAuthority | None' = None) -> 'SceneGraphAuthority':
        backend = str(getattr(scene, 'collision_backend', 'aabb') or 'aabb')
        provider = f'planning_scene_{backend}_provider'
        query_kinds = ('scene_summary', f'{backend}_intersection', 'allowed_collision_matrix', 'scene_diff')

        preserved_frames = list(cls._preserved_robot_frames(scene, previous))
        frame_map = {frame.frame_id: frame for frame in preserved_frames}
        frame_ids = [frame.frame_id for frame in preserved_frames]
        robot_frame_ids = set(frame_ids)
        attachment_edges: list[tuple[str, str]] = list(cls._preserved_robot_edges(scene, previous, robot_frame_ids))
        registered_geometry_ids: list[str] = []
        declared_shape_kinds: list[str] = []

        def _ensure_frame(frame_id: str, parent_frame: str, kind: str) -> None:
            normalized_id = str(frame_id or '')
            if not normalized_id:
                return
            normalized_parent = str(parent_frame or 'world')
            if normalized_id not in frame_map:
                frame_map[normalized_id] = SceneFrame(frame_id=normalized_id, parent_frame=normalized_parent, kind=str(kind))
                frame_ids.append(normalized_id)

        _ensure_frame('world', 'world', 'root')

        for obj in tuple(getattr(scene, 'obstacles', ()) or ()):
            object_id = str(getattr(obj, 'object_id', 'object'))
            _ensure_frame(object_id, 'world', 'obstacle')
            attachment_edges.append(('world', object_id))
            registered_geometry_ids.append(object_id)
            geometry_type = str(dict(getattr(obj, 'metadata', {}) or {}).get('shape', 'box'))
            if geometry_type not in declared_shape_kinds:
                declared_shape_kinds.append(geometry_type)

        for obj in tuple(getattr(scene, 'attached_objects', ()) or ()):
            object_id = str(getattr(obj, 'object_id', 'object'))
            attach_link = str(dict(getattr(obj, 'metadata', {}) or {}).get('attach_link', 'robot'))
            _ensure_frame(attach_link, 'world', 'robot_link')
            _ensure_frame(object_id, attach_link, 'attached_object')
            attachment_edges.append((attach_link, object_id))
            registered_geometry_ids.append(object_id)
            geometry_type = str(dict(getattr(obj, 'metadata', {}) or {}).get('shape', 'box'))
            if geometry_type not in declared_shape_kinds:
                declared_shape_kinds.append(geometry_type)

        metadata = {
            'scene_fidelity': str(getattr(scene, 'scene_fidelity', 'generated') or 'generated'),
            'geometry_contract': str(getattr(getattr(scene, 'geometry_authority', None), 'scene_geometry_contract', 'declared_and_resolved') or 'declared_and_resolved'),
            'robot_graph_key': cls._robot_graph_key_from_scene(scene),
        }
        if previous is not None:
            metadata.update(dict(previous.metadata or {}))
            metadata.update({
                'scene_fidelity': str(getattr(scene, 'scene_fidelity', 'generated') or 'generated'),
                'geometry_contract': str(getattr(getattr(scene, 'geometry_authority', None), 'scene_geometry_contract', 'declared_and_resolved') or 'declared_and_resolved'),
            })
        return cls(
            authority=str(getattr(scene, 'scene_authority', 'planning_scene') or 'planning_scene'),
            provider=provider,
            frame_ids=tuple(dict.fromkeys(frame_ids)),
            attachment_edges=tuple(dict.fromkeys((str(a), str(b)) for a, b in attachment_edges)),
            query_kinds=query_kinds,
            backend=backend,
            frames=tuple(frame_map[frame_id] for frame_id in dict.fromkeys(frame_ids)),
            geometry_registry=GeometryRegistry(
                provider=provider,
                registered_geometry_ids=tuple(dict.fromkeys(registered_geometry_ids)),
                declared_shape_kinds=tuple(declared_shape_kinds),
            ),
            query_context=QueryContext(backend=provider, supported_query_kinds=query_kinds, collision_backend=backend),
            metadata=metadata,
        )
