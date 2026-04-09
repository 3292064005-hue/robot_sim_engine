from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from robot_sim.domain.enums import ImporterFidelity, JointType, KinematicConvention
from robot_sim.model.canonical_robot_model import CanonicalRobotModel
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_geometry import GeometryPrimitive, LinkGeometry, RobotGeometry
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec, RobotLinkSpec
from robot_sim.model.robot_model_bundle import RobotModelBundle
from robot_sim.model.robot_spec import RobotSpec


@dataclass(frozen=True)
class _ParsedLink:
    name: str
    has_visual: bool
    has_collision: bool
    inertial_mass: float | None
    inertial_origin: np.ndarray | None
    visual_primitives: tuple[GeometryPrimitive, ...]
    collision_primitives: tuple[GeometryPrimitive, ...]


@dataclass(frozen=True)
class _ParsedJoint:
    name: str
    parent_link: str
    child_link: str
    joint_type: JointType | None
    axis: np.ndarray
    origin_xyz: np.ndarray
    origin_rpy: np.ndarray
    limit: RobotJointLimit
    raw_type: str

    @property
    def is_fixed(self) -> bool:
        return self.joint_type is None

    @property
    def is_dynamic(self) -> bool:
        return self.joint_type is not None


class URDFModelImporter:
    """Structured serial-chain URDF importer.

    The importer preserves link / joint semantics and geometry availability while
    still producing an approximate DH chain for the existing V7 solver surface.
    Branching trees are handled conservatively by selecting the first serial
    branch and emitting explicit fidelity warnings.
    """

    importer_id = 'urdf_model'

    def capabilities(self) -> dict[str, object]:
        return {
            'source_format': 'urdf',
            'fidelity': ImporterFidelity.SERIAL_KINEMATICS.value,
            'family': 'serial_model_import',
            'notes': 'Parses serial URDF link/joint structure and preserves visual/collision availability while retaining an approximate DH runtime adapter.',
        }

    def load(self, source, *, robot_name: str | None = None, **kwargs):
        path = Path(source)
        tree = ET.parse(path)
        root = tree.getroot()
        link_table = self._parse_links(root)
        joint_table = self._parse_joints(root)
        if not joint_table:
            raise ValueError(f'no supported joints found in URDF: {path}')

        chain, warnings, resolution = self._resolve_serial_chain(link_table, joint_table)
        if not chain:
            raise ValueError(f'URDF import produced no actuated serial chain for V7 runtime: {path}')
        rows: list[DHRow] = []
        structured_joints: list[RobotJointSpec] = []
        selected_links: list[RobotLinkSpec] = []
        joint_axes: list[tuple[float, float, float]] = []
        joint_limits: list[RobotJointLimit] = []
        home_q = []
        link_names: list[str] = []
        joint_names: list[str] = []

        used_link_names: set[str] = set()
        for idx, joint in enumerate(chain):
            origin = joint.origin_xyz
            rpy = joint.origin_rpy
            a = float((origin[0] ** 2 + origin[1] ** 2) ** 0.5)
            alpha = float(rpy[0])
            d = float(origin[2])
            theta_offset = float(rpy[2])
            rows.append(
                DHRow(
                    a=a,
                    alpha=alpha,
                    d=d,
                    theta_offset=theta_offset,
                    joint_type=joint.joint_type,
                    q_min=float(joint.limit.lower),
                    q_max=float(joint.limit.upper),
                )
            )
            structured_joints.append(
                RobotJointSpec(
                    name=joint.name,
                    parent_link=joint.parent_link,
                    child_link=joint.child_link,
                    joint_type=joint.joint_type,
                    axis=joint.axis,
                    limit=joint.limit,
                    origin_translation=joint.origin_xyz,
                    origin_rpy=joint.origin_rpy,
                    metadata={'chain_index': idx},
                )
            )
            joint_axes.append(tuple(float(v) for v in joint.axis.tolist()))
            joint_limits.append(joint.limit)
            joint_names.append(joint.name)
            home_q.append(0.0)
            for link_name in (joint.parent_link, joint.child_link):
                if link_name in link_table and link_name not in used_link_names:
                    parsed_link = link_table[link_name]
                    selected_links.append(
                        RobotLinkSpec(
                            name=parsed_link.name,
                            inertial_mass=parsed_link.inertial_mass,
                            inertial_origin=parsed_link.inertial_origin,
                            has_visual=parsed_link.has_visual,
                            has_collision=parsed_link.has_collision,
                            metadata={'source': 'urdf'},
                        )
                    )
                    used_link_names.add(link_name)
                    link_names.append(link_name)

        geometry, collision_geometry, has_visual, has_collision = self._build_geometry(chain, link_table)
        fidelity = (
            ImporterFidelity.SERIAL_WITH_COLLISION.value if has_collision
            else ImporterFidelity.SERIAL_WITH_VISUAL.value if has_visual
            else ImporterFidelity.SERIAL_KINEMATICS.value
        )
        if not has_visual:
            warnings.append('URDF visual geometry missing or unsupported; runtime geometry falls back to generated capsules where needed.')
        if not has_collision:
            warnings.append('URDF collision geometry missing or unsupported; collision fidelity is reduced to generated serial proxies.')
        stem = robot_name or root.attrib.get('name') or path.stem
        root_link = self._resolve_root_link(chain, link_names)
        downgrade_records = self._build_downgrade_records(
            resolution=resolution,
            has_visual=has_visual,
            has_collision=has_collision,
        )
        fidelity_contract = self._build_runtime_fidelity_contract(
            path=path,
            root_link=root_link,
            chain=chain,
            joint_table=joint_table,
            resolution=resolution,
            has_visual=has_visual,
            has_collision=has_collision,
            fidelity=fidelity,
            downgrade_records=downgrade_records,
        )
        source_model_summary = {
            'source_format': 'urdf',
            'source_family': 'urdf_tree',
            'runtime_family': 'articulated_serial_tree',
            'import_semantics': 'serial_model',
            'joint_count': len(chain),
            'link_count': len(used_link_names),
            'dynamic_joint_count_total': int(sum(1 for item in joint_table.values() if item.is_dynamic)),
            'has_visual': has_visual,
            'has_collision': has_collision,
            'root_link': root_link,
            'selected_joint_names': list(fidelity_contract['selected_joint_names']),
            'downgrade_records': list(fidelity_contract['downgrade_records']),
            'runtime_fidelity_contract': dict(fidelity_contract),
        }
        canonical_model = CanonicalRobotModel(
            name=str(stem),
            joints=tuple(structured_joints),
            links=tuple(selected_links),
            root_link=root_link,
            source_format='urdf',
            execution_adapter='canonical_articulated_chain',
            execution_rows=tuple(rows),
            fidelity=fidelity,
            metadata={
                'importer_id': self.importer_id,
                'warnings': list(dict.fromkeys(warnings)),
                'kinematic_convention': KinematicConvention.DH_APPROXIMATE_FROM_URDF.value,
                'source_path': str(path),
                'runtime_fidelity_contract': dict(fidelity_contract),
                'downgrade_records': list(downgrade_records),
            },
        )
        spec = RobotSpec(
            name=str(stem),
            dh_rows=tuple(rows),
            base_T=np.eye(4, dtype=float),
            tool_T=np.eye(4, dtype=float),
            home_q=np.asarray(home_q, dtype=float),
            display_name=str(stem),
            metadata={
                'importer': 'urdf',
                'importer_impl': self.importer_id,
                'import_semantics': 'serial_model',
                'model_source': 'urdf_model',
                'kinematic_convention': KinematicConvention.DH_APPROXIMATE_FROM_URDF.value,
                'geometry_available': has_visual or geometry is not None,
                'collision_model': 'structured' if has_collision else 'generated_proxy',
                'source': str(path),
                'warnings': list(dict.fromkeys(warnings)),
                'notes': 'URDF source semantics are preserved in canonical/articulated payloads; the runtime now dispatches articulated execution as the primary path while retaining bounded DH rows only for legacy analytic compatibility.',
                'runtime_fidelity_contract': dict(fidelity_contract),
                'downgrade_records': list(downgrade_records),
                'runtime_semantic_family': 'articulated_serial_tree',
            },
            joint_names=tuple(joint_names),
            link_names=tuple(link_names),
            joint_types=tuple(joint.joint_type for joint in chain),
            joint_axes=tuple(joint_axes),
            joint_limits=tuple(joint_limits),
            structured_joints=tuple(structured_joints),
            structured_links=tuple(selected_links),
            kinematic_source='urdf_model',
            geometry_bundle_ref='',
            collision_bundle_ref='',
            source_model_summary=source_model_summary,
            canonical_model=canonical_model,
        )
        return RobotModelBundle(
            spec=spec,
            geometry=geometry,
            collision_geometry=collision_geometry,
            fidelity=fidelity,
            warnings=tuple(dict.fromkeys(warnings)),
            source_path=str(path),
            importer_id=self.importer_id,
            metadata={
                'source_format': 'urdf',
                'import_semantics': 'serial_model',
                'runtime_fidelity_contract': dict(fidelity_contract),
                'downgrade_records': list(downgrade_records),
            },
            source_model_summary=source_model_summary,
            canonical_model=canonical_model,
        )

    def _parse_links(self, root: ET.Element) -> dict[str, _ParsedLink]:
        parsed: dict[str, _ParsedLink] = {}
        for link in root.findall('link'):
            name = str(link.attrib.get('name', '')).strip()
            if not name:
                continue
            visual_primitives = self._extract_primitives(link.findall('visual'))
            collision_primitives = self._extract_primitives(link.findall('collision'))
            inertial = link.find('inertial')
            inertial_mass = None
            inertial_origin = None
            if inertial is not None:
                mass_tag = inertial.find('mass')
                if mass_tag is not None and mass_tag.attrib.get('value') is not None:
                    inertial_mass = float(mass_tag.attrib['value'])
                origin_tag = inertial.find('origin')
                if origin_tag is not None:
                    inertial_origin = self._parse_xyz(origin_tag.attrib.get('xyz'))
            parsed[name] = _ParsedLink(
                name=name,
                has_visual=bool(visual_primitives),
                has_collision=bool(collision_primitives),
                inertial_mass=inertial_mass,
                inertial_origin=inertial_origin,
                visual_primitives=visual_primitives,
                collision_primitives=collision_primitives,
            )
        return parsed

    def _parse_joints(self, root: ET.Element) -> dict[str, _ParsedJoint]:
        parsed: dict[str, _ParsedJoint] = {}
        supported_joint_types = {'revolute', 'prismatic', 'continuous', 'fixed'}
        for joint in root.findall('joint'):
            jtype_raw = str(joint.attrib.get('type', 'revolute')).strip()
            if jtype_raw not in supported_joint_types:
                continue
            parent = joint.find('parent')
            child = joint.find('child')
            if parent is None or child is None:
                continue
            parent_link = str(parent.attrib.get('link', '')).strip()
            child_link = str(child.attrib.get('link', '')).strip()
            if not parent_link or not child_link:
                continue
            origin = joint.find('origin')
            axis_tag = joint.find('axis')
            limit_tag = joint.find('limit')
            xyz = self._parse_xyz(origin.attrib.get('xyz') if origin is not None else None)
            rpy = self._parse_xyz(origin.attrib.get('rpy') if origin is not None else None)
            axis = self._parse_xyz(axis_tag.attrib.get('xyz') if axis_tag is not None else None, default=np.array([0.0, 0.0, 1.0], dtype=float))
            if jtype_raw == 'fixed':
                lower = upper = 0.0
            else:
                lower = float(limit_tag.attrib.get('lower', -math.pi)) if limit_tag is not None else -math.pi
                upper = float(limit_tag.attrib.get('upper', math.pi)) if limit_tag is not None else math.pi
            velocity = float(limit_tag.attrib['velocity']) if limit_tag is not None and limit_tag.attrib.get('velocity') is not None else None
            effort = float(limit_tag.attrib['effort']) if limit_tag is not None and limit_tag.attrib.get('effort') is not None else None
            if jtype_raw == 'continuous':
                lower, upper = -math.pi, math.pi
            joint_name = str(joint.attrib.get('name', f'{parent_link}_to_{child_link}'))
            parsed[joint_name] = _ParsedJoint(
                name=joint_name,
                parent_link=parent_link,
                child_link=child_link,
                joint_type=None if jtype_raw == 'fixed' else (JointType.PRISMATIC if jtype_raw == 'prismatic' else JointType.REVOLUTE),
                axis=axis,
                origin_xyz=xyz,
                origin_rpy=rpy,
                limit=RobotJointLimit(lower=lower, upper=upper, velocity=velocity, effort=effort),
                raw_type=jtype_raw,
            )
        return parsed

    def _resolve_serial_chain(self, links: dict[str, _ParsedLink], joints: dict[str, _ParsedJoint]) -> tuple[list[_ParsedJoint], list[str], dict[str, object]]:
        warnings: list[str] = []
        if not joints:
            return [], ['URDF does not contain any supported joints.'], {
                'root_candidates': [],
                'selected_root_link': '',
                'branching_links': [],
                'fixed_joint_count': 0,
                'multiple_roots': False,
                'selected_joint_names': [],
            }
        child_links = {joint.child_link for joint in joints.values()}
        root_candidates = [name for name in links if name not in child_links]
        if not root_candidates:
            inferred_roots = sorted({joint.parent_link for joint in joints.values()} - child_links)
            root_candidates = inferred_roots or sorted(links) or [next(iter(joints.values())).parent_link]
            warnings.append('URDF root link could not be determined uniquely; importer selected the best available serial chain root.')
        parent_to_joints: dict[str, list[_ParsedJoint]] = {}
        for joint in joints.values():
            parent_to_joints.setdefault(joint.parent_link, []).append(joint)
        for outgoing in parent_to_joints.values():
            outgoing.sort(key=lambda item: (0 if item.is_dynamic else 1, item.name))

        best_paths: list[list[_ParsedJoint]] = []

        def _dfs(link_name: str, seen_links: frozenset[str], seen_joints: frozenset[str]) -> list[_ParsedJoint]:
            best: list[_ParsedJoint] = []
            for joint in parent_to_joints.get(link_name, []):
                if joint.name in seen_joints or joint.child_link in seen_links:
                    continue
                candidate = [joint] + _dfs(
                    joint.child_link,
                    seen_links | {link_name, joint.child_link},
                    seen_joints | {joint.name},
                )
                candidate_score = (sum(1 for item in candidate if item.is_dynamic), len(candidate), ''.join(item.name for item in candidate))
                best_score = (sum(1 for item in best if item.is_dynamic), len(best), ''.join(item.name for item in best))
                if candidate_score > best_score:
                    best = candidate
            return best

        ordered_root_candidates = sorted(dict.fromkeys(root_candidates))
        for root_link in ordered_root_candidates:
            best_paths.append(_dfs(root_link, frozenset({root_link}), frozenset()))

        if len(ordered_root_candidates) > 1:
            warnings.append('URDF contains multiple disconnected root candidates; importer selected the serial branch with the most actuated joints.')

        selected_root_link = ''
        full_path: list[_ParsedJoint] = []
        best_score = (-1, -1, '')
        for root_link, candidate in zip(ordered_root_candidates, best_paths):
            candidate_score = (sum(1 for item in candidate if item.is_dynamic), len(candidate), ''.join(item.name for item in candidate))
            if candidate_score > best_score:
                best_score = candidate_score
                full_path = list(candidate)
                selected_root_link = str(root_link)
        if not full_path:
            return [], warnings + ['URDF serial traversal did not discover any reachable joint chain.'], {
                'root_candidates': ordered_root_candidates,
                'selected_root_link': selected_root_link,
                'branching_links': [],
                'fixed_joint_count': 0,
                'multiple_roots': len(ordered_root_candidates) > 1,
                'selected_joint_names': [],
            }

        branching_links = sorted({joint.parent_link for joint in full_path if len(parent_to_joints.get(joint.parent_link, [])) > 1})
        for link_name in branching_links:
            warnings.append(f'URDF branching detected at link {link_name}; importer selected the strongest serial child branch only.')

        collapsed: list[_ParsedJoint] = []
        pending_xyz = np.zeros(3, dtype=float)
        pending_rpy = np.zeros(3, dtype=float)
        pending_parent_link: str | None = None
        fixed_joint_count = 0
        for joint in full_path:
            if joint.is_fixed:
                fixed_joint_count += 1
                pending_xyz = pending_xyz + joint.origin_xyz
                pending_rpy = pending_rpy + joint.origin_rpy
                if pending_parent_link is None:
                    pending_parent_link = joint.parent_link
                continue
            effective_parent = pending_parent_link or joint.parent_link
            collapsed.append(
                replace(
                    joint,
                    parent_link=effective_parent,
                    origin_xyz=pending_xyz + joint.origin_xyz,
                    origin_rpy=pending_rpy + joint.origin_rpy,
                )
            )
            pending_xyz = np.zeros(3, dtype=float)
            pending_rpy = np.zeros(3, dtype=float)
            pending_parent_link = None

        if fixed_joint_count:
            warnings.append('URDF fixed joints were collapsed into the selected serial branch transform before DH approximation.')
        if not collapsed:
            return [], warnings + ['URDF serial traversal found only fixed joints; no actuated serial chain is available for the V7 runtime.'], {
                'root_candidates': ordered_root_candidates,
                'selected_root_link': selected_root_link,
                'branching_links': branching_links,
                'fixed_joint_count': fixed_joint_count,
                'multiple_roots': len(ordered_root_candidates) > 1,
                'selected_joint_names': [],
            }
        return collapsed, list(dict.fromkeys(warnings)), {
            'root_candidates': ordered_root_candidates,
            'selected_root_link': selected_root_link,
            'branching_links': branching_links,
            'fixed_joint_count': fixed_joint_count,
            'multiple_roots': len(ordered_root_candidates) > 1,
            'selected_joint_names': [joint.name for joint in collapsed],
        }


    def _build_downgrade_records(
        self,
        *,
        resolution: dict[str, object],
        has_visual: bool,
        has_collision: bool,
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        if bool(resolution.get('multiple_roots', False)):
            records.append({
                'kind': 'disconnected_roots',
                'severity': 'warning',
                'detail': 'multiple disconnected root candidates detected; strongest serial root selected',
                'selected_root_link': str(resolution.get('selected_root_link', '') or ''),
                'candidate_root_links': list(resolution.get('root_candidates', ()) or ()),
            })
        for link_name in resolution.get('branching_links', ()) or ():
            records.append({
                'kind': 'branching_tree_pruned',
                'severity': 'warning',
                'detail': f'branching detected at link {link_name}; strongest serial child branch selected',
                'link_name': str(link_name),
            })
        fixed_joint_count = int(resolution.get('fixed_joint_count', 0) or 0)
        if fixed_joint_count > 0:
            records.append({
                'kind': 'fixed_joints_collapsed',
                'severity': 'warning',
                'detail': 'fixed joints collapsed into the selected serial branch before runtime adaptation',
                'count': fixed_joint_count,
            })
        if not has_visual:
            records.append({
                'kind': 'visual_geometry_proxy',
                'severity': 'warning',
                'detail': 'visual geometry missing or unsupported; runtime falls back to generated visual proxies where needed',
            })
        if not has_collision:
            records.append({
                'kind': 'collision_geometry_proxy',
                'severity': 'warning',
                'detail': 'collision geometry missing or unsupported; runtime collision fidelity falls back to generated serial proxies',
            })
        return records

    def _build_runtime_fidelity_contract(
        self,
        *,
        path: Path,
        root_link: str,
        chain: list[_ParsedJoint],
        joint_table: dict[str, _ParsedJoint],
        resolution: dict[str, object],
        has_visual: bool,
        has_collision: bool,
        fidelity: str,
        downgrade_records: list[dict[str, object]],
    ) -> dict[str, object]:
        selected_joint_names = tuple(str(joint.name) for joint in chain)
        selected_joint_name_set = set(selected_joint_names)
        pruned_dynamic_joints = [
            str(joint.name)
            for joint in joint_table.values()
            if joint.is_dynamic and str(joint.name) not in selected_joint_name_set
        ]
        return {
            'contract_version': 'v3',
            'source_path': str(path),
            'source_family': 'urdf_tree',
            'runtime_family': 'articulated_serial_tree',
            'execution_surface': 'canonical_model',
            'execution_adapter': 'canonical_articulated_chain',
            'runtime_dispatch': {
                'primary_execution_surface': 'articulated_model',
                'primary_execution_adapter': 'canonical_articulated_chain',
                'compatibility_execution_adapters': ['canonical_dh_chain'],
            },
            'kinematic_convention': KinematicConvention.DH_APPROXIMATE_FROM_URDF.value,
            'root_link': str(root_link),
            'selected_root_link': str(resolution.get('selected_root_link', root_link) or root_link),
            'selected_joint_names': list(selected_joint_names),
            'pruned_dynamic_joint_names': pruned_dynamic_joints,
            'dynamic_joint_count_total': int(sum(1 for joint in joint_table.values() if joint.is_dynamic)),
            'selected_dynamic_joint_count': int(len(selected_joint_names)),
            'has_visual': bool(has_visual),
            'has_collision': bool(has_collision),
            'fidelity': str(fidelity),
            'downgrade_records': [dict(item) for item in downgrade_records],
            'capability_badges': [
                'source_family:urdf_tree',
                'runtime_family:articulated_serial_tree',
                'execution_surface:canonical_model',
                'execution_adapter:canonical_articulated_chain',
                f'fidelity:{fidelity}',
            ],
        }

    def _extract_primitives(self, nodes: list[ET.Element]) -> tuple[GeometryPrimitive, ...]:
        primitives: list[GeometryPrimitive] = []
        for node in nodes:
            geometry = node.find('geometry')
            if geometry is None:
                continue
            for kind in ('box', 'cylinder', 'sphere', 'mesh'):
                element = geometry.find(kind)
                if element is None:
                    continue
                params: dict[str, object] = dict(element.attrib)
                primitives.append(GeometryPrimitive(kind=kind, params=params))
                break
        return tuple(primitives)

    def _build_geometry(self, chain: list[_ParsedJoint], links: dict[str, _ParsedLink]) -> tuple[RobotGeometry | None, RobotGeometry | None, bool, bool]:
        visual_links: list[LinkGeometry] = []
        collision_links: list[LinkGeometry] = []
        has_visual = False
        has_collision = False
        emitted: set[str] = set()
        for joint in chain:
            for link_name in (joint.parent_link, joint.child_link):
                if link_name in emitted or link_name not in links:
                    continue
                emitted.add(link_name)
                parsed = links[link_name]
                fallback_radius = max(float(np.linalg.norm(joint.origin_xyz)) * 0.05, 0.03)
                visual_links.append(
                    LinkGeometry(
                        name=link_name,
                        radius=fallback_radius,
                        visual_primitives=parsed.visual_primitives,
                        collision_primitives=parsed.collision_primitives,
                        metadata={'source': 'urdf_model'},
                    )
                )
                collision_links.append(
                    LinkGeometry(
                        name=link_name,
                        radius=fallback_radius,
                        collision_primitives=parsed.collision_primitives,
                        metadata={'source': 'urdf_model'},
                    )
                )
                has_visual = has_visual or parsed.has_visual
                has_collision = has_collision or parsed.has_collision
        geometry = RobotGeometry(
            links=tuple(visual_links),
            source='urdf_model',
            fidelity='serial_with_visual' if has_visual else 'serial_kinematics',
            collision_backend_hint='capsule',
            metadata={'source': 'urdf_model', 'has_visual': has_visual},
        ) if visual_links else None
        collision_geometry = RobotGeometry(
            links=tuple(collision_links),
            source='urdf_model',
            fidelity='serial_with_collision' if has_collision else 'approximate',
            collision_backend_hint='capsule',
            metadata={'source': 'urdf_model', 'has_collision': has_collision},
        ) if collision_links else None
        return geometry, collision_geometry, has_visual, has_collision

    def _parse_xyz(self, text: str | None, *, default: np.ndarray | None = None) -> np.ndarray:
        if text is None or not str(text).strip():
            return np.asarray(default if default is not None else np.zeros(3, dtype=float), dtype=float).copy()
        values = [float(v) for v in str(text).split()]
        if len(values) != 3:
            raise ValueError(f'expected three URDF numeric components, got {values}')
        return np.asarray(values, dtype=float)

    @staticmethod
    def _resolve_root_link(chain: list[_ParsedJoint], link_names: list[str]) -> str:
        if chain:
            return str(chain[0].parent_link)
        return str(link_names[0]) if link_names else ''
