from __future__ import annotations

import numpy as np

from robot_sim.model.robot_geometry import GeometryPrimitive, LinkGeometry, RobotGeometry


def serialize_robot_geometry(geometry: RobotGeometry | None) -> dict[str, object] | None:
    """Serialize a runtime geometry bundle into JSON/YAML-safe primitives.

    Args:
        geometry: Structured geometry bundle or ``None``.

    Returns:
        dict[str, object] | None: Serializable payload. ``None`` stays ``None``.

    Boundary behavior:
        NumPy arrays are normalized to Python lists so the payload can be persisted in
        config files, registry snapshots, and export bundles without application-layer
        helpers.
    """
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
    """Deserialize persisted geometry payloads back into ``RobotGeometry``.

    Args:
        payload: Serializable payload produced by :func:`serialize_robot_geometry`.

    Returns:
        RobotGeometry | None: Structured geometry bundle or ``None`` for empty payloads.

    Raises:
        ValueError: Propagates invalid numeric conversions from malformed payload values.

    Boundary behavior:
        Missing optional fields are normalized to the runtime defaults used by
        ``RobotGeometry`` and ``LinkGeometry`` so registry round-trips remain stable.
    """
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


__all__ = ['deserialize_robot_geometry', 'serialize_robot_geometry']
