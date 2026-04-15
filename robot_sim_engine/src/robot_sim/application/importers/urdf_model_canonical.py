from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robot_sim.model.canonical_robot_model import CanonicalRobotModel
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec, RobotLinkSpec

from robot_sim.application.importers.urdf_model_parsing import ParsedJoint, ParsedLink


@dataclass(frozen=True)
class CanonicalSerialAssembly:
    rows: tuple[DHRow, ...]
    structured_joints: tuple[RobotJointSpec, ...]
    selected_links: tuple[RobotLinkSpec, ...]
    joint_axes: tuple[tuple[float, float, float], ...]
    joint_limits: tuple[RobotJointLimit, ...]
    home_q: tuple[float, ...]
    link_names: tuple[str, ...]
    joint_names: tuple[str, ...]
    canonical_model: CanonicalRobotModel


def build_canonical_serial_model(
    *,
    path: Path,
    importer_id: str,
    stem: str,
    chain: list[ParsedJoint],
    link_table: dict[str, ParsedLink],
    root_link: str,
    fidelity: str,
    warnings: list[str],
    fidelity_contract: dict[str, object],
    downgrade_records: list[dict[str, object]],
) -> CanonicalSerialAssembly:
    """Build the canonical serial-model intermediate layer for URDF import.

    Args:
        path: URDF source path.
        importer_id: Importer identifier.
        stem: Target robot identifier.
        chain: Selected dynamic serial chain.
        link_table: Parsed URDF link table.
        root_link: Resolved root link for the selected chain.
        fidelity: Selected importer fidelity label.
        warnings: Structured warning list.
        fidelity_contract: Runtime fidelity contract summary.
        downgrade_records: Structured downgrade records.

    Returns:
        CanonicalSerialAssembly: Canonical intermediate structures consumed by RobotSpec
            and the runtime adapter.

    Raises:
        ValueError: Propagates from ``CanonicalRobotModel`` if the assembled source graph is inconsistent.
    """
    rows: list[DHRow] = []
    structured_joints: list[RobotJointSpec] = []
    selected_links: list[RobotLinkSpec] = []
    joint_axes: list[tuple[float, float, float]] = []
    joint_limits: list[RobotJointLimit] = []
    home_q: list[float] = []
    link_names: list[str] = []
    joint_names: list[str] = []
    used_link_names: set[str] = set()

    for idx, joint in enumerate(chain):
        origin = joint.origin_xyz
        rpy = joint.origin_rpy
        rows.append(
            DHRow(
                a=float((origin[0] ** 2 + origin[1] ** 2) ** 0.5),
                alpha=float(rpy[0]),
                d=float(origin[2]),
                theta_offset=float(rpy[2]),
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
            'importer_id': importer_id,
            'warnings': list(dict.fromkeys(warnings)),
            'source_path': str(path),
            'runtime_fidelity_contract': dict(fidelity_contract),
            'downgrade_records': list(downgrade_records),
            'canonical_model_contract_version': 'v1',
            'canonical_model_layer': 'urdf_serial_intermediate',
        },
    )
    return CanonicalSerialAssembly(
        rows=tuple(rows),
        structured_joints=tuple(structured_joints),
        selected_links=tuple(selected_links),
        joint_axes=tuple(joint_axes),
        joint_limits=tuple(joint_limits),
        home_q=tuple(home_q),
        link_names=tuple(link_names),
        joint_names=tuple(joint_names),
        canonical_model=canonical_model,
    )
