from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_spec import RobotSpec

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.app.workflows.application_workflow import ApplicationWorkflowFacade


@dataclass(frozen=True)
class ResolvedImportBundle:
    """Canonical robot-import bundle returned by :class:`ApplicationWorkflowFacade`."""

    spec: RobotSpec
    source_path: Path
    importer_id: str
    fidelity: str
    warnings: tuple[str, ...]
    geometry_available: bool
    source_model_summary: dict[str, object]
    persisted_path: Path | None
    suggested_name: str
    staged_only: bool
    robot_geometry: RobotGeometry | None = None
    collision_geometry: RobotGeometry | None = None


def resolve_spec_reference(
    owner: 'ApplicationWorkflowFacade',
    *,
    robot: str | None = None,
    source: str | Path | None = None,
    importer_id: str | None = None,
) -> RobotSpec:
    """Resolve one canonical robot specification from registry or importer inputs.

    Args:
        owner: Canonical application workflow façade.
        robot: Optional registry robot name.
        source: Optional importer source path.
        importer_id: Optional importer override used when resolving ``source``.

    Returns:
        RobotSpec: Canonical spec used by downstream application workflows.

    Raises:
        FileNotFoundError: If the importer source path is missing.
        ValueError: If both ``robot`` and ``source`` are absent.

    Boundary behavior:
        Import-backed resolution remains staged-only here so headless and GUI callers do not
        silently persist transient imports while resolving command/session inputs.
    """
    if source not in (None, ''):
        return owner.resolve_import(source, importer_id=importer_id, persist=False).spec
    if robot in (None, ''):
        raise ValueError('request must provide either robot or source')
    return owner.load_robot_spec(str(robot))


def resolve_import(
    owner: 'ApplicationWorkflowFacade',
    source: str | Path,
    *,
    importer_id: str | None = None,
    persist: bool,
) -> ResolvedImportBundle:
    """Resolve and optionally persist one imported robot specification."""
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f'import source not found: {source_path}')
    bundle = owner.workflows.import_robot_uc.execute_bundle(source_path, importer_id=importer_id)
    requested_id = importer_id or source_path.suffix.lower().lstrip('.')
    if requested_id == 'yml':
        requested_id = 'yaml'
    imported_spec = owner.workflows.import_robot_uc.normalize_bundle_spec(bundle, requested_id=requested_id)
    preferred_name = str(getattr(imported_spec, 'name', '') or source_path.stem)
    registry = owner.registries.robot_registry
    exclude_path = source_path if source_path.parent.resolve() == registry.robots_dir.resolve() else None
    resolved_name = registry.next_available_name(preferred_name, exclude_path=exclude_path)
    runtime_spec = replace(imported_spec, name=resolved_name)
    persisted_path = None
    robot_geometry = bundle.geometry
    collision_geometry = bundle.collision_geometry
    if persist:
        persisted_path = registry.save(runtime_spec, name=resolved_name)
        runtime_spec = registry.load(persisted_path.stem)
        robot_geometry = None
        collision_geometry = None
    metadata = dict(getattr(runtime_spec, 'metadata', {}) or {})
    return ResolvedImportBundle(
        spec=runtime_spec,
        source_path=source_path,
        importer_id=str(metadata.get('importer_resolved', importer_id or requested_id or '')),
        fidelity=str(metadata.get('import_fidelity', 'unknown')),
        warnings=tuple(str(item) for item in metadata.get('warnings', ()) or ()),
        geometry_available=bool(metadata.get('geometry_available', False)),
        source_model_summary=dict(metadata.get('source_model_summary', {}) or {}),
        persisted_path=persisted_path,
        suggested_name=resolved_name,
        staged_only=not persist,
        robot_geometry=robot_geometry,
        collision_geometry=collision_geometry,
    )
