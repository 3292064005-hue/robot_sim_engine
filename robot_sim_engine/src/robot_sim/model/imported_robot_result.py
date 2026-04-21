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
        fk_result: FK result for the loaded robot's home configuration.
        source_path: Original import source selected by the user.
        importer_id: Resolved importer identifier that handled the source.
        fidelity: Reported importer fidelity level.
        warnings: User-facing bounded warning list emitted during import.
        geometry_available: Whether the importer produced a geometry bundle.
        source_model_summary: Structured summary retained from the parsed source model.
        persisted_path: Canonical YAML path written into the robot registry when the import is
            persisted immediately. ``None`` indicates a staged transient import.
        suggested_name: Runtime identity reserved for a staged import before persistence.
        staged_only: Whether the import is currently loaded transiently and still requires a
            later save/publish step.
    """

    spec: RobotSpec
    fk_result: FKResult
    source_path: Path
    importer_id: str
    fidelity: str
    warnings: tuple[str, ...] = ()
    geometry_available: bool = False
    source_model_summary: dict[str, object] = field(default_factory=dict)
    persisted_path: Path | None = None
    suggested_name: str = ''
    staged_only: bool = False

    @property
    def persisted_name(self) -> str:
        """Return the canonical persisted or staged robot identifier without suffix."""
        if self.persisted_path is not None:
            return self.persisted_path.stem
        return str(self.suggested_name or self.spec.name)
