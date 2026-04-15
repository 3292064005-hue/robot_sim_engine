from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import numpy as np

from robot_sim.domain.enums import ImporterFidelity, KinematicConvention
from robot_sim.application.importers.urdf_model_canonical import build_canonical_serial_model
from robot_sim.application.importers.urdf_model_parsing import ParsedJoint, ParsedLink, parse_joints, parse_links
from robot_sim.application.importers.urdf_model_runtime import (
    build_downgrade_records,
    build_runtime_fidelity_contract,
    build_runtime_geometry,
    resolve_root_link,
)
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_model_bundle import RobotModelBundle
from robot_sim.model.robot_spec import RobotSpec



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
        root_link = self._resolve_root_link(chain, [])
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
        canonical_assembly = build_canonical_serial_model(
            path=path,
            importer_id=self.importer_id,
            stem=str(stem),
            chain=chain,
            link_table=link_table,
            root_link=root_link,
            fidelity=fidelity,
            warnings=warnings,
            fidelity_contract=fidelity_contract,
            downgrade_records=downgrade_records,
        )
        source_model_summary = {
            'source_format': 'urdf',
            'source_family': 'urdf_tree',
            'runtime_family': 'articulated_serial_tree',
            'import_semantics': 'serial_model',
            'joint_count': len(chain),
            'link_count': len(canonical_assembly.link_names),
            'dynamic_joint_count_total': int(sum(1 for item in joint_table.values() if item.is_dynamic)),
            'has_visual': has_visual,
            'has_collision': has_collision,
            'root_link': root_link,
            'selected_joint_names': list(fidelity_contract['selected_joint_names']),
            'downgrade_records': list(fidelity_contract['downgrade_records']),
            'runtime_fidelity_contract': dict(fidelity_contract),
            'fidelity_roadmap': {
                'roadmap_level': str(fidelity),
                'source_model_state': 'structured_source',
                'runtime_state': 'runtime_executable',
                'geometry_state': 'geometry_recoverable' if has_visual or has_collision else 'proxy_only',
            },
        }
        canonical_model = canonical_assembly.canonical_model
        spec = RobotSpec(
            name=str(stem),
            dh_rows=tuple(canonical_assembly.rows),
            base_T=np.eye(4, dtype=float),
            tool_T=np.eye(4, dtype=float),
            home_q=np.asarray(canonical_assembly.home_q, dtype=float),
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
            joint_names=tuple(canonical_assembly.joint_names),
            link_names=tuple(canonical_assembly.link_names),
            joint_types=tuple(joint.joint_type for joint in chain),
            joint_axes=tuple(canonical_assembly.joint_axes),
            joint_limits=tuple(canonical_assembly.joint_limits),
            structured_joints=tuple(canonical_assembly.structured_joints),
            structured_links=tuple(canonical_assembly.selected_links),
            kinematic_source='urdf_model',
            geometry_bundle_ref='bundle.geometry' if geometry is not None else '',
            collision_bundle_ref='bundle.collision_geometry' if collision_geometry is not None else '',
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

    def _parse_links(self, root: ET.Element) -> dict[str, ParsedLink]:
        """Parse URDF link declarations through the extracted parser layer."""
        return parse_links(root)

    def _parse_joints(self, root: ET.Element) -> dict[str, ParsedJoint]:
        """Parse URDF joints through the extracted parser layer."""
        return parse_joints(root)

    def _resolve_serial_chain(self, links: dict[str, ParsedLink], joints: dict[str, ParsedJoint]) -> tuple[list[ParsedJoint], list[str], dict[str, object]]:
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
        parent_to_joints: dict[str, list[ParsedJoint]] = {}
        for joint in joints.values():
            parent_to_joints.setdefault(joint.parent_link, []).append(joint)
        for outgoing in parent_to_joints.values():
            outgoing.sort(key=lambda item: (0 if item.is_dynamic else 1, item.name))

        best_paths: list[list[ParsedJoint]] = []

        def _dfs(link_name: str, seen_links: frozenset[str], seen_joints: frozenset[str]) -> list[ParsedJoint]:
            best: list[ParsedJoint] = []
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
        full_path: list[ParsedJoint] = []
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

        collapsed: list[ParsedJoint] = []
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
        """Build typed downgrade records through the runtime-adapter helper layer."""
        return build_downgrade_records(
            resolution=resolution,
            has_visual=has_visual,
            has_collision=has_collision,
        )

    def _build_runtime_fidelity_contract(
        self,
        *,
        path: Path,
        root_link: str,
        chain: list[ParsedJoint],
        joint_table: dict[str, ParsedJoint],
        resolution: dict[str, object],
        has_visual: bool,
        has_collision: bool,
        fidelity: str,
        downgrade_records: list[dict[str, object]],
    ) -> dict[str, object]:
        """Build the runtime fidelity contract through the extracted runtime layer."""
        return build_runtime_fidelity_contract(
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

    def _extract_primitives(self, nodes: list[ET.Element]):
        """Compatibility shim retained while runtime geometry parsing lives in urdf_model_parsing."""
        from robot_sim.application.importers.urdf_model_parsing import extract_primitives
        return extract_primitives(nodes)

    def _build_geometry(self, chain: list[ParsedJoint], links: dict[str, ParsedLink]) -> tuple[RobotGeometry | None, RobotGeometry | None, bool, bool]:
        """Build runtime geometry through the extracted runtime-adapter layer."""
        return build_runtime_geometry(chain, links)

    def _parse_xyz(self, text: str | None, *, default: np.ndarray | None = None) -> np.ndarray:
        """Compatibility shim retained while vector parsing lives in urdf_model_parsing."""
        from robot_sim.application.importers.urdf_model_parsing import parse_xyz
        return parse_xyz(text, default=default)

    @staticmethod
    def _resolve_root_link(chain: list[ParsedJoint], link_names: list[str]) -> str:
        """Resolve the canonical runtime root link through the extracted runtime-adapter layer."""
        return resolve_root_link(chain, link_names)
