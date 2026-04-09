from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from robot_sim.domain.enums import ImporterFidelity, JointType, KinematicConvention
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_links import RobotJointLimit, RobotJointSpec
from robot_sim.model.robot_model_bundle import RobotModelBundle
from robot_sim.model.robot_spec import RobotSpec


class URDFSkeletonRobotImporter:
    """Approximate URDF importer.

    This importer intentionally extracts a DH-like serial skeleton from URDF
    joint origins. It is a bounded-fidelity fallback kept for compatibility when
    callers explicitly request the legacy skeleton-only semantics.
    """

    importer_id = 'urdf_skeleton'

    def capabilities(self) -> dict[str, object]:
        return {
            'source_format': 'urdf',
            'fidelity': ImporterFidelity.APPROXIMATE.value,
            'family': 'approximate_tree_import',
            'notes': 'Approximates a serial DH-like chain from URDF joint origins. Not a full URDF tree importer.',
        }

    def load(self, source, *, robot_name: str | None = None, **kwargs):
        path = Path(source)
        tree = ET.parse(path)
        root = tree.getroot()
        rows = []
        home_q = []
        structured_joints: list[RobotJointSpec] = []
        warnings: list[str] = [
            'Imported with urdf_skeleton fidelity: approximate DH-like serial chain only.',
        ]
        joint_names: list[str] = []
        joint_axes: list[tuple[float, float, float]] = []
        joint_limits: list[RobotJointLimit] = []
        for idx, joint in enumerate(root.findall('joint')):
            jtype = joint.attrib.get('type', 'revolute')
            if jtype not in {'revolute', 'prismatic', 'continuous'}:
                continue
            origin = joint.find('origin')
            axis_tag = joint.find('axis')
            xyz = [0.0, 0.0, 0.0]
            rpy = [0.0, 0.0, 0.0]
            if origin is not None:
                if origin.attrib.get('xyz'):
                    xyz = [float(v) for v in origin.attrib['xyz'].split()]
                if origin.attrib.get('rpy'):
                    rpy = [float(v) for v in origin.attrib['rpy'].split()]
            axis = np.array([0.0, 0.0, 1.0], dtype=float)
            if axis_tag is not None and axis_tag.attrib.get('xyz'):
                axis = np.array([float(v) for v in axis_tag.attrib['xyz'].split()], dtype=float)
            limit = joint.find('limit')
            lower = float(limit.attrib.get('lower', -math.pi)) if limit is not None else -math.pi
            upper = float(limit.attrib.get('upper', math.pi)) if limit is not None else math.pi
            if jtype == 'continuous':
                lower, upper = -math.pi, math.pi
            a = float((xyz[0] ** 2 + xyz[1] ** 2) ** 0.5)
            alpha = float(rpy[0])
            d = float(xyz[2])
            theta_offset = float(rpy[2])
            joint_type = JointType.PRISMATIC if jtype == 'prismatic' else JointType.REVOLUTE
            rows.append(
                DHRow(
                    a=a,
                    alpha=alpha,
                    d=d,
                    theta_offset=theta_offset,
                    joint_type=joint_type,
                    q_min=lower,
                    q_max=upper,
                )
            )
            joint_name = str(joint.attrib.get('name', f'joint_{idx}'))
            structured_joints.append(
                RobotJointSpec(
                    name=joint_name,
                    parent_link=str(joint.find('parent').attrib.get('link', '')) if joint.find('parent') is not None else '',
                    child_link=str(joint.find('child').attrib.get('link', '')) if joint.find('child') is not None else '',
                    joint_type=joint_type,
                    axis=axis,
                    limit=RobotJointLimit(lower=lower, upper=upper),
                    origin_translation=np.asarray(xyz, dtype=float),
                    origin_rpy=np.asarray(rpy, dtype=float),
                    metadata={'skeleton_only': True},
                )
            )
            joint_names.append(joint_name)
            joint_axes.append(tuple(float(v) for v in axis.tolist()))
            joint_limits.append(RobotJointLimit(lower=lower, upper=upper))
            home_q.append(0.0)
        if not rows:
            raise ValueError(f'no supported joints found in URDF: {path}')
        stem = robot_name or path.stem
        source_model_summary = {
            'source_format': 'urdf',
            'import_semantics': 'skeleton',
            'joint_count': len(rows),
            'link_count': len(rows) + 1,
            'has_visual': False,
            'has_collision': False,
        }
        spec = RobotSpec(
            name=stem,
            dh_rows=tuple(rows),
            base_T=np.eye(4),
            tool_T=np.eye(4),
            home_q=np.asarray(home_q, dtype=float),
            display_name=stem,
            metadata={
                'importer': 'urdf',
                'importer_impl': self.importer_id,
                'import_semantics': 'skeleton',
                'model_source': 'urdf_skeleton',
                'kinematic_convention': KinematicConvention.DH_APPROXIMATE_FROM_URDF.value,
                'geometry_available': False,
                'collision_model': 'none',
                'source': str(path),
                'warnings': list(warnings),
                'notes': 'URDF joint origins were collapsed into an approximate DH-like serial chain. This is suitable for demos/tests, not for general URDF fidelity.',
            },
            joint_names=tuple(joint_names),
            joint_types=tuple(joint.joint_type for joint in structured_joints),
            joint_axes=tuple(joint_axes),
            joint_limits=tuple(joint_limits),
            structured_joints=tuple(structured_joints),
            kinematic_source='urdf_skeleton',
            source_model_summary=source_model_summary,
        )
        return RobotModelBundle(
            spec=spec,
            geometry=RobotGeometry.simple_capsules(len(rows)),
            collision_geometry=RobotGeometry.simple_capsules(len(rows)),
            fidelity=ImporterFidelity.APPROXIMATE.value,
            warnings=tuple(warnings),
            source_path=str(path),
            importer_id=self.importer_id,
            metadata={'source_format': 'urdf', 'import_semantics': 'skeleton'},
            source_model_summary=source_model_summary,
        )


URDFRobotImporter = URDFSkeletonRobotImporter
