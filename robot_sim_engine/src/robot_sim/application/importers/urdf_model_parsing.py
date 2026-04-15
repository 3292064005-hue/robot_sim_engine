from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import numpy as np

from robot_sim.domain.enums import JointType
from robot_sim.model.robot_geometry import GeometryPrimitive
from robot_sim.model.robot_links import RobotJointLimit


@dataclass(frozen=True)
class ParsedLink:
    """Structured URDF link payload extracted from the source tree.

    Attributes:
        name: URDF link name.
        has_visual: Whether supported visual primitives were recovered.
        has_collision: Whether supported collision primitives were recovered.
        inertial_mass: Optional inertial mass in kilograms.
        inertial_origin: Optional inertial origin xyz vector.
        visual_primitives: Supported visual geometry primitives.
        collision_primitives: Supported collision geometry primitives.
    """

    name: str
    has_visual: bool
    has_collision: bool
    inertial_mass: float | None
    inertial_origin: np.ndarray | None
    visual_primitives: tuple[GeometryPrimitive, ...]
    collision_primitives: tuple[GeometryPrimitive, ...]


@dataclass(frozen=True)
class ParsedJoint:
    """Structured URDF joint payload extracted from the source tree.

    Attributes:
        name: URDF joint name.
        parent_link: Parent link identifier.
        child_link: Child link identifier.
        joint_type: Normalized runtime joint type or ``None`` for fixed joints.
        axis: Joint axis vector.
        origin_xyz: Joint origin translation.
        origin_rpy: Joint origin Euler orientation.
        limit: Normalized joint limits.
        raw_type: Original URDF joint type string.
    """

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


SUPPORTED_URDF_PRIMITIVES = ('box', 'cylinder', 'sphere', 'mesh')
SUPPORTED_URDF_JOINT_TYPES = {'revolute', 'prismatic', 'continuous', 'fixed'}


def parse_xyz(text: str | None, *, default: np.ndarray | None = None) -> np.ndarray:
    """Parse a URDF xyz/rpy vector into a normalized numpy array.

    Args:
        text: Raw whitespace-delimited URDF vector string.
        default: Optional fallback vector used when ``text`` is empty.

    Returns:
        np.ndarray: A copied three-element float vector.

    Raises:
        ValueError: If ``text`` contains anything other than three numeric components.

    Boundary behavior:
        Empty or missing text falls back to ``default`` or a zero vector so callers can
        keep parser control flow deterministic across optional URDF tags.
    """
    if text is None or not str(text).strip():
        return np.asarray(default if default is not None else np.zeros(3, dtype=float), dtype=float).copy()
    values = [float(v) for v in str(text).split()]
    if len(values) != 3:
        raise ValueError(f'expected three URDF numeric components, got {values}')
    return np.asarray(values, dtype=float)


def extract_primitives(nodes: list[ET.Element]) -> tuple[GeometryPrimitive, ...]:
    """Extract supported URDF geometry primitives from visual/collision nodes.

    Args:
        nodes: URDF ``visual`` or ``collision`` elements.

    Returns:
        tuple[GeometryPrimitive, ...]: Supported primitive payloads in source order.

    Raises:
        None: Unsupported or malformed geometry nodes are skipped defensively.
    """
    primitives: list[GeometryPrimitive] = []
    for node in nodes:
        geometry = node.find('geometry')
        if geometry is None:
            continue
        for kind in SUPPORTED_URDF_PRIMITIVES:
            element = geometry.find(kind)
            if element is None:
                continue
            params: dict[str, object] = dict(element.attrib)
            primitives.append(GeometryPrimitive(kind=kind, params=params))
            break
    return tuple(primitives)


def parse_links(root: ET.Element) -> dict[str, ParsedLink]:
    """Parse URDF link declarations into canonical structured records.

    Args:
        root: Parsed URDF XML root element.

    Returns:
        dict[str, ParsedLink]: Link-name keyed structured link records.

    Raises:
        ValueError: Propagates malformed numeric inertial origins.
    """
    parsed: dict[str, ParsedLink] = {}
    for link in root.findall('link'):
        name = str(link.attrib.get('name', '')).strip()
        if not name:
            continue
        visual_primitives = extract_primitives(link.findall('visual'))
        collision_primitives = extract_primitives(link.findall('collision'))
        inertial = link.find('inertial')
        inertial_mass = None
        inertial_origin = None
        if inertial is not None:
            mass_tag = inertial.find('mass')
            if mass_tag is not None and mass_tag.attrib.get('value') is not None:
                inertial_mass = float(mass_tag.attrib['value'])
            origin_tag = inertial.find('origin')
            if origin_tag is not None:
                inertial_origin = parse_xyz(origin_tag.attrib.get('xyz'))
        parsed[name] = ParsedLink(
            name=name,
            has_visual=bool(visual_primitives),
            has_collision=bool(collision_primitives),
            inertial_mass=inertial_mass,
            inertial_origin=inertial_origin,
            visual_primitives=visual_primitives,
            collision_primitives=collision_primitives,
        )
    return parsed


def parse_joints(root: ET.Element) -> dict[str, ParsedJoint]:
    """Parse URDF joints into canonical structured records.

    Args:
        root: Parsed URDF XML root element.

    Returns:
        dict[str, ParsedJoint]: Joint-name keyed structured joint records.

    Raises:
        ValueError: Propagates malformed numeric xyz/rpy vectors.
    """
    parsed: dict[str, ParsedJoint] = {}
    for joint in root.findall('joint'):
        jtype_raw = str(joint.attrib.get('type', 'revolute')).strip()
        if jtype_raw not in SUPPORTED_URDF_JOINT_TYPES:
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
        xyz = parse_xyz(origin.attrib.get('xyz') if origin is not None else None)
        rpy = parse_xyz(origin.attrib.get('rpy') if origin is not None else None)
        axis = parse_xyz(axis_tag.attrib.get('xyz') if axis_tag is not None else None, default=np.array([0.0, 0.0, 1.0], dtype=float))
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
        parsed[joint_name] = ParsedJoint(
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
