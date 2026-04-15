from __future__ import annotations

from pathlib import Path

import numpy as np

from robot_sim.domain.enums import KinematicConvention
from robot_sim.model.robot_geometry import LinkGeometry, RobotGeometry

from robot_sim.application.importers.urdf_model_parsing import ParsedJoint, ParsedLink


def build_runtime_geometry(chain: list[ParsedJoint], links: dict[str, ParsedLink]) -> tuple[RobotGeometry | None, RobotGeometry | None, bool, bool]:
    """Build runtime visual and collision geometry bundles from a selected chain.

    Args:
        chain: Selected serial-chain joints.
        links: Parsed URDF link table.

    Returns:
        tuple[RobotGeometry | None, RobotGeometry | None, bool, bool]:
            Visual geometry bundle, collision geometry bundle, visual availability flag,
            and collision availability flag.

    Raises:
        None: Missing links degrade to proxy-only geometry instead of failing.
    """
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


def resolve_root_link(chain: list[ParsedJoint], link_names: list[str]) -> str:
    """Resolve the canonical runtime root link for a selected serial chain."""
    if chain:
        return str(chain[0].parent_link)
    return str(link_names[0]) if link_names else ''


def build_runtime_fidelity_contract(
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
    """Build the versioned runtime fidelity contract for an imported URDF model."""
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


def build_downgrade_records(*, resolution: dict[str, object], has_visual: bool, has_collision: bool) -> list[dict[str, object]]:
    """Build structured downgrade records for non-ideal URDF imports."""
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
