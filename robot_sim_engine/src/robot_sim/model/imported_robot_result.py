from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from robot_sim.model.fk_result import FKResult
from robot_sim.model.robot_spec import RobotSpec


@dataclass(frozen=True)
class ImportedRobotResult:
    """Terminal result for a robot-import workflow.

    Attributes:
        spec: Imported robot specification after metadata normalization.
        fk_result: FK result for the persisted robot's home configuration.
        persisted_path: Canonical YAML path written into the robot registry.
        source_path: Original import source selected by the user.
        importer_id: Resolved importer identifier that handled the source.
        fidelity: Reported importer fidelity level.
        warnings: User-facing bounded warning list emitted during import.
        geometry_available: Whether the importer produced a geometry bundle.
        source_model_summary: Structured summary retained from the parsed source model.
    """

    spec: RobotSpec
    fk_result: FKResult
    persisted_path: Path
    source_path: Path
    importer_id: str
    fidelity: str
    warnings: tuple[str, ...] = ()
    geometry_available: bool = False
    source_model_summary: dict[str, object] = field(default_factory=dict)

    @property
    def persisted_name(self) -> str:
        """Return the canonical persisted robot identifier without suffix."""
        return self.persisted_path.stem
