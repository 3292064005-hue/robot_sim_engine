from __future__ import annotations

from pathlib import Path
from typing import Iterable
import re

from robot_sim.model.robot_catalog_entry import RobotCatalogEntry
from robot_sim.application.services.robot_registry_support import (
    RobotCatalogStore,
    RobotSpecMapper,
    RobotSpecSerializer,
    SourcePathNormalizer,
)
from robot_sim.model.robot_spec import RobotSpec


class RobotRegistry:
    """Robot-library registry with writable overlay support.

    Args:
        robots_dir: Writable canonical robot-library directory used for save/import operations.
        readonly_roots: Optional read-only robot-library directories that remain loadable and
            listable but are never written to.

    Boundary behavior:
        Lookup order is deterministic: the writable overlay wins, then each read-only root in
        the provided order. User-imported robots can therefore override bundled defaults without
        mutating package resources.
    """

    def __init__(self, robots_dir: str | Path, readonly_roots: Iterable[str | Path] = ()) -> None:
        self.robots_dir = Path(robots_dir)
        self.robots_dir.mkdir(parents=True, exist_ok=True)
        resolved_writable = self.robots_dir.resolve()
        unique_readonly: list[Path] = []
        for item in readonly_roots:
            path = Path(item)
            if not path.exists():
                continue
            resolved = path.resolve()
            if resolved == resolved_writable:
                continue
            if any(existing.resolve() == resolved for existing in unique_readonly):
                continue
            unique_readonly.append(path)
        self._readonly_roots = tuple(unique_readonly)
        slugify = self._slugify
        self._catalog_store = RobotCatalogStore(self.robots_dir, self._readonly_roots, slugify=slugify)
        self._source_path_normalizer = SourcePathNormalizer(self.robots_dir, readonly_roots=self._readonly_roots)
        self._serializer = RobotSpecSerializer(self._source_path_normalizer)
        self._mapper = RobotSpecMapper(slugify=slugify)

    def _slugify(self, value: str) -> str:
        text = re.sub(r'[^a-zA-Z0-9_\-]+', '_', value.strip()).strip('_')
        return text.lower() or 'robot'

    def _iter_library_roots(self) -> tuple[Path, ...]:
        return self._catalog_store.iter_library_roots()

    def list_names(self) -> list[str]:
        return self._catalog_store.list_names()

    def list_specs(self) -> list[RobotSpec]:
        return [self.load(name) for name in self.list_names()]

    def list_entries(self) -> list[RobotCatalogEntry]:
        entries = [
            RobotCatalogEntry(
                name=spec.name,
                label=spec.label,
                dof=spec.dof,
                description=spec.description,
                metadata=dict(spec.metadata),
            )
            for spec in self.list_specs()
        ]
        return sorted(entries, key=lambda item: (item.label.lower(), item.name.lower()))

    def exists(self, name: str) -> bool:
        return self._catalog_store.exists(name)

    def next_available_name(self, base_name: str, *, exclude_path: str | Path | None = None) -> str:
        return self._catalog_store.next_available_name(base_name, exclude_path=exclude_path)

    def load(self, name: str) -> RobotSpec:
        path = self._catalog_store.resolve_existing_path(name)
        if path is None:
            raise FileNotFoundError(f'robot config not found: {self._catalog_store.writable_path(self._slugify(name))}')
        spec = self._mapper.from_dict(self._serializer.load_mapping(path))
        if spec.display_name is None:
            spec = RobotSpec(
                name=spec.name,
                dh_rows=spec.dh_rows,
                base_T=spec.base_T,
                tool_T=spec.tool_T,
                home_q=spec.home_q,
                display_name=spec.name,
                description=spec.description,
                metadata=spec.metadata,
                joint_names=spec.joint_names,
                link_names=spec.link_names,
                joint_types=spec.joint_types,
                joint_axes=spec.joint_axes,
                joint_limits=spec.joint_limits,
                structured_joints=spec.structured_joints,
                structured_links=spec.structured_links,
                kinematic_source=spec.kinematic_source,
                geometry_bundle_ref=spec.geometry_bundle_ref,
                collision_bundle_ref=spec.collision_bundle_ref,
                source_model_summary=spec.source_model_summary,
                canonical_model=spec.canonical_model,
                imported_package=spec.imported_package,
            )
        return spec

    def save(self, spec: RobotSpec, name: str | None = None) -> Path:
        stem = self._slugify(name or spec.name)
        path = self._catalog_store.writable_path(stem)
        payload = self.to_dict(spec)
        payload['id'] = stem
        return self._serializer.save_mapping(path, payload)

    def from_dict(self, data: dict[str, object]) -> RobotSpec:
        return self._mapper.from_dict(dict(data or {}))

    def to_dict(self, spec: RobotSpec) -> dict[str, object]:
        return self._mapper.to_dict(spec)
