from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from robot_sim.core.collision.geometry import AABB

_SUPPORTED_DECLARATION_KINDS = {'aabb', 'box', 'sphere', 'cylinder'}


@dataclass(frozen=True)
class SceneGeometryProjection:
    """Canonical declaration->validation projection for one scene geometry record.

    Attributes:
        declaration_geometry: Canonical business/UI declaration geometry.
        validation_geometry: Backend-facing validation geometry payload.
        render_geometry: Geometry payload preserved for render/export/UI surfaces.
        query_aabb: Query-time AABB consumed by broad-phase environment checks.
        adapter_kind: Stable adapter label describing the runtime projection policy.
        projection_degraded: Whether validation geometry is less expressive than the
            declaration geometry.
        validation_backend: Resolved validation backend identifier.
        validation_geometry_source: Stable provenance label for diagnostics/export.
    """

    declaration_geometry: dict[str, object]
    validation_geometry: dict[str, object]
    render_geometry: dict[str, object]
    query_aabb: AABB
    adapter_kind: str
    projection_degraded: bool
    validation_backend: str
    validation_geometry_source: str

    def summary(self) -> dict[str, object]:
        return {
            'declaration_geometry': dict(self.declaration_geometry),
            'validation_geometry': dict(self.validation_geometry),
            'render_geometry': dict(self.render_geometry),
            'query_geometry': serialize_aabb(self.query_aabb),
            'adapter_kind': str(self.adapter_kind),
            'projection_degraded': bool(self.projection_degraded),
            'validation_backend': str(self.validation_backend),
            'validation_geometry_source': str(self.validation_geometry_source),
        }


def _normalized_xyz(value: object, *, field_name: str) -> tuple[float, float, float]:
    try:
        array = np.asarray(value, dtype=float).reshape(3)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field_name} must contain exactly three finite numeric values') from exc
    if not np.isfinite(array).all():
        raise ValueError(f'{field_name} must contain only finite numeric values')
    x, y, z = array.tolist()
    return float(x), float(y), float(z)


def _positive_scalar(value: object, *, field_name: str) -> float:
    try:
        scalar = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field_name} must be numeric') from exc
    if not np.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f'{field_name} must be finite and strictly positive')
    return scalar



def serialize_aabb(geometry: AABB) -> dict[str, object]:
    return {
        'kind': 'aabb',
        'minimum': [float(value) for value in np.asarray(geometry.minimum, dtype=float).tolist()],
        'maximum': [float(value) for value in np.asarray(geometry.maximum, dtype=float).tolist()],
    }



def declaration_geometry_from_aabb(geometry: AABB) -> dict[str, object]:
    return serialize_aabb(geometry)



def aabb_from_geometry_payload(payload: Mapping[str, object]) -> AABB:
    kind = str(payload.get('kind', 'aabb') or 'aabb').strip().lower() or 'aabb'
    if kind not in _SUPPORTED_DECLARATION_KINDS:
        raise ValueError(f'unsupported declaration geometry kind: {kind}')
    if kind == 'aabb':
        minimum = np.asarray(_normalized_xyz(payload.get('minimum'), field_name='minimum'), dtype=float)
        maximum = np.asarray(_normalized_xyz(payload.get('maximum'), field_name='maximum'), dtype=float)
        if np.any(maximum < minimum):
            raise ValueError('aabb maximum must be >= minimum for every axis')
        return AABB(minimum=minimum, maximum=maximum)
    center = np.asarray(_normalized_xyz(payload.get('center'), field_name='center'), dtype=float)
    if kind == 'box':
        size = np.asarray(_normalized_xyz(payload.get('size'), field_name='size'), dtype=float)
        if np.any(size <= 0.0):
            raise ValueError('box size must be strictly positive on every axis')
        half = size * 0.5
        return AABB(minimum=center - half, maximum=center + half)
    if kind == 'sphere':
        radius = _positive_scalar(payload.get('radius'), field_name='radius')
        delta = np.asarray((radius, radius, radius), dtype=float)
        return AABB(minimum=center - delta, maximum=center + delta)
    radius = _positive_scalar(payload.get('radius'), field_name='radius')
    height = _positive_scalar(payload.get('height'), field_name='height')
    delta = np.asarray((radius, radius, height * 0.5), dtype=float)
    return AABB(minimum=center - delta, maximum=center + delta)



def normalize_declaration_geometry(
    declaration_geometry: Mapping[str, object] | None,
    *,
    fallback_geometry: AABB | None = None,
) -> dict[str, object]:
    """Normalize a declaration geometry payload into one canonical mapping.

    Args:
        declaration_geometry: Raw declaration payload.
        fallback_geometry: Optional legacy AABB fallback used when no declaration payload
            is present.

    Returns:
        dict[str, object]: Canonical declaration geometry payload.

    Raises:
        ValueError: If the payload is malformed.
    """
    if isinstance(declaration_geometry, Mapping):
        payload = dict(declaration_geometry)
    elif fallback_geometry is not None:
        payload = declaration_geometry_from_aabb(fallback_geometry)
    else:
        return {}
    kind = str(payload.get('kind', 'aabb') or 'aabb').strip().lower() or 'aabb'
    if kind not in _SUPPORTED_DECLARATION_KINDS:
        raise ValueError(f'unsupported declaration geometry kind: {kind}')
    if kind == 'aabb':
        normalized_aabb = aabb_from_geometry_payload(payload)
        return serialize_aabb(normalized_aabb)
    center = list(_normalized_xyz(payload.get('center'), field_name='center'))
    normalized: dict[str, object] = {'kind': kind, 'center': center}
    if kind == 'box':
        size = list(_normalized_xyz(payload.get('size'), field_name='size'))
        if any(value <= 0.0 for value in size):
            raise ValueError('box size must be strictly positive on every axis')
        normalized['size'] = size
    elif kind == 'sphere':
        radius = _positive_scalar(payload.get('radius'), field_name='radius')
        normalized['radius'] = float(radius)
        normalized['size'] = [float(radius * 2.0)] * 3
    else:
        radius = _positive_scalar(payload.get('radius'), field_name='radius')
        height = _positive_scalar(payload.get('height'), field_name='height')
        normalized['radius'] = float(radius)
        normalized['height'] = float(height)
        normalized['size'] = [float(radius * 2.0), float(radius * 2.0), float(height)]
    return normalized



def _capsule_backend_validation_geometry(declaration_geometry: dict[str, object]) -> tuple[dict[str, object], bool, str]:
    kind = str(declaration_geometry.get('kind', 'aabb') or 'aabb')
    if kind in {'box', 'sphere', 'cylinder'}:
        return dict(declaration_geometry), False, 'primitive_passthrough'
    return dict(declaration_geometry), False, 'aabb_passthrough'



def _aabb_backend_validation_geometry(declaration_geometry: dict[str, object]) -> tuple[dict[str, object], bool, str]:
    query_aabb = aabb_from_geometry_payload(declaration_geometry)
    validation_geometry = serialize_aabb(query_aabb)
    projection_degraded = str(declaration_geometry.get('kind', 'aabb') or 'aabb') != 'aabb'
    return validation_geometry, projection_degraded, 'primitive_to_aabb' if projection_degraded else 'aabb_passthrough'



def project_declaration_geometry(
    declaration_geometry: Mapping[str, object] | None,
    *,
    backend_id: str,
    attached: bool = False,
    fallback_geometry: AABB | None = None,
) -> SceneGeometryProjection:
    """Project one declaration geometry into backend validation and query geometry.

    Args:
        declaration_geometry: Canonical or raw declaration geometry payload.
        backend_id: Resolved validation backend identifier.
        attached: Whether the record represents an attached object.
        fallback_geometry: Optional legacy AABB fallback.

    Returns:
        SceneGeometryProjection: Canonical multi-layer geometry projection.

    Raises:
        ValueError: If the declaration payload is malformed.
    """
    _ = attached  # reserved for backend-specific attachment policies
    declaration = normalize_declaration_geometry(declaration_geometry, fallback_geometry=fallback_geometry)
    query_aabb = aabb_from_geometry_payload(declaration)
    normalized_backend = str(backend_id or 'aabb').strip().lower() or 'aabb'
    if normalized_backend == 'capsule':
        validation_geometry, projection_degraded, adapter_kind = _capsule_backend_validation_geometry(declaration)
    else:
        validation_geometry, projection_degraded, adapter_kind = _aabb_backend_validation_geometry(declaration)
    return SceneGeometryProjection(
        declaration_geometry=declaration,
        validation_geometry=validation_geometry,
        render_geometry=dict(declaration),
        query_aabb=query_aabb,
        adapter_kind=adapter_kind,
        projection_degraded=bool(projection_degraded),
        validation_backend=normalized_backend,
        validation_geometry_source=f'{normalized_backend}_planning_scene',
    )



def project_scene_object_geometry(obj: object, *, backend_id: str, attached: bool = False) -> SceneGeometryProjection:
    """Project a scene object through the explicit backend adapter model.

    Args:
        obj: SceneObject-like instance exposing ``geometry`` and ``metadata``.
        backend_id: Resolved validation backend identifier.
        attached: Whether the record represents an attached object.

    Returns:
        SceneGeometryProjection: Canonical projection payload.

    Raises:
        ValueError: If declaration geometry cannot be normalized.
    """
    metadata = dict(getattr(obj, 'metadata', {}) or {})
    declaration = metadata.get('declaration_geometry')
    geometry = getattr(obj, 'geometry', None)
    projection = project_declaration_geometry(
        declaration if isinstance(declaration, Mapping) else None,
        backend_id=str(metadata.get('validation_backend', backend_id) or backend_id),
        attached=attached,
        fallback_geometry=geometry if isinstance(geometry, AABB) else None,
    )
    return projection


__all__ = [
    'SceneGeometryProjection',
    'aabb_from_geometry_payload',
    'declaration_geometry_from_aabb',
    'normalize_declaration_geometry',
    'project_declaration_geometry',
    'project_scene_object_geometry',
    'serialize_aabb',
]
