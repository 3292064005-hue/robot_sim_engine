from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from robot_sim.domain.enums import KinematicConvention
from robot_sim.model.articulated_robot_model import ArticulatedJointModel, ArticulatedRobotModel
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


def summarize_articulated_source_graph(
    *,
    links: dict[str, ParsedLink],
    joints: dict[str, ParsedJoint],
    selected_root_link: str,
    root_candidates: tuple[str, ...] = (),
) -> dict[str, object]:
    """Summarize the complete URDF articulated graph before any serial execution adaptation.

    Args:
        links: Parsed URDF link table.
        joints: Parsed URDF joint table.
        selected_root_link: Root chosen for the runtime graph seed.
        root_candidates: Optional root candidates discovered during importer resolution.

    Returns:
        dict[str, object]: Stable graph summary including links, edges, roots, branching links,
            and dynamic/fixed joint partitions.

    Boundary behavior:
        Disconnected roots are preserved in the summary rather than being silently dropped so
        runtime diagnostics and scene-graph projection can reflect the full imported topology.
    """
    parent_to_joints: dict[str, list[ParsedJoint]] = defaultdict(list)
    child_links = {joint.child_link for joint in joints.values()}
    for joint in joints.values():
        parent_to_joints[joint.parent_link].append(joint)
    for outgoing in parent_to_joints.values():
        outgoing.sort(key=lambda item: (item.parent_link, item.child_link, item.name))

    ordered_roots = [str(selected_root_link)] if str(selected_root_link or '').strip() else []
    for root in root_candidates or ():
        root_name = str(root)
        if root_name and root_name not in ordered_roots:
            ordered_roots.append(root_name)
    inferred_roots = sorted({name for name in links if name not in child_links} | ({joint.parent_link for joint in joints.values()} - child_links))
    for root in inferred_roots:
        if root not in ordered_roots:
            ordered_roots.append(root)
    if not ordered_roots and links:
        ordered_roots = [str(next(iter(sorted(links))))]

    ordered_links: list[str] = []
    ordered_edges: list[tuple[str, str]] = []
    dynamic_joint_names: list[str] = []
    fixed_joint_names: list[str] = []
    seen_links: set[str] = set()
    seen_joints: set[str] = set()

    def _visit(link_name: str) -> None:
        normalized = str(link_name or '')
        if not normalized or normalized in seen_links:
            return
        seen_links.add(normalized)
        ordered_links.append(normalized)
        for joint in parent_to_joints.get(normalized, ()):  # already deterministic
            if joint.name in seen_joints:
                continue
            seen_joints.add(joint.name)
            ordered_edges.append((str(joint.parent_link), str(joint.child_link)))
            if joint.is_dynamic:
                dynamic_joint_names.append(str(joint.name))
            else:
                fixed_joint_names.append(str(joint.name))
            _visit(joint.child_link)

    for root in ordered_roots:
        _visit(root)
    for link_name in sorted(links):
        _visit(link_name)

    branching_links = sorted(link_name for link_name, outgoing in parent_to_joints.items() if len(outgoing) > 1)
    semantic_family = 'articulated_tree_projection' if branching_links or len(ordered_roots) > 1 else 'articulated_serial_tree'
    return {
        'graph_contract_version': 'v1',
        'root_link': str(selected_root_link or ordered_roots[0] if ordered_roots else ''),
        'root_candidates': [str(root) for root in ordered_roots],
        'link_names': [str(link) for link in ordered_links],
        'edge_pairs': [[str(parent), str(child)] for parent, child in ordered_edges],
        'dynamic_joint_names': [str(name) for name in dynamic_joint_names],
        'fixed_joint_names': [str(name) for name in fixed_joint_names],
        'branching_link_names': [str(name) for name in branching_links],
        'dynamic_joint_count_total': int(len(dynamic_joint_names)),
        'fixed_joint_count_total': int(len(fixed_joint_names)),
        'supports_branched_tree_projection': True,
        'supports_branched_tree_execution': bool(not branching_links and len(ordered_roots) == 1),
        'supports_closed_loop_execution': False,
        'supports_mobile_base_execution': False,
        'semantic_family': semantic_family,
    }


def build_articulated_source_model(
    *,
    stem: str,
    joints: dict[str, ParsedJoint],
    graph_summary: dict[str, object],
    fidelity: str,
) -> ArticulatedRobotModel:
    """Build an articulated graph model from the complete parsed URDF joint tree.

    Args:
        stem: Robot identifier.
        joints: Parsed URDF joint table.
        graph_summary: Full graph summary emitted before serial adaptation.
        fidelity: Import fidelity label.

    Returns:
        ArticulatedRobotModel: Graph-first articulated model preserving imported dynamic topology.

    Raises:
        ValueError: Propagates inconsistent articulated-model invariants.

    Boundary behavior:
        Fixed joints remain represented in ``graph_edge_pairs`` metadata while the dynamic
        articulated joints preserve their nearest dynamic parent indices for runtime graph usage.
        Serial-only execution helpers on ``ArticulatedRobotModel`` still reject branched trees.
    """
    parent_to_joints: dict[str, list[ParsedJoint]] = defaultdict(list)
    for joint in joints.values():
        parent_to_joints[joint.parent_link].append(joint)
    for outgoing in parent_to_joints.values():
        outgoing.sort(key=lambda item: (item.parent_link, item.child_link, item.name))

    ordered_roots = tuple(str(item) for item in graph_summary.get('root_candidates', ()) or ())
    if not ordered_roots:
        root_link = str(graph_summary.get('root_link', '') or '')
        ordered_roots = (root_link,) if root_link else ()

    dynamic_models: list[ArticulatedJointModel] = []
    graph_edge_pairs = tuple(
        (str(parent), str(child))
        for parent, child in (tuple(pair) for pair in graph_summary.get('edge_pairs', ()) or ())
    )
    seen_links: set[str] = set()
    seen_joints: set[str] = set()

    def _visit(link_name: str, parent_dynamic_index: int | None) -> None:
        normalized_link = str(link_name or '')
        if not normalized_link:
            return
        seen_links.add(normalized_link)
        for joint in parent_to_joints.get(normalized_link, ()):  # deterministic
            if joint.name in seen_joints:
                continue
            seen_joints.add(joint.name)
            next_parent_index = parent_dynamic_index
            if joint.is_dynamic:
                dynamic_models.append(
                    ArticulatedJointModel(
                        name=str(joint.name),
                        parent_link=str(joint.parent_link),
                        child_link=str(joint.child_link),
                        joint_type=joint.joint_type,
                        axis=tuple(float(v) for v in np.asarray(joint.axis, dtype=float).reshape(3).tolist()),
                        origin_translation=tuple(float(v) for v in np.asarray(joint.origin_xyz, dtype=float).reshape(3).tolist()),
                        origin_rpy=tuple(float(v) for v in np.asarray(joint.origin_rpy, dtype=float).reshape(3).tolist()),
                        limit=joint.limit,
                        parent_index=parent_dynamic_index,
                        metadata={'source': 'urdf_model', 'raw_type': str(joint.raw_type), 'graph_preserved': True},
                    )
                )
                next_parent_index = len(dynamic_models) - 1
            _visit(joint.child_link, next_parent_index)

    for root_link in ordered_roots:
        _visit(root_link, None)

    link_names = tuple(str(item) for item in graph_summary.get('link_names', ()) or ())
    if not link_names:
        link_names = tuple(dict.fromkeys([str(graph_summary.get('root_link', '') or '')] + [joint.child_link for joint in dynamic_models if hasattr(joint, 'child_link')]))
    return ArticulatedRobotModel(
        name=str(stem),
        root_link=str(graph_summary.get('root_link', '') or (ordered_roots[0] if ordered_roots else 'world')),
        joint_models=tuple(dynamic_models),
        link_names=tuple(link_names),
        base_T=np.eye(4, dtype=float),
        tool_T=np.eye(4, dtype=float),
        home_q=np.zeros(len(dynamic_models), dtype=float),
        semantic_family=str(graph_summary.get('semantic_family', 'articulated_serial_tree') or 'articulated_serial_tree'),
        source_surface='urdf_source_graph',
        source_format='urdf',
        fidelity=str(fidelity or ''),
        metadata={
            'graph_contract_version': str(graph_summary.get('graph_contract_version', 'v1') or 'v1'),
            'graph_edge_pairs': [[str(parent), str(child)] for parent, child in graph_edge_pairs],
            'root_candidates': [str(item) for item in ordered_roots],
            'branching_link_names': [str(item) for item in graph_summary.get('branching_link_names', ()) or ()],
            'supports_branched_tree_projection': bool(graph_summary.get('supports_branched_tree_projection', True)),
            'dynamic_joint_count_total': int(graph_summary.get('dynamic_joint_count_total', len(dynamic_models)) or len(dynamic_models)),
            'fixed_joint_count_total': int(graph_summary.get('fixed_joint_count_total', 0) or 0),
            'graph_preserved': True,
        },
    )


def build_runtime_fidelity_contract(
    *,
    path: Path,
    root_link: str,
    chain: list[ParsedJoint],
    joint_table: dict[str, ParsedJoint],
    resolution: dict[str, object],
    graph_summary: dict[str, object],
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
    graph_edge_pairs = [list(pair) for pair in graph_summary.get('edge_pairs', ()) or ()]
    graph_link_names = [str(item) for item in graph_summary.get('link_names', ()) or ()]
    graph_dynamic_joint_names = [str(item) for item in graph_summary.get('dynamic_joint_names', ()) or ()]
    graph_branching_links = [str(item) for item in graph_summary.get('branching_link_names', ()) or ()]
    semantic_family = str(graph_summary.get('semantic_family', 'articulated_serial_tree') or 'articulated_serial_tree')
    execution_semantics = 'tree_active_path' if graph_branching_links else 'serial_tree'
    execution_scope = 'active_path_over_tree' if graph_branching_links else 'serial_tree'
    return {
        'contract_version': 'v4',
        'source_path': str(path),
        'source_family': 'urdf_tree',
        'runtime_family': semantic_family,
        'execution_surface': 'canonical_model',
        'execution_adapter': 'canonical_articulated_chain',
        'runtime_dispatch': {
            'primary_execution_surface': 'articulated_model',
            'primary_execution_adapter': 'canonical_articulated_chain',
            'execution_semantics': execution_semantics,
            'execution_scope': execution_scope,
        },
        'source_model_layer': {
            'surface': 'urdf_tree',
            'source_path': str(path),
            'selected_root_link': str(resolution.get('selected_root_link', root_link) or root_link),
            'candidate_root_links': list(resolution.get('root_candidates', ()) or ()),
        },
        'articulated_graph_layer': {
            'surface': 'articulated_model',
            'semantic_family': semantic_family,
            'root_link': str(graph_summary.get('root_link', root_link) or root_link),
            'graph_link_names': graph_link_names,
            'graph_edge_pairs': graph_edge_pairs,
            'graph_dynamic_joint_names': graph_dynamic_joint_names,
            'selected_joint_names': list(selected_joint_names),
            'branching_link_names': graph_branching_links,
            'supports_branched_tree_projection': bool(graph_summary.get('supports_branched_tree_projection', True)),
            'supports_branched_tree_execution': bool(graph_summary.get('supports_branched_tree_execution', False)),
            'supports_closed_loop_execution': False,
            'supports_mobile_base_execution': False,
        },
        'execution_adapter_layer': {
            'surface': 'serial_execution_rows',
            'adapter_id': 'canonical_articulated_chain',
            'selected_dynamic_joint_count': int(len(selected_joint_names)),
            'pruned_dynamic_joint_names': pruned_dynamic_joints,
            'adapter_scope': 'solver_kinematics_baseline',
            'execution_semantics': execution_semantics,
            'execution_scope': execution_scope,
            'supports_active_path_execution': True,
            'supports_full_tree_execution': False,
            'selected_tip_joint_name': '' if not selected_joint_names else str(selected_joint_names[-1]),
        },
        'kinematic_convention': KinematicConvention.DH_APPROXIMATE_FROM_URDF.value,
        'root_link': str(graph_summary.get('root_link', root_link) or root_link),
        'selected_root_link': str(resolution.get('selected_root_link', root_link) or root_link),
        'selected_joint_names': list(selected_joint_names),
        'pruned_dynamic_joint_names': pruned_dynamic_joints,
        'dynamic_joint_count_total': int(graph_summary.get('dynamic_joint_count_total', sum(1 for joint in joint_table.values() if joint.is_dynamic)) or 0),
        'selected_dynamic_joint_count': int(len(selected_joint_names)),
        'branched_tree_supported': bool(graph_summary.get('supports_branched_tree_projection', True)),
        'branched_tree_execution_mode': execution_scope,
        'closed_loop_supported': False,
        'mobile_base_supported': False,
        'has_visual': bool(has_visual),
        'has_collision': bool(has_collision),
        'fidelity': str(fidelity),
        'downgrade_records': [dict(item) for item in downgrade_records],
        'capability_badges': [
            'source_family:urdf_tree',
            f'runtime_family:{semantic_family}',
            'primary_execution_surface:articulated_model',
            'execution_surface:canonical_model',
            'execution_adapter:canonical_articulated_chain',
            'graph_preserved:full_source_tree',
            f'execution_scope:{execution_scope}',
            f'fidelity:{fidelity}',
        ],
    }


def build_downgrade_records(*, resolution: dict[str, object], graph_summary: dict[str, object], has_visual: bool, has_collision: bool) -> list[dict[str, object]]:
    """Build structured downgrade records for non-ideal URDF imports."""
    records: list[dict[str, object]] = []
    if bool(resolution.get('multiple_roots', False)):
        records.append({
            'kind': 'disconnected_roots',
            'severity': 'warning',
            'detail': 'multiple disconnected root candidates detected; strongest serial root selected while full graph metadata is preserved',
            'selected_root_link': str(resolution.get('selected_root_link', '') or ''),
            'candidate_root_links': list(resolution.get('root_candidates', ()) or ()),
        })
    for link_name in graph_summary.get('branching_link_names', ()) or ():
        records.append({
            'kind': 'branching_tree_serial_adapter_limit',
            'severity': 'warning',
            'detail': f'branching detected at link {link_name}; articulated graph is preserved, while the solver adapter still executes the strongest serial branch only',
            'link_name': str(link_name),
        })
    fixed_joint_count = int(resolution.get('fixed_joint_count', 0) or 0)
    if fixed_joint_count > 0:
        records.append({
            'kind': 'fixed_joints_collapsed',
            'severity': 'warning',
            'detail': 'fixed joints are preserved in the articulated graph metadata and collapsed only inside the serial solver adapter',
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
