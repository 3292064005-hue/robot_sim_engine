from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.model.canonical_robot_model import CanonicalRobotModel
from robot_sim.model.imported_robot_package import ImportedRobotPackage
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_spec import RobotSpec


@dataclass(frozen=True)
class RobotModelBundle:
    """Imported robot payload before persistence into the registry.

    Attributes:
        spec: Canonical robot specification used by the runtime.
        geometry: Primary visual / collision geometry bundle.
        collision_geometry: Optional collision-specific geometry bundle when it
            differs from ``geometry``.
        fidelity: Declared importer fidelity level.
        warnings: User-facing bounded warning set.
        source_path: Source path used by the importer.
        importer_id: Canonical importer identifier.
        metadata: Importer-specific metadata preserved for compatibility.
        source_model_summary: Structured summary of the parsed source model.
    """

    spec: RobotSpec
    geometry: RobotGeometry | None = None
    collision_geometry: RobotGeometry | None = None
    fidelity: str = ''
    warnings: tuple[str, ...] = ()
    source_path: str = ''
    importer_id: str = ''
    metadata: dict[str, object] = field(default_factory=dict)
    source_model_summary: dict[str, object] = field(default_factory=dict)
    canonical_model: CanonicalRobotModel | None = None
    imported_package: ImportedRobotPackage | None = None

    @property
    def import_metadata(self) -> dict[str, object]:
        """Compatibility alias exposing importer metadata."""
        return dict(self.metadata)
