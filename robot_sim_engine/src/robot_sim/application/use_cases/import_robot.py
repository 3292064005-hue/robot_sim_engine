from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from robot_sim.model.imported_robot_package import ImportedRobotPackage
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_geometry_model import RobotGeometryModel
from robot_sim.model.robot_model_bundle import RobotModelBundle


class ImportRobotUseCase:
    def __init__(self, importer_registry) -> None:
        self._importers = importer_registry


    @staticmethod
    def build_imported_package(bundle: RobotModelBundle) -> ImportedRobotPackage:
        """Build a structured imported-robot package from an importer bundle.

        Args:
            bundle: Structured importer bundle returned by the selected importer.

        Returns:
            ImportedRobotPackage: Split package containing runtime, articulated, and geometry
                models plus importer fidelity metadata.

        Raises:
            ValueError: Propagates invalid runtime/articulated model invariants.
        """
        geometry_model = RobotGeometryModel(
            visual_geometry=bundle.geometry,
            collision_geometry=bundle.collision_geometry,
            metadata={
                'importer_id': str(bundle.importer_id or ''),
                'source_path': str(bundle.source_path or ''),
            },
        )
        runtime_model = bundle.spec.runtime_model
        return ImportedRobotPackage(
            package_id=str(bundle.spec.name or 'robot'),
            importer_id=str(bundle.importer_id or ''),
            source_path=str(bundle.source_path or ''),
            runtime_model=runtime_model,
            articulated_model=bundle.spec.articulated_model,
            geometry_model=geometry_model,
            source_model_summary=dict(bundle.source_model_summary or {}),
            asset_resolution_manifest={
                'geometry_bundle_ref': str(bundle.spec.geometry_bundle_ref or ''),
                'collision_bundle_ref': str(bundle.spec.collision_bundle_ref or ''),
                'has_visual_geometry': bool(bundle.geometry is not None),
                'has_collision_geometry': bool(bundle.collision_geometry is not None),
            },
            fidelity=str(bundle.fidelity or ''),
            warnings=tuple(str(item) for item in bundle.warnings),
            metadata=dict(bundle.metadata or {}),
        )

    def execute_bundle(self, source: str | Path, importer_id: str | None = None, **kwargs) -> RobotModelBundle:
        path = Path(source)
        importer_id = importer_id or path.suffix.lower().lstrip('.')
        if importer_id == 'yml':
            importer_id = 'yaml'
        canonical_id = self._importers.resolve_id(importer_id)
        importer = self._importers.get(canonical_id)
        loaded = importer.load(path, **kwargs)
        if isinstance(loaded, RobotModelBundle):
            if loaded.imported_package is not None:
                return loaded
            return RobotModelBundle(**{**loaded.__dict__, 'imported_package': self.build_imported_package(loaded)})
        geometry = RobotGeometry.simple_capsules(getattr(loaded, 'dof', 0))
        summary = dict(getattr(loaded, 'source_model_summary', {}) or {})
        fallback_bundle = RobotModelBundle(
            spec=loaded,
            geometry=geometry,
            collision_geometry=geometry,
            fidelity=str(getattr(loaded, 'metadata', {}).get('import_fidelity', 'native')),
            warnings=tuple(str(item) for item in getattr(loaded, 'metadata', {}).get('warnings', ())),
            source_path=str(path),
            importer_id=str(canonical_id),
            metadata={'legacy_adapter': True},
            source_model_summary=summary,
        )
        return RobotModelBundle(**{**fallback_bundle.__dict__, 'imported_package': self.build_imported_package(fallback_bundle)})

    def normalize_bundle_spec(self, bundle: RobotModelBundle, *, requested_id: str) -> object:
        """Normalize importer bundle metadata onto the persisted robot specification.

        Args:
            bundle: Structured importer bundle returned by ``execute_bundle``.
            requested_id: Importer identifier requested by the caller before registry
                canonicalization.

        Returns:
            RobotSpec: Immutable spec with normalized importer/source-model metadata.

        Raises:
            None: Metadata normalization is deterministic.
        """
        metadata = dict(getattr(bundle.spec, 'metadata', {}) or {})
        metadata.setdefault('importer_requested', str(requested_id))
        metadata.setdefault('importer_resolved', str(bundle.importer_id or requested_id))
        metadata.setdefault('import_fidelity', str(bundle.fidelity or metadata.get('import_fidelity', 'unknown')))
        metadata.setdefault('geometry_available', bool(bundle.geometry is not None))
        imported_package = bundle.imported_package or self.build_imported_package(bundle)
        visual_ref = 'spec.imported_package.geometry_model.visual_geometry' if imported_package.geometry_model is not None and imported_package.geometry_model.visual_geometry is not None else ''
        collision_ref = 'spec.imported_package.geometry_model.collision_geometry' if imported_package.geometry_model is not None and imported_package.geometry_model.collision_geometry is not None else ''
        metadata.setdefault('geometry_ref', visual_ref)
        metadata.setdefault('collision_geometry_ref', collision_ref)
        metadata.pop('serialized_robot_geometry', None)
        metadata.pop('serialized_collision_geometry', None)
        descriptor_table = getattr(self._importers, '_metadata', {})
        descriptor = descriptor_table.get(str(bundle.importer_id)) if hasattr(descriptor_table, 'get') else None
        if descriptor is not None:
            metadata.setdefault('import_family', str(descriptor.metadata.get('family', 'unknown')))
        canonical_model = getattr(bundle.spec, 'canonical_model', None)
        if bundle.source_model_summary:
            metadata.setdefault('source_model_summary', dict(bundle.source_model_summary))
        execution_summary = {
            'execution_adapter': str(getattr(canonical_model, 'execution_adapter', metadata.get('execution_adapter', 'robot_spec_execution_rows')) or 'robot_spec_execution_rows'),
            'execution_surface': 'canonical_model' if canonical_model is not None else str(metadata.get('execution_surface', 'robot_spec') or 'robot_spec'),
            'execution_row_count': int(len(getattr(bundle.spec, 'execution_rows', getattr(bundle.spec, 'dh_rows', ())))),
        }
        if canonical_model is not None:
            metadata.setdefault('canonical_model_summary', canonical_model.summary())
            metadata.setdefault('execution_adapter', str(canonical_model.execution_adapter))
        metadata.setdefault('execution_surface', str(execution_summary['execution_surface']))
        metadata['execution_row_count'] = int(execution_summary['execution_row_count'])
        metadata['execution_summary'] = dict(execution_summary)
        if bundle.warnings:
            notes = list(metadata.get('warnings', []))
            for warning in bundle.warnings:
                if warning not in notes:
                    notes.append(warning)
            metadata['warnings'] = notes
        if bundle.importer_id == 'urdf_skeleton':
            metadata.setdefault('import_family', 'approximate_tree_import')
        elif bundle.importer_id == 'urdf_model':
            metadata.setdefault('import_family', 'serial_model_import')
        normalized_spec = replace(
            bundle.spec,
            metadata=metadata,
            geometry_bundle_ref=visual_ref if visual_ref else bundle.spec.geometry_bundle_ref,
            collision_bundle_ref=collision_ref if collision_ref else bundle.spec.collision_bundle_ref,
            source_model_summary=dict(bundle.source_model_summary or bundle.spec.source_model_summary or {}),
            canonical_model=canonical_model or bundle.spec.canonical_model,
        )
        normalized_metadata = dict(normalized_spec.metadata)
        for heavy_key in (
            'runtime_model_summary',
            'articulated_model_summary',
            'geometry_model_summary',
            'imported_package_summary',
            'imported_package',
        ):
            normalized_metadata.pop(heavy_key, None)
        normalized_metadata['runtime_package_family'] = 'source_runtime_geometry_split'
        normalized_metadata['runtime_model_ref'] = 'spec.runtime_model'
        normalized_metadata['articulated_model_ref'] = 'spec.articulated_model'
        normalized_metadata['geometry_model_ref'] = 'spec.imported_package.geometry_model'
        normalized_metadata['imported_package_ref'] = 'spec.imported_package'
        return replace(normalized_spec, metadata=normalized_metadata, imported_package=imported_package)

    def execute(self, source: str | Path, importer_id: str | None = None, **kwargs):
        path = Path(source)
        requested_id = importer_id or path.suffix.lower().lstrip('.')
        if requested_id == 'yml':
            requested_id = 'yaml'
        bundle = self.execute_bundle(path, importer_id=requested_id, **kwargs)
        return self.normalize_bundle_spec(bundle, requested_id=str(requested_id))
