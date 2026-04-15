from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from robot_sim.domain.enums import ModuleStatus, PlannerFamily, TrajectoryMode


@dataclass(frozen=True)
class PlannerCapabilityDescriptor:
    """Stable descriptor for one registered planner capability."""

    planner_id: str
    label: str
    trajectory_mode: str
    family: str
    goal_source: str
    default_enabled: bool = True
    ui_visible: bool = True
    ui_label: str = ''
    status: str = ModuleStatus.STABLE.value
    metadata: dict[str, object] = field(default_factory=dict)

    def as_metadata(self) -> dict[str, object]:
        payload = {
            'planner_id': self.planner_id,
            'planner_label': self.label,
            'trajectory_mode': self.trajectory_mode,
            'family': self.family,
            'goal_source': self.goal_source,
            'default_enabled': bool(self.default_enabled),
            'ui_visible': bool(self.ui_visible),
            'ui_label': self.ui_label or self.trajectory_mode,
            'status': self.status,
        }
        payload.update(dict(self.metadata or {}))
        return payload


_DEFAULT_PLANNER_CAPABILITIES: tuple[PlannerCapabilityDescriptor, ...] = (
    PlannerCapabilityDescriptor(
        planner_id='joint_quintic',
        label='Joint quintic planner',
        trajectory_mode=TrajectoryMode.JOINT.value,
        family=PlannerFamily.JOINT.value,
        goal_source='joint_space',
        default_enabled=True,
        ui_visible=True,
        ui_label=TrajectoryMode.JOINT.value,
        metadata={'requires_ik': False, 'retiming': 'builtin_scaling', 'stable_surface': True},
    ),
    PlannerCapabilityDescriptor(
        planner_id='cartesian_sampled',
        label='Cartesian sampled planner',
        trajectory_mode=TrajectoryMode.CARTESIAN.value,
        family=PlannerFamily.CARTESIAN.value,
        goal_source='cartesian_pose',
        default_enabled=True,
        ui_visible=True,
        ui_label=TrajectoryMode.CARTESIAN.value,
        metadata={'requires_ik': True, 'retiming': 'builtin_scaling', 'stable_surface': True},
    ),
    PlannerCapabilityDescriptor(
        planner_id='joint_trapezoidal',
        label='Joint trapezoidal planner',
        trajectory_mode=TrajectoryMode.JOINT.value,
        family=PlannerFamily.JOINT.value,
        goal_source='joint_space',
        default_enabled=False,
        ui_visible=False,
        ui_label=TrajectoryMode.JOINT.value,
        status=ModuleStatus.BETA.value,
        metadata={'requires_ik': False, 'retiming': 'planner_native', 'stable_surface': False, 'exposure_reason': 'hidden_until_promoted'},
    ),
    PlannerCapabilityDescriptor(
        planner_id='waypoint_graph',
        label='Waypoint graph planner',
        trajectory_mode='waypoint_graph',
        family=PlannerFamily.WAYPOINT_GRAPH.value,
        goal_source='waypoint_graph',
        default_enabled=False,
        ui_visible=False,
        ui_label='waypoint_graph',
        status=ModuleStatus.EXPERIMENTAL.value,
        metadata={'requires_ik': True, 'retiming': 'builtin_scaling', 'stable_surface': False, 'exposure_reason': 'profile_gated'},
    ),
)


def planner_capability_descriptors() -> tuple[PlannerCapabilityDescriptor, ...]:
    return _DEFAULT_PLANNER_CAPABILITIES


def planner_capability_map() -> dict[str, PlannerCapabilityDescriptor]:
    return {descriptor.planner_id: descriptor for descriptor in planner_capability_descriptors()}


def planner_descriptor_for_id(planner_id: str | None) -> PlannerCapabilityDescriptor | None:
    return planner_capability_map().get(str(planner_id or '').strip())


def planner_mode_options(*, include_hidden: bool = False) -> tuple[str, ...]:
    options: list[str] = []
    for descriptor in planner_capability_descriptors():
        if not include_hidden and not descriptor.ui_visible:
            continue
        mode = str(descriptor.ui_label or descriptor.trajectory_mode)
        if mode not in options:
            options.append(mode)
    return tuple(options)


def resolve_default_planner_id(mode: str | TrajectoryMode | None, *, waypoint_graph_present: bool = False) -> str:
    if waypoint_graph_present:
        return 'waypoint_graph'
    normalized_mode = getattr(mode, 'value', mode)
    normalized_mode = str(normalized_mode or TrajectoryMode.JOINT.value)
    for descriptor in planner_capability_descriptors():
        if descriptor.trajectory_mode == normalized_mode and descriptor.default_enabled:
            return descriptor.planner_id
    for descriptor in planner_capability_descriptors():
        if descriptor.trajectory_mode == normalized_mode:
            return descriptor.planner_id
    raise ValueError(f'unknown trajectory mode: {normalized_mode}')


def planner_descriptor_snapshot(descriptors: Iterable[PlannerCapabilityDescriptor] | None = None) -> dict[str, dict[str, object]]:
    snapshot: dict[str, dict[str, object]] = {}
    for descriptor in descriptors or planner_capability_descriptors():
        snapshot[descriptor.planner_id] = descriptor.as_metadata()
    return snapshot
