from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.model.robot_geometry import RobotGeometry


@dataclass(frozen=True)
class RobotGeometryModel:
    """Structured geometry model that keeps visual and collision assets separate.

    Args:
        visual_geometry: Visual geometry bundle exposed to render and screenshot providers.
        collision_geometry: Collision geometry bundle exposed to scene/query providers.
        geometry_contract: Stable contract label describing how geometry is split.

    Boundary behavior:
        The current runtime continues to support a single shared geometry bundle. When
        ``collision_geometry`` is omitted, consumers may explicitly fall back to the visual
        bundle instead of guessing through metadata patches.
    """

    visual_geometry: RobotGeometry | None = None
    collision_geometry: RobotGeometry | None = None
    geometry_contract: str = 'split_visual_collision'
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def has_visual_geometry(self) -> bool:
        return self.visual_geometry is not None

    @property
    def has_collision_geometry(self) -> bool:
        return self.collision_geometry is not None


    def to_dict(self) -> dict[str, object]:
        from robot_sim.application.services.runtime_asset_service import serialize_robot_geometry
        return {
            'geometry_contract': str(self.geometry_contract or 'split_visual_collision'),
            'visual_geometry': serialize_robot_geometry(self.visual_geometry),
            'collision_geometry': serialize_robot_geometry(self.collision_geometry),
            'metadata': dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> 'RobotGeometryModel | None':
        if not isinstance(payload, dict) or not payload:
            return None
        from robot_sim.application.services.runtime_asset_service import deserialize_robot_geometry

        visual_summary = payload.get('visual_geometry')
        collision_summary = payload.get('collision_geometry')
        return cls(
            visual_geometry=deserialize_robot_geometry(visual_summary if isinstance(visual_summary, dict) else None),
            collision_geometry=deserialize_robot_geometry(collision_summary if isinstance(collision_summary, dict) else None),
            geometry_contract=str(payload.get('geometry_contract', 'split_visual_collision') or 'split_visual_collision'),
            metadata=dict(payload.get('metadata', {}) or {}),
        )

    def summary(self) -> dict[str, object]:
        def _summary(bundle: RobotGeometry | None) -> dict[str, object] | None:
            if bundle is None:
                return None
            return {
                'source': str(bundle.source),
                'fidelity': str(bundle.fidelity),
                'collision_backend_hint': str(bundle.collision_backend_hint),
                'link_count': int(len(bundle.links)),
                'metadata': dict(bundle.metadata or {}),
            }
        return {
            'geometry_contract': str(self.geometry_contract or 'split_visual_collision'),
            'has_visual_geometry': bool(self.has_visual_geometry),
            'has_collision_geometry': bool(self.has_collision_geometry),
            'visual_geometry': _summary(self.visual_geometry),
            'collision_geometry': _summary(self.collision_geometry),
            'metadata': dict(self.metadata or {}),
        }
