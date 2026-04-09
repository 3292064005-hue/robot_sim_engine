from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Mapping

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.core.collision.scene import PlanningScene, SceneObject


def _resolved_geometry_from_object(obj: 'SceneObject', summary: Mapping[str, object] | None = None) -> dict[str, object]:
    payload = None if summary is None else summary.get('resolved_geometry')
    if isinstance(payload, Mapping):
        return dict(payload)
    geometry = getattr(obj, 'geometry', None)
    if geometry is None:
        return {}
    return {
        'kind': 'aabb',
        'minimum': [float(value) for value in geometry.minimum],
        'maximum': [float(value) for value in geometry.maximum],
    }


def _declared_geometry_from_object(summary: Mapping[str, object] | None, fallback: dict[str, object]) -> dict[str, object]:
    payload = None if summary is None else summary.get('declared_geometry')
    if isinstance(payload, Mapping):
        return dict(payload)
    return dict(fallback)


@dataclass(frozen=True)
class GeometryAuthorityRecord:
    """Stable declared/resolved geometry record projected from a planning-scene object."""

    object_id: str
    declared_geometry: dict[str, object]
    resolved_geometry: dict[str, object]
    authority: str = 'planning_scene'
    geometry_source: str = ''
    attached: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        return {
            'object_id': str(self.object_id),
            'authority': str(self.authority or 'planning_scene'),
            'geometry_source': str(self.geometry_source or ''),
            'attached': bool(self.attached),
            'declared_geometry': dict(self.declared_geometry or {}),
            'resolved_geometry': dict(self.resolved_geometry or {}),
            'metadata': dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class SceneGeometryAuthority:
    """Single scene-geometry authority contract shared by scene editing, validation, and export."""

    authority: str
    authority_kind: str = 'planning_scene'
    scene_geometry_contract: str = 'declared_and_resolved'
    declared_geometry_source: str = ''
    resolved_geometry_source: str = ''
    supported_scene_shapes: tuple[str, ...] = ()
    records: tuple[GeometryAuthorityRecord, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'authority', str(self.authority or 'planning_scene'))
        object.__setattr__(self, 'authority_kind', str(self.authority_kind or 'planning_scene'))
        object.__setattr__(self, 'scene_geometry_contract', str(self.scene_geometry_contract or 'declared_and_resolved'))
        object.__setattr__(self, 'declared_geometry_source', str(self.declared_geometry_source or ''))
        object.__setattr__(self, 'resolved_geometry_source', str(self.resolved_geometry_source or ''))
        object.__setattr__(self, 'supported_scene_shapes', tuple(str(item) for item in self.supported_scene_shapes))
        object.__setattr__(self, 'records', tuple(self.records))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))

    @property
    def capability_badges(self) -> list[str]:
        badges = [
            f'authority:{self.authority or "planning_scene"}',
            f'authority_kind:{self.authority_kind or "planning_scene"}',
            f'geometry_contract:{self.scene_geometry_contract or "declared_and_resolved"}',
            f'declared_source:{self.declared_geometry_source or "unknown"}',
            f'resolved_source:{self.resolved_geometry_source or "unknown"}',
        ]
        badges.extend(f'shape:{shape}' for shape in self.supported_scene_shapes if shape)
        return badges

    def has_capability_badge(self, badge: str) -> bool:
        return str(badge or '') in set(self.capability_badges)

    def require_declared_and_resolved(self) -> None:
        expected = 'geometry_contract:declared_and_resolved'
        if not self.has_capability_badge(expected):
            raise ValueError(
                'scene geometry authority does not satisfy the declared-and-resolved contract: '
                f'{self.scene_geometry_contract!r}'
            )

    def require_supported_shape(self, shape: str) -> None:
        normalized = str(shape or '').strip().lower()
        expected = f'shape:{normalized}'
        if not normalized or not self.has_capability_badge(expected):
            raise ValueError(
                f'scene geometry authority does not support shape {normalized!r}; '
                f'supported={list(self.supported_scene_shapes)!r}'
            )

    def summary(self) -> dict[str, object]:
        return {
            'authority': str(self.authority or 'planning_scene'),
            'authority_kind': str(self.authority_kind or 'planning_scene'),
            'scene_geometry_contract': str(self.scene_geometry_contract or 'declared_and_resolved'),
            'declared_geometry_source': str(self.declared_geometry_source or ''),
            'resolved_geometry_source': str(self.resolved_geometry_source or ''),
            'supported_scene_shapes': list(self.supported_scene_shapes),
            'record_count': int(len(self.records)),
            'obstacle_count': int(sum(1 for record in self.records if not record.attached)),
            'attached_object_count': int(sum(1 for record in self.records if record.attached)),
            'capability_badges': self.capability_badges,
            'records': [record.summary() for record in self.records],
            'metadata': dict(self.metadata or {}),
        }

    def metadata_patch(self) -> dict[str, object]:
        return {}

    @classmethod
    def from_scene(cls, scene: 'PlanningScene') -> 'SceneGeometryAuthority':
        if scene is None:
            raise ValueError('scene geometry authority requires a planning scene instance')
        metadata = dict(getattr(scene, 'metadata', {}) or {})
        declared_geometry_source = str(
            metadata.get('declared_geometry_source', metadata.get('geometry_source', getattr(scene, 'geometry_source', 'generated')))
            or metadata.get('geometry_source', getattr(scene, 'geometry_source', 'generated'))
        )
        resolved_geometry_source = str(
            metadata.get('resolved_geometry_source', f"{getattr(scene, 'collision_backend', 'aabb')}_planning_scene")
            or f"{getattr(scene, 'collision_backend', 'aabb')}_planning_scene"
        )
        supported_shapes = tuple(str(item) for item in metadata.get('supported_scene_shapes', ('box', 'cylinder', 'sphere')) or ('box', 'cylinder', 'sphere'))
        authority = str(metadata.get('geometry_authority_scope', metadata.get('scene_authority', 'planning_scene')) or metadata.get('scene_authority', 'planning_scene'))
        records: list[GeometryAuthorityRecord] = []
        for attached, objects in (
            (False, tuple(getattr(scene, 'obstacles', ()) or ())),
            (True, tuple(getattr(scene, 'attached_objects', ()) or ())),
        ):
            for obj in objects:
                object_summary = obj.summary() if hasattr(obj, 'summary') else {}
                resolved_geometry = _resolved_geometry_from_object(obj, object_summary)
                declared_geometry = _declared_geometry_from_object(object_summary, resolved_geometry)
                records.append(
                    GeometryAuthorityRecord(
                        object_id=str(getattr(obj, 'object_id', object_summary.get('object_id', 'object'))),
                        authority=authority,
                        geometry_source=declared_geometry_source,
                        attached=attached,
                        declared_geometry=declared_geometry,
                        resolved_geometry=resolved_geometry,
                        metadata=dict(object_summary.get('metadata', {}) or {}),
                    )
                )
        return cls(
            authority=authority,
            authority_kind=str(metadata.get('geometry_authority_kind', 'planning_scene') or 'planning_scene'),
            scene_geometry_contract=str(metadata.get('scene_geometry_contract', 'declared_and_resolved') or 'declared_and_resolved'),
            declared_geometry_source=declared_geometry_source,
            resolved_geometry_source=resolved_geometry_source,
            supported_scene_shapes=supported_shapes,
            records=tuple(records),
            metadata={
                'scene_authority': str(metadata.get('scene_authority', 'planning_scene') or 'planning_scene'),
                'collision_backend': str(getattr(scene, 'collision_backend', metadata.get('resolved_collision_backend', 'aabb'))),
                'scene_fidelity': str(metadata.get('scene_fidelity', getattr(scene, 'geometry_source', 'generated')) or getattr(scene, 'geometry_source', 'generated')),
            },
        )

    @classmethod
    def from_summary(
        cls,
        scene_summary: Mapping[str, object] | None,
        *,
        authority: str,
        authority_kind: str,
        declared_geometry_source: str,
        resolved_geometry_source: str,
        supported_scene_shapes: Iterable[str],
        collision_backend: str,
        scene_fidelity: str,
    ) -> 'SceneGeometryAuthority':
        summary = dict(scene_summary or {})
        geometry_summary = summary.get('geometry_authority')
        if isinstance(geometry_summary, Mapping):
            return cls(
                authority=str(geometry_summary.get('authority', authority) or authority),
                authority_kind=str(geometry_summary.get('authority_kind', authority_kind) or authority_kind),
                scene_geometry_contract=str(geometry_summary.get('scene_geometry_contract', 'declared_and_resolved') or 'declared_and_resolved'),
                declared_geometry_source=str(geometry_summary.get('declared_geometry_source', declared_geometry_source) or declared_geometry_source),
                resolved_geometry_source=str(geometry_summary.get('resolved_geometry_source', resolved_geometry_source) or resolved_geometry_source),
                supported_scene_shapes=tuple(str(item) for item in geometry_summary.get('supported_scene_shapes', supported_scene_shapes) or ()),
                records=tuple(
                    GeometryAuthorityRecord(
                        object_id=str(record.get('object_id', 'object') or 'object'),
                        authority=str(record.get('authority', authority) or authority),
                        geometry_source=str(record.get('geometry_source', declared_geometry_source) or declared_geometry_source),
                        attached=bool(record.get('attached', False)),
                        declared_geometry=dict(record.get('declared_geometry', {}) or {}),
                        resolved_geometry=dict(record.get('resolved_geometry', {}) or {}),
                        metadata=dict(record.get('metadata', {}) or {}),
                    )
                    for record in geometry_summary.get('records', ()) or ()
                    if isinstance(record, Mapping)
                ),
                metadata={
                    'scene_authority': str(summary.get('scene_authority', authority) or authority),
                    'collision_backend': str(summary.get('collision_backend', collision_backend) or collision_backend),
                    'scene_fidelity': str(summary.get('scene_fidelity', scene_fidelity) or scene_fidelity),
                },
            )
        return cls(
            authority=str(authority),
            authority_kind=str(authority_kind),
            scene_geometry_contract=str(summary.get('scene_geometry_contract', 'declared_and_resolved') or 'declared_and_resolved'),
            declared_geometry_source=str(summary.get('declared_geometry_source', declared_geometry_source) or declared_geometry_source),
            resolved_geometry_source=str(summary.get('resolved_geometry_source', resolved_geometry_source) or resolved_geometry_source),
            supported_scene_shapes=tuple(str(item) for item in supported_scene_shapes),
            metadata={
                'scene_authority': str(summary.get('scene_authority', authority) or authority),
                'collision_backend': str(summary.get('collision_backend', collision_backend) or collision_backend),
                'scene_fidelity': str(summary.get('scene_fidelity', scene_fidelity) or scene_fidelity),
            },
        )


SceneGeometryAuthoritySummary = SceneGeometryAuthority


def default_scene_geometry_authority() -> SceneGeometryAuthority:
    return SceneGeometryAuthority(authority='planning_scene', supported_scene_shapes=('box', 'cylinder', 'sphere'))


def summarize_scene_geometry_authority(scene: 'PlanningScene') -> SceneGeometryAuthoritySummary:
    return SceneGeometryAuthority.from_scene(scene)
