from __future__ import annotations

from dataclasses import replace

from robot_sim.application.importers.importer_descriptor import ImporterDescriptor
from robot_sim.application.importers.urdf_model_importer import URDFModelImporter
from robot_sim.application.importers.urdf_skeleton_importer import URDFSkeletonRobotImporter
from robot_sim.application.importers.yaml_importer import YAMLRobotImporter

__all__ = ['ImporterRegistry', 'URDFModelImporter', 'URDFSkeletonRobotImporter', 'YAMLRobotImporter']


class ImporterRegistry:
    """Registry of available robot importers."""

    def __init__(self) -> None:
        self._importers: dict[str, object] = {}
        self._aliases: dict[str, str] = {}
        self._metadata: dict[str, ImporterDescriptor] = {}

    def register(
        self,
        importer_id: str,
        importer: object,
        *,
        metadata: dict[str, object] | None = None,
        aliases: tuple[str, ...] = (),
        replace: bool = False,
        source: str = 'runtime',
    ) -> None:
        canonical_id = str(importer_id)
        alias_tuple = tuple(str(alias) for alias in aliases if str(alias) != canonical_id)
        if canonical_id in self._importers and not replace:
            raise ValueError(f'duplicate importer id: {canonical_id}')
        for alias in alias_tuple:
            owner = self._aliases.get(alias)
            if owner is not None and owner != canonical_id and not replace:
                raise ValueError(f'duplicate importer alias: {alias}')
        if replace and canonical_id in self._metadata:
            for alias in self._metadata[canonical_id].aliases:
                self._aliases.pop(alias, None)
        merged_metadata = dict(getattr(importer, 'capabilities', lambda: {})() or {})
        merged_metadata.update(dict(metadata or {}))
        merged_metadata.setdefault('canonical_id', canonical_id)
        merged_metadata.setdefault('source', str(source))
        if 'fidelity' not in merged_metadata:
            raise ValueError(f'importer metadata missing fidelity: {canonical_id}')
        self._importers[canonical_id] = importer
        self._metadata[canonical_id] = ImporterDescriptor(
            importer_id=canonical_id,
            aliases=alias_tuple,
            metadata=merged_metadata,
        )
        for alias in alias_tuple:
            self._aliases[alias] = canonical_id

    def register_alias(self, alias: str, canonical_id: str) -> None:
        """Register one compatibility alias for an existing canonical importer."""
        normalized_alias = str(alias)
        canonical = str(canonical_id)
        if canonical not in self._importers:
            raise KeyError(f'unknown importer canonical id: {canonical}')
        if normalized_alias == canonical:
            return
        owner = self._aliases.get(normalized_alias)
        if owner is not None and owner != canonical:
            raise ValueError(f'duplicate importer alias: {normalized_alias}')
        self._aliases[normalized_alias] = canonical
        descriptor = self._metadata[canonical]
        alias_tuple = tuple(dict.fromkeys((*descriptor.aliases, normalized_alias)))
        self._metadata[canonical] = replace(descriptor, aliases=alias_tuple)

    def resolve_id(self, importer_id: str) -> str:
        key = str(importer_id)
        return self._aliases.get(key, key)

    def get(self, importer_id: str):
        canonical = self.resolve_id(importer_id)
        if canonical not in self._importers:
            raise KeyError(f'unknown importer: {importer_id}')
        return self._importers[canonical]

    def resolve(self, importer_id: str):
        return self.get(importer_id)

    def ids(self) -> list[str]:
        return sorted(self._importers)

    def descriptors(self) -> list[ImporterDescriptor]:
        return [self._metadata[key] for key in self.ids()]
