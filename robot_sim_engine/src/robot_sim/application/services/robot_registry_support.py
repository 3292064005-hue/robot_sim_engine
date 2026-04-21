from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import yaml

from robot_sim.domain.enums import JointType
from robot_sim.model.canonical_robot_model import CanonicalRobotModel, deserialize_canonical_robot_model, serialize_canonical_robot_model
from robot_sim.model.dh_row import DHRow
from robot_sim.model.imported_robot_package import ImportedRobotPackage
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec, RobotLinkSpec
from robot_sim.model.robot_spec import RobotSpec


@dataclass(frozen=True)
class SourcePathNormalizer:
    """Normalize persisted robot-source paths into stable relative metadata."""

    writable_root: Path
    readonly_roots: tuple[Path, ...] = ()

    def __init__(self, writable_root: str | Path, readonly_roots: Iterable[str | Path] = ()) -> None:
        object.__setattr__(self, 'writable_root', Path(writable_root))
        object.__setattr__(self, 'readonly_roots', tuple(Path(item) for item in readonly_roots))

    def normalize_path(self, value: object) -> object:
        if not isinstance(value, str):
            return value
        candidate = value.strip()
        if not candidate:
            return value
        try:
            path = Path(candidate)
        except (TypeError, ValueError):
            return value
        search_roots = self._search_roots()
        if not path.is_absolute():
            if len(path.parts) == 1:
                anchored = self._resolve_library_member(path, search_roots)
                if anchored is not None:
                    normalized = self._normalize_against_known_anchors(anchored, search_roots)
                    if normalized is not None:
                        return normalized
            return candidate
        normalized = self._normalize_against_known_anchors(path, search_roots)
        return candidate if normalized is None else normalized

    def normalize_payload(self, value: object, *, parent_key: str | None = None) -> object:
        if isinstance(value, dict):
            return {key: self.normalize_payload(item, parent_key=str(key)) for key, item in value.items()}
        if isinstance(value, list):
            return [self.normalize_payload(item, parent_key=parent_key) for item in value]
        if isinstance(value, tuple):
            return [self.normalize_payload(item, parent_key=parent_key) for item in value]
        if parent_key == 'source_path':
            return self.normalize_path(value)
        return value

    def _search_roots(self) -> tuple[Path, ...]:
        return (self.writable_root, *self.readonly_roots)

    @staticmethod
    def _safe_resolve(path: Path) -> Path | None:
        try:
            return path.resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            return None

    def _resolve_library_member(self, path: Path, search_roots: tuple[Path, ...]) -> Path | None:
        for root in search_roots:
            anchored = self._safe_resolve(root / path)
            if anchored is not None and anchored.exists():
                return anchored
        return None

    def _normalize_against_known_anchors(self, path: Path, search_roots: tuple[Path, ...]) -> str | None:
        resolved_path = self._safe_resolve(path)
        if resolved_path is None:
            return None
        for anchor in self._candidate_anchors(search_roots):
            resolved_anchor = self._safe_resolve(anchor)
            if resolved_anchor is None:
                continue
            try:
                relative = resolved_path.relative_to(resolved_anchor)
            except ValueError:
                continue
            normalized = relative.as_posix()
            if normalized:
                return normalized
        return None

    @staticmethod
    def _candidate_anchors(search_roots: tuple[Path, ...]) -> tuple[Path, ...]:
        anchors: list[Path] = []
        for root in search_roots:
            for anchor in (root.parent.parent, root.parent, root):
                if all(anchor != existing for existing in anchors):
                    anchors.append(anchor)
        return tuple(anchors)


@dataclass(frozen=True)
class RobotCatalogStore:
    """Own robot-library root discovery, lookup order, and path allocation."""

    robots_dir: Path
    readonly_roots: tuple[Path, ...]
    slugify: Callable[[str], str]

    def iter_library_roots(self) -> tuple[Path, ...]:
        return (self.robots_dir, *self.readonly_roots)

    def list_names(self) -> list[str]:
        stems: set[str] = set()
        for root in self.iter_library_roots():
            if not root.exists():
                continue
            stems.update(path.stem for path in root.glob('*.yaml'))
        return sorted(stems)

    def writable_path(self, name: str) -> Path:
        return self.robots_dir / f'{self.slugify(name)}.yaml'

    def readonly_paths(self, name: str) -> tuple[Path, ...]:
        target = f'{self.slugify(name)}.yaml'
        return tuple(root / target for root in self.readonly_roots if (root / target).exists())

    def resolve_existing_path(self, name: str) -> Path | None:
        normalized = self.slugify(name)
        writable_path = self.writable_path(normalized)
        if writable_path.exists():
            return writable_path
        for root in self.readonly_roots:
            candidate = root / f'{normalized}.yaml'
            if candidate.exists():
                return candidate
        return None

    def exists(self, name: str) -> bool:
        return self.resolve_existing_path(name) is not None

    def next_available_name(self, base_name: str, *, exclude_path: str | Path | None = None) -> str:
        stem = self.slugify(base_name)
        allowed_path = Path(exclude_path).resolve() if exclude_path is not None else None
        candidate = stem
        index = 2
        while True:
            candidate_path = self.writable_path(candidate)
            if candidate_path.exists():
                if allowed_path is not None and candidate_path.resolve() == allowed_path:
                    return candidate
            else:
                readonly_matches = self.readonly_paths(candidate)
                if not readonly_matches:
                    return candidate
                if allowed_path is not None and any(path.resolve() == allowed_path for path in readonly_matches):
                    return candidate
            candidate = f'{stem}_{index}'
            index += 1


@dataclass(frozen=True)
class RobotSpecSerializer:
    """Own YAML transport plus source-path normalization for persisted robot specs."""

    source_path_normalizer: SourcePathNormalizer

    def load_mapping(self, path: Path) -> dict[str, Any]:
        with path.open('r', encoding='utf-8') as handle:
            return dict(yaml.safe_load(handle) or {})

    def save_mapping(self, path: Path, payload: dict[str, Any]) -> Path:
        normalized = self.source_path_normalizer.normalize_payload(payload)
        with path.open('w', encoding='utf-8') as handle:
            yaml.safe_dump(normalized, handle, sort_keys=False, allow_unicode=True)
        return path


@dataclass(frozen=True)
class RobotSpecMapper:
    """Own conversion between persisted dictionaries and :class:`RobotSpec`."""

    slugify: Callable[[str], str]

    def from_dict(self, data: dict[str, Any]) -> RobotSpec:
        rows_data = data.get('dh_rows') or []
        if not rows_data:
            raise ValueError('dh_rows is required')
        rows = []
        for idx, row_payload in enumerate(rows_data):
            q_min = float(row_payload.get('q_min', -np.pi))
            q_max = float(row_payload.get('q_max', np.pi))
            if q_min > q_max:
                raise ValueError(f'dh_rows[{idx}] has q_min > q_max')
            rows.append(
                DHRow(
                    a=float(row_payload.get('a', 0.0)),
                    alpha=float(row_payload.get('alpha', 0.0)),
                    d=float(row_payload.get('d', 0.0)),
                    theta_offset=float(row_payload.get('theta_offset', 0.0)),
                    joint_type=JointType(str(row_payload.get('joint_type', JointType.REVOLUTE.value))),
                    q_min=q_min,
                    q_max=q_max,
                )
            )
        rows = tuple(rows)
        display_name = str(data.get('name') or 'unnamed_robot')
        stored_name = str(data.get('id') or self.slugify(display_name))
        dof = len(rows)
        home_q = np.array(data.get('home_q', [0.0] * dof), dtype=float)
        if home_q.shape != (dof,):
            raise ValueError(f'home_q shape mismatch, expected {(dof,)}, got {home_q.shape}')
        base_T = np.array(data.get('base_T', np.eye(4).tolist()), dtype=float)
        tool_T = np.array(data.get('tool_T', np.eye(4).tolist()), dtype=float)
        if base_T.shape != (4, 4) or tool_T.shape != (4, 4):
            raise ValueError('base_T and tool_T must be 4x4')
        if not np.isfinite(home_q).all() or not np.isfinite(base_T).all() or not np.isfinite(tool_T).all():
            raise ValueError('robot configuration contains non-finite values')
        mins = np.array([row.q_min for row in rows], dtype=float)
        maxs = np.array([row.q_max for row in rows], dtype=float)
        if np.any(home_q < mins) or np.any(home_q > maxs):
            raise ValueError('home_q must lie within joint limits')
        metadata = dict(data.get('metadata') or {})
        description = str(data.get('description') or '')

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
            'id': spec.name,
            'name': spec.label,
            'description': spec.description,
            'metadata': metadata,
            'dh_rows': [
                {
                    'a': float(row.a),
                    'alpha': float(row.alpha),
                    'd': float(row.d),
                    'theta_offset': float(row.theta_offset),
                    'joint_type': row.joint_type.value,
                    'q_min': float(row.q_min),
                    'q_max': float(row.q_max),
                }
                for row in spec.dh_rows
            ],
            'base_T': np.asarray(spec.base_T, dtype=float).tolist(),
            'tool_T': np.asarray(spec.tool_T, dtype=float).tolist(),
            'home_q': np.asarray(spec.home_q, dtype=float).tolist(),
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
        if not payload['description']:
            payload.pop('description')
        if not payload['metadata']:
            payload.pop('metadata')
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
