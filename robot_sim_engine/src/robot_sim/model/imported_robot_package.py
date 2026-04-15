from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.model.articulated_robot_model import ArticulatedRobotModel
from robot_sim.model.robot_geometry_model import RobotGeometryModel
from robot_sim.model.runtime_robot_model import RuntimeRobotModel


@dataclass(frozen=True)
class ImportedRobotPackage:
    """Structured import package persisted alongside a robot spec.

    The package separates source-model, runtime-model, and geometry-model summaries so
    downstream consumers no longer need to reverse-engineer importer semantics from a single
    metadata dictionary.
    """

    package_id: str
    importer_id: str
    source_path: str
    runtime_model: RuntimeRobotModel
    articulated_model: ArticulatedRobotModel | None = None
    geometry_model: RobotGeometryModel | None = None
    source_model_summary: dict[str, object] = field(default_factory=dict)
    asset_resolution_manifest: dict[str, object] = field(default_factory=dict)
    fidelity_breakdown: dict[str, object] = field(default_factory=dict)
    fidelity: str = ''
    warnings: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


    def to_dict(self) -> dict[str, object]:
        return {
            'package_id': str(self.package_id),
            'importer_id': str(self.importer_id),
            'source_path': str(self.source_path),
            'runtime_model': self.runtime_model.summary(),
            'articulated_model': None if self.articulated_model is None else self.articulated_model.to_dict(),
            'geometry_model': None if self.geometry_model is None else self.geometry_model.to_dict(),
            'source_model_summary': dict(self.source_model_summary or {}),
            'asset_resolution_manifest': dict(self.asset_resolution_manifest or {}),
            'fidelity_breakdown': dict(self.fidelity_breakdown or {}),
            'fidelity': str(self.fidelity or ''),
            'warnings': [str(item) for item in self.warnings],
            'metadata': dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> 'ImportedRobotPackage | None':
        if not isinstance(payload, dict) or not payload:
            return None
        runtime_payload = dict(payload.get('runtime_model') or {})
        if not runtime_payload:
            return None
        from robot_sim.model.runtime_robot_model import deserialize_runtime_robot_model

        runtime_model = deserialize_runtime_robot_model(runtime_payload)
        articulated_model = ArticulatedRobotModel.from_dict(payload.get('articulated_model') if isinstance(payload.get('articulated_model'), dict) else runtime_payload.get('articulated_model_summary') if isinstance(runtime_payload.get('articulated_model_summary'), dict) else None)
        geometry_model = RobotGeometryModel.from_dict(payload.get('geometry_model') if isinstance(payload.get('geometry_model'), dict) else None)
        return cls(
            package_id=str(payload.get('package_id', '') or ''),
            importer_id=str(payload.get('importer_id', '') or ''),
            source_path=str(payload.get('source_path', '') or ''),
            runtime_model=runtime_model,
            articulated_model=articulated_model,
            geometry_model=geometry_model,
            source_model_summary=dict(payload.get('source_model_summary', {}) or {}),
            asset_resolution_manifest=dict(payload.get('asset_resolution_manifest', {}) or {}),
            fidelity_breakdown=dict(payload.get('fidelity_breakdown', {}) or {}),
            fidelity=str(payload.get('fidelity', '') or ''),
            warnings=tuple(str(item) for item in payload.get('warnings', ()) or ()),
            metadata=dict(payload.get('metadata', {}) or {}),
        )

    def summary(self) -> dict[str, object]:
        return {
            'package_id': str(self.package_id),
            'importer_id': str(self.importer_id),
            'source_path': str(self.source_path),
            'fidelity': str(self.fidelity or ''),
            'warnings': [str(item) for item in self.warnings],
            'runtime_model': self.runtime_model.summary(),
            'articulated_model': None if self.articulated_model is None else self.articulated_model.summary(),
            'geometry_model': None if self.geometry_model is None else self.geometry_model.summary(),
            'source_model_summary': dict(self.source_model_summary or {}),
            'asset_resolution_manifest': dict(self.asset_resolution_manifest or {}),
            'fidelity_breakdown': dict(self.fidelity_breakdown or {}),
            'metadata': dict(self.metadata or {}),
        }
