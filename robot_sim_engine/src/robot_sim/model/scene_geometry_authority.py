from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Mapping

from robot_sim.model.scene_validation_surface import summarize_record_validation_surface

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.core.collision.scene import PlanningScene, SceneObject


def _mapping_payload(summary: Mapping[str, object] | None, *keys: str) -> dict[str, object] | None:
    if summary is None:
        return None
    for key in keys:
        payload = summary.get(key)
        if isinstance(payload, Mapping):
            return dict(payload)
    return None


def _resolved_geometry_from_object(obj: 'SceneObject', summary: Mapping[str, object] | None = None) -> dict[str, object]:
    payload = _mapping_payload(summary, 'validation_geometry', 'resolved_geometry')
    if payload is not None:
        return payload
    geometry = getattr(obj, 'geometry', None)
    if geometry is None:
        return {}
    return {
        'kind': 'aabb',
        'minimum': [float(value) for value in geometry.minimum],
        'maximum': [float(value) for value in geometry.maximum],
    }



def _declared_geometry_from_object(summary: Mapping[str, object] | None, fallback: dict[str, object]) -> dict[str, object]:
    payload = _mapping_payload(summary, 'declaration_geometry', 'declared_geometry')
    if payload is not None:
        return payload
    return dict(fallback)



def _render_geometry_from_object(summary: Mapping[str, object] | None, fallback: dict[str, object]) -> dict[str, object]:
    payload = _mapping_payload(summary, 'render_geometry', 'declaration_geometry', 'declared_geometry')
    if payload is not None:
        return payload
    return dict(fallback)


@dataclass(frozen=True)
class GeometryAuthorityRecord:
    """Stable scene-geometry record projected from a planning-scene object.

    The canonical contract now separates three geometry surfaces:
    - declaration_geometry: the business/UI declaration entered by the caller
    - validation_geometry: the backend/query geometry used by collision validation
    - render_geometry: the geometry intent consumed by render/export/session projections

    Backward compatibility:
        ``declared_geometry`` and ``resolved_geometry`` remain available as aliases for
        legacy call sites while the new three-layer contract propagates through the scene
        summary and export surfaces.
    """

    object_id: str
    declaration_geometry: dict[str, object]
    validation_geometry: dict[str, object]
    render_geometry: dict[str, object]
    authority: str = 'planning_scene'
    declaration_geometry_source: str = ''
    validation_geometry_source: str = ''
    render_geometry_source: str = ''
    attached: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def declared_geometry(self) -> dict[str, object]:
        return dict(self.declaration_geometry or {})

    @property
    def resolved_geometry(self) -> dict[str, object]:
        return dict(self.validation_geometry or {})

    @property
    def geometry_source(self) -> str:
        return str(self.declaration_geometry_source or self.render_geometry_source or self.validation_geometry_source or '')

    def summary(self) -> dict[str, object]:
        declaration_geometry = dict(self.declaration_geometry or {})
        validation_geometry = dict(self.validation_geometry or {})
        render_geometry = dict(self.render_geometry or {})
        validation_surface = summarize_record_validation_surface(
            validation_geometry_source=str(self.validation_geometry_source or ''),
            validation_geometry=validation_geometry,
            attached=bool(self.attached),
        )
        return {
            'object_id': str(self.object_id),
            'authority': str(self.authority or 'planning_scene'),
            'geometry_source': self.geometry_source,
            'attached': bool(self.attached),
            'declaration_geometry_source': str(self.declaration_geometry_source or ''),
            'validation_geometry_source': str(self.validation_geometry_source or ''),
            'render_geometry_source': str(self.render_geometry_source or ''),
            'declaration_geometry': declaration_geometry,
            'validation_geometry': validation_geometry,
            'render_geometry': render_geometry,
            'validation_surface': validation_surface,
            # legacy aliases
            'declared_geometry': declaration_geometry,
            'resolved_geometry': validation_geometry,
            'metadata': dict(self.metadata or {}),
            **validation_surface,
        }


@dataclass(frozen=True)
class SceneGeometryAuthority:
    """Single scene-geometry authority contract shared by scene editing, validation, and export."""

    authority: str
    authority_kind: str = 'planning_scene'
    scene_geometry_contract: str = 'declaration_validation_render'
    declaration_geometry_source: str = ''
    validation_geometry_source: str = ''
    render_geometry_source: str = ''
    supported_scene_shapes: tuple[str, ...] = ()
    records: tuple[GeometryAuthorityRecord, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'authority', str(self.authority or 'planning_scene'))
        object.__setattr__(self, 'authority_kind', str(self.authority_kind or 'planning_scene'))
        object.__setattr__(self, 'scene_geometry_contract', str(self.scene_geometry_contract or 'declaration_validation_render'))
        object.__setattr__(self, 'declaration_geometry_source', str(self.declaration_geometry_source or ''))
        object.__setattr__(self, 'validation_geometry_source', str(self.validation_geometry_source or ''))
        object.__setattr__(self, 'render_geometry_source', str(self.render_geometry_source or ''))
        object.__setattr__(self, 'supported_scene_shapes', tuple(str(item) for item in self.supported_scene_shapes))
        object.__setattr__(self, 'records', tuple(self.records))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))

    # legacy source aliases -------------------------------------------------
    @property
    def declared_geometry_source(self) -> str:
        return str(self.declaration_geometry_source or '')

    @property
    def resolved_geometry_source(self) -> str:
        return str(self.validation_geometry_source or '')

    @property
    def capability_badges(self) -> list[str]:
        badges = [
            f'authority:{self.authority or "planning_scene"}',
            f'authority_kind:{self.authority_kind or "planning_scene"}',
            f'geometry_contract:{self.scene_geometry_contract or "declaration_validation_render"}',
            f'declaration_source:{self.declaration_geometry_source or "unknown"}',
            f'validation_source:{self.validation_geometry_source or "unknown"}',
            f'render_source:{self.render_geometry_source or "unknown"}',
        ]
        # keep legacy badges so existing diagnostics and tests do not silently drift
        badges.extend(
            [
                f'declared_source:{self.declaration_geometry_source or "unknown"}',
                f'resolved_source:{self.validation_geometry_source or "unknown"}',
                'geometry_contract:declared_and_resolved' if self.scene_geometry_contract == 'declaration_validation_render' else '',
            ]
        )
        badges.extend(f'shape:{shape}' for shape in self.supported_scene_shapes if shape)
        return [badge for badge in badges if badge]

    def has_capability_badge(self, badge: str) -> bool:
        return str(badge or '') in set(self.capability_badges)

    def require_declared_and_resolved(self) -> None:
        if self.scene_geometry_contract in {'declared_and_resolved', 'declaration_validation_render'}:
            return
        raise ValueError(
            'scene geometry authority does not satisfy the declared/resolved validation contract: '
            f'{self.scene_geometry_contract!r}'
        )

    def require_three_layer_contract(self) -> None:
        if self.scene_geometry_contract == 'declaration_validation_render':
            return
        raise ValueError(
            'scene geometry authority does not satisfy the declaration/validation/render contract: '
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
            'scene_geometry_contract': str(self.scene_geometry_contract or 'declaration_validation_render'),
            'scene_geometry_contract_version': 'v1',
            'declaration_geometry_source': str(self.declaration_geometry_source or ''),
            'validation_geometry_source': str(self.validation_geometry_source or ''),
            'render_geometry_source': str(self.render_geometry_source or ''),
            # legacy aliases
            'declared_geometry_source': str(self.declaration_geometry_source or ''),
            'resolved_geometry_source': str(self.validation_geometry_source or ''),
            'supported_scene_shapes': list(self.supported_scene_shapes),
            'record_count': int(len(self.records)),
            'obstacle_count': int(sum(1 for record in self.records if not record.attached)),
            'attached_object_count': int(sum(1 for record in self.records if record.attached)),
            'capability_badges': self.capability_badges,
            'records': [record.summary() for record in self.records],
            'metadata': dict(self.metadata or {}),
        }

    def metadata_patch(self) -> dict[str, object]:
        return {
            'scene_geometry_contract': str(self.scene_geometry_contract or 'declaration_validation_render'),
            'scene_geometry_contract_version': 'v1',
            'declaration_geometry_source': str(self.declaration_geometry_source or ''),
            'validation_geometry_source': str(self.validation_geometry_source or ''),
            'render_geometry_source': str(self.render_geometry_source or ''),
        }

    @classmethod
    def from_scene(cls, scene: 'PlanningScene') -> 'SceneGeometryAuthority':
        if scene is None:
            raise ValueError('scene geometry authority requires a planning scene instance')
        metadata = dict(getattr(scene, 'metadata', {}) or {})
        declaration_geometry_source = str(
            metadata.get('declaration_geometry_source', metadata.get('declared_geometry_source', metadata.get('geometry_source', getattr(scene, 'geometry_source', 'generated'))))
            or metadata.get('geometry_source', getattr(scene, 'geometry_source', 'generated'))
        )
        validation_geometry_source = str(
            metadata.get('validation_geometry_source', metadata.get('resolved_geometry_source', f"{getattr(scene, 'collision_backend', 'aabb')}_planning_scene"))
            or f"{getattr(scene, 'collision_backend', 'aabb')}_planning_scene"
        )
        render_geometry_source = str(
            metadata.get('render_geometry_source', metadata.get('geometry_source', declaration_geometry_source)) or declaration_geometry_source
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
                validation_geometry = _resolved_geometry_from_object(obj, object_summary)
                declaration_geometry = _declared_geometry_from_object(object_summary, validation_geometry)
                render_geometry = _render_geometry_from_object(object_summary, declaration_geometry)
                records.append(
                    GeometryAuthorityRecord(
                        object_id=str(getattr(obj, 'object_id', object_summary.get('object_id', 'object'))),
                        authority=authority,
                        declaration_geometry_source=str(object_summary.get('declaration_geometry_source', object_summary.get('declared_geometry_source', declaration_geometry_source)) or declaration_geometry_source),
                        validation_geometry_source=str(object_summary.get('validation_geometry_source', object_summary.get('resolved_geometry_source', validation_geometry_source)) or validation_geometry_source),
                        render_geometry_source=str(object_summary.get('render_geometry_source', render_geometry_source) or render_geometry_source),
                        attached=attached,
                        declaration_geometry=declaration_geometry,
                        validation_geometry=validation_geometry,
                        render_geometry=render_geometry,
                        metadata=dict(object_summary.get('metadata', {}) or {}),
                    )
                )
        return cls(
            authority=authority,
            authority_kind=str(metadata.get('geometry_authority_kind', 'planning_scene') or 'planning_scene'),
            scene_geometry_contract=str(metadata.get('scene_geometry_contract', 'declaration_validation_render') or 'declaration_validation_render'),
            declaration_geometry_source=declaration_geometry_source,
            validation_geometry_source=validation_geometry_source,
            render_geometry_source=render_geometry_source,
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
        declaration_geometry_source: str,
        validation_geometry_source: str,
        render_geometry_source: str,
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
                scene_geometry_contract=str(geometry_summary.get('scene_geometry_contract', 'declaration_validation_render') or 'declaration_validation_render'),
                declaration_geometry_source=str(geometry_summary.get('declaration_geometry_source', geometry_summary.get('declared_geometry_source', declaration_geometry_source)) or declaration_geometry_source),
                validation_geometry_source=str(geometry_summary.get('validation_geometry_source', geometry_summary.get('resolved_geometry_source', validation_geometry_source)) or validation_geometry_source),
                render_geometry_source=str(geometry_summary.get('render_geometry_source', render_geometry_source) or render_geometry_source),
                supported_scene_shapes=tuple(str(item) for item in geometry_summary.get('supported_scene_shapes', supported_scene_shapes) or supported_scene_shapes),
                records=tuple(
                    GeometryAuthorityRecord(
                        object_id=str(item.get('object_id', 'object') or 'object'),
                        declaration_geometry=dict(item.get('declaration_geometry', item.get('declared_geometry', {})) or {}),
                        validation_geometry=dict(item.get('validation_geometry', item.get('resolved_geometry', {})) or {}),
                        render_geometry=dict(item.get('render_geometry', item.get('declaration_geometry', item.get('declared_geometry', {}))) or {}),
                        authority=str(item.get('authority', geometry_summary.get('authority', authority)) or authority),
                        declaration_geometry_source=str(item.get('declaration_geometry_source', item.get('declared_geometry_source', geometry_summary.get('declaration_geometry_source', geometry_summary.get('declared_geometry_source', declaration_geometry_source)))) or declaration_geometry_source),
                        validation_geometry_source=str(item.get('validation_geometry_source', item.get('resolved_geometry_source', geometry_summary.get('validation_geometry_source', geometry_summary.get('resolved_geometry_source', validation_geometry_source)))) or validation_geometry_source),
                        render_geometry_source=str(item.get('render_geometry_source', geometry_summary.get('render_geometry_source', render_geometry_source)) or render_geometry_source),
                        attached=bool(item.get('attached', False)),
                        metadata=dict(item.get('metadata', {}) or {}),
                    )
                    for item in geometry_summary.get('records', ())
                    if isinstance(item, Mapping)
                ),
                metadata={
                    'scene_authority': str(summary.get('scene_authority', authority) or authority),
                    'collision_backend': str(collision_backend or summary.get('collision_backend', 'aabb') or 'aabb'),
                    'scene_fidelity': str(scene_fidelity or summary.get('scene_fidelity', 'generated') or 'generated'),
                },
            )
        return cls(
            authority=str(authority or summary.get('scene_authority', 'planning_scene') or 'planning_scene'),
            authority_kind=str(authority_kind or 'planning_scene'),
            scene_geometry_contract=str(summary.get('scene_geometry_contract', 'declaration_validation_render') or 'declaration_validation_render'),
            declaration_geometry_source=str(summary.get('declaration_geometry_source', summary.get('declared_geometry_source', declaration_geometry_source)) or declaration_geometry_source),
            validation_geometry_source=str(summary.get('validation_geometry_source', summary.get('resolved_geometry_source', validation_geometry_source)) or validation_geometry_source),
            render_geometry_source=str(summary.get('render_geometry_source', render_geometry_source) or render_geometry_source),
            supported_scene_shapes=tuple(str(item) for item in summary.get('supported_scene_shapes', supported_scene_shapes) or supported_scene_shapes),
            records=(),
            metadata={
                'scene_authority': str(summary.get('scene_authority', authority) or authority),
                'collision_backend': str(collision_backend or summary.get('collision_backend', 'aabb') or 'aabb'),
                'scene_fidelity': str(scene_fidelity or summary.get('scene_fidelity', 'generated') or 'generated'),
            },
        )



def default_scene_geometry_authority() -> SceneGeometryAuthority:
    return SceneGeometryAuthority(
        authority='planning_scene',
        authority_kind='planning_scene',
        scene_geometry_contract='declaration_validation_render',
        declaration_geometry_source='generated',
        validation_geometry_source='aabb_planning_scene',
        render_geometry_source='generated',
        supported_scene_shapes=('box', 'cylinder', 'sphere'),
        records=(),
        metadata={'scene_authority': 'planning_scene', 'collision_backend': 'aabb', 'scene_fidelity': 'generated'},
    )



def summarize_scene_geometry_authority(scene: 'PlanningScene') -> SceneGeometryAuthority:
    return SceneGeometryAuthority.from_scene(scene)


__all__ = [
    'GeometryAuthorityRecord',
    'SceneGeometryAuthority',
    'default_scene_geometry_authority',
    'summarize_scene_geometry_authority',
]
