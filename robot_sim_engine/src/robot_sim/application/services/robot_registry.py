from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import re

import numpy as np
import yaml

from robot_sim.domain.enums import JointType
from robot_sim.model.canonical_robot_model import CanonicalRobotModel, deserialize_canonical_robot_model, serialize_canonical_robot_model
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_catalog_entry import RobotCatalogEntry
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec, RobotLinkSpec
from robot_sim.model.imported_robot_package import ImportedRobotPackage
from robot_sim.model.robot_spec import RobotSpec


class RobotRegistry:
    """Robot-library registry with writable overlay support.

    Args:
        robots_dir: Writable canonical robot-library directory used for save/import operations.
        readonly_roots: Optional read-only robot-library directories that remain loadable and
            listable but are never written to. Installed wheels use this to expose bundled
            robot YAML files from package resources while persisting user changes under a
            per-user writable overlay.

    Boundary behavior:
        Lookup order is deterministic: the writable overlay wins, then each read-only root in
        the provided order. This allows user-imported robots to override bundled defaults
        intentionally without mutating package resources.
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

    def _iter_library_roots(self) -> tuple[Path, ...]:
        return (self.robots_dir, *self._readonly_roots)

    def list_names(self) -> list[str]:
        stems: set[str] = set()
        for root in self._iter_library_roots():
            if not root.exists():
                continue
            stems.update(p.stem for p in root.glob('*.yaml'))
        return sorted(stems)

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

    def _slugify(self, value: str) -> str:
        """Normalize robot identifiers to stable lowercase filesystem-safe slugs."""
        text = re.sub(r"[^a-zA-Z0-9_\-]+", "_", value.strip()).strip("_")
        return text.lower() or "robot"

    def _path(self, name: str) -> Path:
        return self.robots_dir / f"{name}.yaml"

    def _readonly_paths(self, name: str) -> tuple[Path, ...]:
        target = f'{name}.yaml'
        return tuple(root / target for root in self._readonly_roots if (root / target).exists())

    def _resolve_existing_path(self, name: str) -> Path | None:
        normalized = self._slugify(name)
        writable_path = self._path(normalized)
        if writable_path.exists():
            return writable_path
        for root in self._readonly_roots:
            candidate = root / f'{normalized}.yaml'
            if candidate.exists():
                return candidate
        return None

    def exists(self, name: str) -> bool:
        """Return whether the canonical robot config already exists in the overlay library.

        Args:
            name: Candidate robot identifier, normalized through the registry slug rules.

        Returns:
            bool: ``True`` when the corresponding YAML config exists in either the writable
                overlay or any configured read-only library root.
        """
        return self._resolve_existing_path(name) is not None

    def next_available_name(self, base_name: str, *, exclude_path: str | Path | None = None) -> str:
        """Allocate a non-destructive robot identifier for import/save workflows."""
        stem = self._slugify(base_name)
        allowed_path = Path(exclude_path).resolve() if exclude_path is not None else None
        candidate = stem
        index = 2
        while True:
            candidate_path = self._path(candidate)
            if candidate_path.exists():
                if allowed_path is not None and candidate_path.resolve() == allowed_path:
                    return candidate
            else:
                readonly_matches = self._readonly_paths(candidate)
                if not readonly_matches:
                    return candidate
                if allowed_path is not None and any(path.resolve() == allowed_path for path in readonly_matches):
                    return candidate
            candidate = f'{stem}_{index}'
            index += 1

    def load(self, name: str) -> RobotSpec:
        path = self._resolve_existing_path(name)
        if path is None:
            raise FileNotFoundError(f"robot config not found: {self._path(self._slugify(name))}")
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        spec = self.from_dict(data)
        if spec.display_name is None:
            spec = RobotSpec(
                name=spec.name,
                dh_rows=spec.dh_rows,
                base_T=spec.base_T,
                tool_T=spec.tool_T,
                home_q=spec.home_q,
                display_name=str(data.get("name") or spec.name),
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
        path = self._path(stem)
        payload = self.to_dict(spec)
        payload['id'] = stem
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)
        return path

    def from_dict(self, data: dict[str, Any]) -> RobotSpec:
        rows_data = data.get("dh_rows") or []
        if not rows_data:
            raise ValueError("dh_rows is required")
        rows = []
        for idx, r in enumerate(rows_data):
            q_min = float(r.get("q_min", -np.pi))
            q_max = float(r.get("q_max", np.pi))
            if q_min > q_max:
                raise ValueError(f"dh_rows[{idx}] has q_min > q_max")
            rows.append(
                DHRow(
                    a=float(r.get("a", 0.0)),
                    alpha=float(r.get("alpha", 0.0)),
                    d=float(r.get("d", 0.0)),
                    theta_offset=float(r.get("theta_offset", 0.0)),
                    joint_type=JointType(str(r.get("joint_type", JointType.REVOLUTE.value))),
                    q_min=q_min,
                    q_max=q_max,
                )
            )
        rows = tuple(rows)
        display_name = str(data.get("name") or "unnamed_robot")
        stored_name = str(data.get("id") or self._slugify(display_name))
        dof = len(rows)
        home_q = np.array(data.get("home_q", [0.0] * dof), dtype=float)
        if home_q.shape != (dof,):
            raise ValueError(f"home_q shape mismatch, expected {(dof,)}, got {home_q.shape}")
        base_T = np.array(data.get("base_T", np.eye(4).tolist()), dtype=float)
        tool_T = np.array(data.get("tool_T", np.eye(4).tolist()), dtype=float)
        if base_T.shape != (4, 4) or tool_T.shape != (4, 4):
            raise ValueError("base_T and tool_T must be 4x4")
        if not np.isfinite(home_q).all() or not np.isfinite(base_T).all() or not np.isfinite(tool_T).all():
            raise ValueError("robot configuration contains non-finite values")
        mins = np.array([r.q_min for r in rows], dtype=float)
        maxs = np.array([r.q_max for r in rows], dtype=float)
        if np.any(home_q < mins) or np.any(home_q > maxs):
            raise ValueError("home_q must lie within joint limits")
        metadata = dict(data.get("metadata") or {})
        description = str(data.get("description") or "")

        joint_names = tuple(str(item) for item in data.get('joint_names') or ())
        link_names = tuple(str(item) for item in data.get('link_names') or ())
        joint_types = tuple(JointType(str(item)) for item in data.get('joint_types') or ())
        joint_axes = tuple(tuple(float(v) for v in axis) for axis in data.get('joint_axes') or ())
        joint_limits = tuple(
            RobotJointLimit(
                lower=float(item.get('lower', -np.pi)),
                upper=float(item.get('upper', np.pi)),
                velocity=float(item['velocity']) if item.get('velocity') is not None else None,
                effort=float(item['effort']) if item.get('effort') is not None else None,
            )
            for item in data.get('joint_limits') or ()
        )
        structured_joints = tuple(
            RobotJointSpec(
                name=str(item.get('name', 'joint')),
                parent_link=str(item.get('parent_link', '')),
                child_link=str(item.get('child_link', '')),
                joint_type=JointType(str(item.get('joint_type', JointType.REVOLUTE.value))),
                axis=np.asarray(item.get('axis', [0.0, 0.0, 1.0]), dtype=float),
                limit=RobotJointLimit(
                    lower=float((item.get('limit') or {}).get('lower', -np.pi)),
                    upper=float((item.get('limit') or {}).get('upper', np.pi)),
                    velocity=float((item.get('limit') or {}).get('velocity')) if (item.get('limit') or {}).get('velocity') is not None else None,
                    effort=float((item.get('limit') or {}).get('effort')) if (item.get('limit') or {}).get('effort') is not None else None,
                ),
                origin_translation=np.asarray(item.get('origin_translation', [0.0, 0.0, 0.0]), dtype=float),
                origin_rpy=np.asarray(item.get('origin_rpy', [0.0, 0.0, 0.0]), dtype=float),
                metadata=dict(item.get('metadata') or {}),
            )
            for item in data.get('structured_joints') or ()
        )
        structured_links = tuple(
            RobotLinkSpec(
                name=str(item.get('name', 'link')),
                parent_joint=str(item.get('parent_joint')) if item.get('parent_joint') is not None else None,
                inertial_mass=float(item['inertial_mass']) if item.get('inertial_mass') is not None else None,
                inertial_origin=np.asarray(item.get('inertial_origin', [0.0, 0.0, 0.0]), dtype=float) if item.get('inertial_origin') is not None else None,
                has_visual=bool(item.get('has_visual', False)),
                has_collision=bool(item.get('has_collision', False)),
                metadata=dict(item.get('metadata') or {}),
            )
            for item in data.get('structured_links') or ()
        )
        canonical_model = deserialize_canonical_robot_model(dict(data.get('canonical_model') or {}))
        if canonical_model is None:
            canonical_model = self._synthesize_canonical_model(
                stored_name=stored_name,
                source_format=str(metadata.get('source_format', 'yaml') or 'yaml'),
                rows=rows,
                joint_names=joint_names,
                link_names=link_names,
                joint_axes=joint_axes,
                joint_limits=joint_limits,
                structured_joints=structured_joints,
                structured_links=structured_links,
            )
        imported_package_payload = data.get('imported_package') or metadata.get('imported_package')
        imported_package = ImportedRobotPackage.from_dict(imported_package_payload if isinstance(imported_package_payload, dict) else None)
        imported_package_summary = dict(data.get('imported_package_summary') or metadata.get('imported_package_summary') or {})
        if imported_package_summary:
            metadata.setdefault('imported_package_summary', imported_package_summary)
        if imported_package is not None:
            metadata.setdefault('imported_package', imported_package.to_dict())
        articulated_model_summary = dict(data.get('articulated_model_summary') or metadata.get('articulated_model_summary') or {})
        if articulated_model_summary:
            metadata.setdefault('articulated_model_summary', articulated_model_summary)
        geometry_model_summary = data.get('geometry_model_summary', metadata.get('geometry_model_summary'))
        if geometry_model_summary is not None:
            metadata.setdefault('geometry_model_summary', dict(geometry_model_summary or {}))
        if imported_package is not None:
            imported_package = imported_package.with_normalized_asset_resolution_manifest(
                geometry_bundle_ref=str(data.get('geometry_bundle_ref') or ''),
                collision_bundle_ref=str(data.get('collision_bundle_ref') or ''),
            )
            for heavy_key in (
                'runtime_model_summary',
                'articulated_model_summary',
                'geometry_model_summary',
                'imported_package_summary',
                'imported_package',
                'serialized_robot_geometry',
                'serialized_collision_geometry',
            ):
                metadata.pop(heavy_key, None)
        return RobotSpec(
            name=stored_name,
            dh_rows=rows,
            base_T=base_T,
            tool_T=tool_T,
            home_q=home_q,
            display_name=display_name,
            description=description,
            metadata=metadata,
            joint_names=joint_names,
            link_names=link_names,
            joint_types=joint_types,
            joint_axes=joint_axes,
            joint_limits=joint_limits,
            structured_joints=structured_joints,
            structured_links=structured_links,
            kinematic_source=str(data.get('kinematic_source') or ''),
            geometry_bundle_ref=str(data.get('geometry_bundle_ref') or ''),
            collision_bundle_ref=str(data.get('collision_bundle_ref') or ''),
            source_model_summary=dict(data.get('source_model_summary') or {}),
            canonical_model=canonical_model,
            imported_package=imported_package,
        )

    def to_dict(self, spec: RobotSpec) -> dict[str, Any]:
        metadata = dict(spec.metadata)
        for heavy_key in (
            'runtime_model_summary',
            'articulated_model_summary',
            'geometry_model_summary',
            'imported_package_summary',
            'imported_package',
            'serialized_robot_geometry',
            'serialized_collision_geometry',
        ):
            metadata.pop(heavy_key, None)
        metadata['execution_summary'] = dict(spec.execution_summary)
        payload: dict[str, Any] = {
            "id": spec.name,
            "name": spec.label,
            "description": spec.description,
            "metadata": metadata,
            "dh_rows": [
                {
                    "a": float(r.a),
                    "alpha": float(r.alpha),
                    "d": float(r.d),
                    "theta_offset": float(r.theta_offset),
                    "joint_type": r.joint_type.value,
                    "q_min": float(r.q_min),
                    "q_max": float(r.q_max),
                }
                for r in spec.dh_rows
            ],
            "base_T": np.asarray(spec.base_T, dtype=float).tolist(),
            "tool_T": np.asarray(spec.tool_T, dtype=float).tolist(),
            "home_q": np.asarray(spec.home_q, dtype=float).tolist(),
        }
        if spec.joint_names:
            payload['joint_names'] = list(spec.joint_names)
        if spec.link_names:
            payload['link_names'] = list(spec.link_names)
        if spec.joint_types:
            payload['joint_types'] = [item.value if hasattr(item, 'value') else str(item) for item in spec.joint_types]
        if spec.joint_axes:
            payload['joint_axes'] = [list(axis) for axis in spec.joint_axes]
        if spec.joint_limits:
            payload['joint_limits'] = [
                {
                    'lower': float(item.lower),
                    'upper': float(item.upper),
                    'velocity': None if item.velocity is None else float(item.velocity),
                    'effort': None if item.effort is None else float(item.effort),
                }
                for item in spec.joint_limits
            ]
        if spec.structured_joints:
            payload['structured_joints'] = [
                {
                    'name': item.name,
                    'parent_link': item.parent_link,
                    'child_link': item.child_link,
                    'joint_type': item.joint_type.value,
                    'axis': np.asarray(item.axis, dtype=float).tolist(),
                    'limit': {
                        'lower': float(item.limit.lower) if item.limit is not None else -np.pi,
                        'upper': float(item.limit.upper) if item.limit is not None else np.pi,
                        'velocity': None if item.limit is None or item.limit.velocity is None else float(item.limit.velocity),
                        'effort': None if item.limit is None or item.limit.effort is None else float(item.limit.effort),
                    },
                    'origin_translation': np.asarray(item.origin_translation, dtype=float).tolist(),
                    'origin_rpy': np.asarray(item.origin_rpy, dtype=float).tolist(),
                    'metadata': dict(item.metadata),
                }
                for item in spec.structured_joints
            ]
        if spec.structured_links:
            payload['structured_links'] = [
                {
                    'name': item.name,
                    'parent_joint': item.parent_joint,
                    'inertial_mass': None if item.inertial_mass is None else float(item.inertial_mass),
                    'inertial_origin': None if item.inertial_origin is None else np.asarray(item.inertial_origin, dtype=float).tolist(),
                    'has_visual': bool(item.has_visual),
                    'has_collision': bool(item.has_collision),
                    'metadata': dict(item.metadata),
                }
                for item in spec.structured_links
            ]
        if spec.kinematic_source:
            payload['kinematic_source'] = spec.kinematic_source
        if spec.geometry_bundle_ref:
            payload['geometry_bundle_ref'] = spec.geometry_bundle_ref
        if spec.collision_bundle_ref:
            payload['collision_bundle_ref'] = spec.collision_bundle_ref
        if spec.source_model_summary:
            payload['source_model_summary'] = dict(spec.source_model_summary)
        payload['runtime_model'] = spec.runtime_model.summary()
        payload['articulated_model'] = spec.articulated_model.to_dict()
        imported_package = spec.imported_package
        if imported_package is not None:
            imported_package = imported_package.with_normalized_asset_resolution_manifest(
                geometry_bundle_ref=spec.geometry_bundle_ref,
                collision_bundle_ref=spec.collision_bundle_ref,
            )
            payload['imported_package'] = imported_package.to_dict()
            payload['imported_package_summary'] = imported_package.summary()
            if imported_package.geometry_model is not None:
                payload['geometry_model'] = imported_package.geometry_model.to_dict()
                payload['geometry_model_summary'] = imported_package.geometry_model.summary()
        else:
            imported_package_summary = metadata.get('imported_package_summary')
            if imported_package_summary is not None:
                payload['imported_package_summary'] = dict(imported_package_summary or {})
            geometry_model_summary = metadata.get('geometry_model_summary')
            if geometry_model_summary is not None:
                payload['geometry_model_summary'] = dict(geometry_model_summary or {})
        payload['articulated_model_summary'] = spec.articulated_model.summary()
        serialized_canonical = serialize_canonical_robot_model(spec.canonical_model)
        if serialized_canonical is not None:
            payload['canonical_model'] = serialized_canonical
        if not payload["description"]:
            payload.pop("description")
        if not payload["metadata"]:
            payload.pop("metadata")
        return payload

    @staticmethod
    def _synthesize_canonical_model(
        *,
        stored_name: str,
        source_format: str,
        rows: tuple[DHRow, ...],
        joint_names: tuple[str, ...],
        link_names: tuple[str, ...],
        joint_axes: tuple[tuple[float, float, float], ...],
        joint_limits: tuple[RobotJointLimit, ...],
        structured_joints: tuple[RobotJointSpec, ...],
        structured_links: tuple[RobotLinkSpec, ...],
    ) -> CanonicalRobotModel:
        if structured_joints:
            joints = tuple(structured_joints)
        else:
            resolved_joint_names = joint_names or tuple(f'joint_{index}' for index in range(len(rows)))
            resolved_link_names = link_names or tuple(f'link_{index}' for index in range(len(rows) + 1))
            joints = tuple(
                RobotJointSpec(
                    name=resolved_joint_names[index],
                    parent_link=resolved_link_names[index],
                    child_link=resolved_link_names[index + 1],
                    joint_type=row.joint_type,
                    axis=joint_axes[index] if index < len(joint_axes) else np.array([0.0, 0.0, 1.0], dtype=float),
                    limit=joint_limits[index] if index < len(joint_limits) else RobotJointLimit(lower=float(row.q_min), upper=float(row.q_max)),
                    origin_translation=np.array([float(row.a), 0.0, float(row.d)], dtype=float),
                    origin_rpy=np.array([float(row.alpha), 0.0, float(row.theta_offset)], dtype=float),
                    metadata={'generated_from': 'robot_registry', 'execution_surface': 'canonical_model', 'source_projection': 'dh_rows'},
                )
                for index, row in enumerate(rows)
            )
        if structured_links:
            links = tuple(structured_links)
        else:
            resolved_link_names = link_names or tuple(f'link_{index}' for index in range(len(rows) + 1))
            links = tuple(RobotLinkSpec(name=name, metadata={'generated_from': 'robot_registry'}) for name in resolved_link_names)
        root_link = links[0].name if links else ''
        return CanonicalRobotModel(
            name=stored_name,
            joints=joints,
            links=links,
            root_link=root_link,
            source_format=source_format,
            execution_adapter='canonical_dh_chain',
            execution_rows=tuple(rows),
            fidelity='native' if source_format == 'yaml' else 'structured',
            metadata={'generated_from': 'robot_registry', 'execution_surface': 'canonical_model'},
        )
