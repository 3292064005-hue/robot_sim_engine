from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from robot_sim.model.articulated_robot_model import ArticulatedRobotModel
from robot_sim.model.imported_robot_package import ImportedRobotPackage
from robot_sim.model.robot_geometry_model import RobotGeometryModel
from robot_sim.model.robot_model_bundle import RobotModelBundle


class ImportRobotUseCase:
    def __init__(self, importer_registry) -> None:
        self._importers = importer_registry



    @staticmethod
    def _build_import_fidelity_breakdown(bundle: RobotModelBundle) -> dict[str, object]:
        """Build a normalized fidelity breakdown for importer outputs.

        Args:
            bundle: Structured importer bundle returned by the selected importer.

        Returns:
            dict[str, object]: Normalized fidelity semantics separating source recovery,
                runtime executability, and geometry recoverability.
        """
        summary = dict(bundle.source_model_summary or {})
        runtime_contract = dict(summary.get('runtime_fidelity_contract', {}) or {})
        raw_downgrade_records = runtime_contract.get('downgrade_records', ()) or summary.get('downgrade_records', ()) or ()
        downgrade_records: list[dict[str, object]] = []
        degradation_reasons: list[str] = []
        for item in raw_downgrade_records:
            if isinstance(item, Mapping):
                record = {str(key): value for key, value in dict(item).items()}
            else:
                record = {'kind': 'unstructured_record', 'detail': str(item)}
            downgrade_records.append(record)
            reason = str(record.get('kind', '') or record.get('detail', '') or '').strip()
            if reason:
                degradation_reasons.append(reason)
        selected_joint_names = [str(item) for item in runtime_contract.get('selected_joint_names', ()) or ()]
        geometry_recoverable = bool(bundle.geometry is not None or bundle.collision_geometry is not None)
        roadmap = dict(summary.get('fidelity_roadmap', {}) or {})
        source_recovered = bool(summary)
        runtime_executable = bool(bundle.spec.runtime_model is not None)
        mesh_assets_recoverable = bool((bundle.metadata or {}).get('mesh_assets_recoverable', geometry_recoverable))
        graph_layer = dict(runtime_contract.get('articulated_graph_layer', {}) or {})
        adapter_layer = dict(runtime_contract.get('execution_adapter_layer', {}) or {})
        return {
            'roadmap_level': str(roadmap.get('roadmap_level', bundle.fidelity or '')),
            'source_recovered': source_recovered,
            'runtime_executable': runtime_executable,
            'geometry_recoverable': geometry_recoverable,
            'graph_recovered': bool(graph_layer),
            'source_model_state': str(roadmap.get('source_model_state', 'structured_source') if source_recovered else 'missing'),
            'runtime_state': str(roadmap.get('runtime_state', 'runtime_executable') if runtime_executable else 'missing'),
            'geometry_state': str(roadmap.get('geometry_state', 'geometry_recoverable' if geometry_recoverable else 'proxy_only')),
            'graph_state': 'articulated_graph_ready' if graph_layer else 'serial_projection_only',
            'execution_adapter_state': 'adapter_ready' if adapter_layer else 'legacy_runtime_rows',
            'execution_adapter': str(adapter_layer.get('adapter_id', runtime_contract.get('execution_adapter', '')) or runtime_contract.get('execution_adapter', '')),
            'branched_tree_supported': bool(runtime_contract.get('branched_tree_supported', graph_layer.get('supports_branched_tree_projection', False))),
            'branching_detected': bool(graph_layer.get('branching_link_names')),
            'pruned_dynamic_joint_names': [str(item) for item in runtime_contract.get('pruned_dynamic_joint_names', ()) or ()],
            'mesh_assets_recoverable': mesh_assets_recoverable,
            'selected_joint_names': selected_joint_names,
            'degradation_reasons': degradation_reasons,
            'downgrade_records': downgrade_records,
        }

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
        articulated_source_payload = (bundle.metadata or {}).get('articulated_source_model')
        articulated_model = ArticulatedRobotModel.from_dict(articulated_source_payload if isinstance(articulated_source_payload, Mapping) else None)
        if articulated_model is None:
            articulated_model = bundle.spec.articulated_model
        return ImportedRobotPackage(
            package_id=str(bundle.spec.name or 'robot'),
            importer_id=str(bundle.importer_id or ''),
            source_path=str(bundle.source_path or ''),
            runtime_model=runtime_model,
            articulated_model=articulated_model,
            geometry_model=geometry_model,
            source_model_summary=dict(bundle.source_model_summary or {}),
            asset_resolution_manifest={
                'geometry_bundle_ref': str(bundle.spec.geometry_bundle_ref or ''),
                'collision_bundle_ref': str(bundle.spec.collision_bundle_ref or ''),
                'has_visual_geometry': bool(bundle.geometry is not None),
                'has_collision_geometry': bool(bundle.collision_geometry is not None),
            },
            fidelity_breakdown=ImportRobotUseCase._build_import_fidelity_breakdown(bundle),
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
        if not isinstance(loaded, RobotModelBundle):
            raise TypeError(
                f'importer {canonical_id!r} returned {type(loaded).__name__}; '
                'canonical importers must return RobotModelBundle'
            )
        if loaded.imported_package is not None:
            return loaded
        return RobotModelBundle(**{**loaded.__dict__, 'imported_package': self.build_imported_package(loaded)})

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
        runtime_model = bundle.spec.runtime_model
        articulated_model = imported_package.articulated_model
        runtime_execution_layers = dict(runtime_model.execution_layers)
        if articulated_model is not None:
            runtime_execution_layers['articulated_graph'] = {
                'surface': 'articulated_model',
                'semantic_family': str(articulated_model.semantic_family),
                'topology': dict(articulated_model.topology_summary),
                'graph_edge_pairs': [list(item) for item in articulated_model.metadata.get('graph_edge_pairs', ()) or ()],
                'branching_link_names': [str(item) for item in articulated_model.metadata.get('branching_link_names', ()) or ()],
                'supports_branched_tree_projection': bool(articulated_model.metadata.get('supports_branched_tree_projection', False)),
            }
        execution_summary = {
            'execution_adapter': str(getattr(canonical_model, 'execution_adapter', metadata.get('execution_adapter', 'robot_spec_execution_rows')) or 'robot_spec_execution_rows'),
            'execution_surface': 'canonical_model' if canonical_model is not None else str(metadata.get('execution_surface', 'robot_spec') or 'robot_spec'),
            'primary_execution_surface': 'articulated_model',
            'execution_row_count': int(len(getattr(bundle.spec, 'execution_rows', getattr(bundle.spec, 'dh_rows', ())))),
            'execution_contract_version': str(runtime_model.summary().get('execution_contract_version', 'v2')),
            'execution_layers': runtime_execution_layers,
            'articulated_topology': {} if articulated_model is None else dict(articulated_model.topology_summary),
        }
        if canonical_model is not None:
            metadata.setdefault('canonical_model_summary', canonical_model.summary())
            metadata.setdefault('execution_adapter', str(canonical_model.execution_adapter))
        metadata.setdefault('execution_surface', str(execution_summary['execution_surface']))
        metadata['execution_row_count'] = int(execution_summary['execution_row_count'])
        metadata['execution_summary'] = dict(execution_summary)
        if articulated_model is not None:
            metadata['runtime_semantic_family'] = str(articulated_model.semantic_family or metadata.get('runtime_semantic_family', 'articulated_serial_tree'))
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
