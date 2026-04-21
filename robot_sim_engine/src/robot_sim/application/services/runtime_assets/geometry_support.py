from __future__ import annotations

from dataclasses import dataclass, replace

from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_geometry_model import RobotGeometryModel
from robot_sim.model.robot_geometry_serialization import deserialize_robot_geometry
from robot_sim.model.robot_spec import RobotSpec

from .models import GeometryProjectionResult


def resolve_robot_geometry(
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


def resolve_collision_geometry(
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


@dataclass(frozen=True)
class GeometryProjectionService:
    """Resolve visual/collision geometry into one canonical geometry model."""

    def project(
        self,
        spec: RobotSpec,
        *,
        robot_geometry: RobotGeometry | None = None,
        collision_geometry: RobotGeometry | None = None,
    ) -> GeometryProjectionResult:
        visual_geometry = resolve_robot_geometry(spec, explicit_geometry=robot_geometry)
        resolved_collision_geometry = resolve_collision_geometry(
            spec,
            robot_geometry=visual_geometry,
            explicit_geometry=collision_geometry,
        )
        geometry_model = RobotGeometryModel(
            visual_geometry=visual_geometry,
            collision_geometry=resolved_collision_geometry,
            metadata={
                'robot_name': spec.name,
                'geometry_available_from_source': bool(spec.geometry_available),
                'source_model': str(spec.model_source or spec.kinematic_source or ''),
            },
        )
        return GeometryProjectionResult(
            robot_geometry=visual_geometry,
            collision_geometry=resolved_collision_geometry,
            geometry_model=geometry_model,
        )
