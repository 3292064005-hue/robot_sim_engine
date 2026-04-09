from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.domain.enums import ReferenceFrame, TrajectoryMode
from robot_sim.domain.types import FloatArray
from robot_sim.model.ik_contracts import IKConstraintSummary, IKSeedPolicy, IKTaskMask
from robot_sim.model.planner_specs import WaypointPlannerSpec
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.waypoint_graph import WaypointGraph


@dataclass(frozen=True)
class FKRequest:
    """Forward-kinematics request at the application boundary."""

    spec: RobotSpec
    q: FloatArray


@dataclass(frozen=True)
class IKRequest:
    """Inverse-kinematics request at the application boundary.

    The first four fields keep the legacy constructor order used by workers,
    controllers, and tests. Additional contract fields extend the request
    without breaking the existing call sites.
    """

    spec: RobotSpec
    target: Pose
    q0: FloatArray
    config: IKConfig
    target_frame: ReferenceFrame | None = None
    position_mask: tuple[bool, bool, bool] = (True, True, True)
    orientation_mask: tuple[bool, bool, bool] = (True, True, True)
    seed_policy: IKSeedPolicy = IKSeedPolicy.PROVIDED
    secondary_objectives: tuple[str, ...] = ()
    timeout_ms: float | None = None
    allow_approximate_solution: bool = False
    constraint_summary: IKConstraintSummary | None = None
    request_metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.position_mask) != 3 or len(self.orientation_mask) != 3:
            raise ValueError('IKRequest masks must each have length 3')
        if self.timeout_ms is not None and float(self.timeout_ms) < 0.0:
            raise ValueError('IKRequest.timeout_ms must be >= 0 when provided')
        if self.target_frame is None:
            object.__setattr__(self, 'target_frame', self.target.frame)
        object.__setattr__(self, 'request_metadata', dict(self.request_metadata or {}))
        if self.constraint_summary is None:
            object.__setattr__(
                self,
                'constraint_summary',
                IKConstraintSummary(
                    target_frame=getattr(self.target_frame, 'value', str(self.target_frame)),
                    position_only=self.position_only,
                    orientation_weight=float(self.config.orientation_weight),
                    notes=tuple(self.secondary_objectives),
                ),
            )

    @property
    def task_mask(self) -> IKTaskMask:
        return IKTaskMask(position=tuple(bool(v) for v in self.position_mask), orientation=tuple(bool(v) for v in self.orientation_mask))

    @property
    def position_only(self) -> bool:
        return bool(self.config.position_only or not any(self.orientation_mask))


@dataclass(frozen=True)
class TrajectoryRequest:
    """Trajectory planning request at the application boundary."""

    q_start: FloatArray
    q_goal: FloatArray | None
    duration: float
    dt: float
    spec: RobotSpec | None = None
    mode: TrajectoryMode = TrajectoryMode.JOINT
    target_pose: Pose | None = None
    ik_config: IKConfig | None = None
    planner_id: str | None = None
    waypoint_graph: WaypointGraph | None = None
    max_velocity: float | None = None
    max_acceleration: float | None = None
    collision_obstacles: tuple[object, ...] = ()
    planning_scene: object | None = None
    validation_layers: tuple[str, ...] | None = None

    def to_waypoint_planner_spec(self) -> WaypointPlannerSpec:
        """Build a core-neutral waypoint planner spec from the request.

        Returns:
            Immutable waypoint planner specification.

        Raises:
            ValueError: If the robot specification or waypoint graph is missing.
        """
        if self.spec is None:
            raise ValueError('waypoint planner requires robot spec')
        if self.waypoint_graph is None:
            raise ValueError('waypoint planner requires waypoint_graph')
        return WaypointPlannerSpec(
            q_start=self.q_start,
            duration=float(self.duration),
            dt=float(self.dt),
            spec=self.spec,
            mode=self.mode,
            waypoint_graph=self.waypoint_graph,
            ik_config=self.ik_config,
            max_velocity=self.max_velocity,
            max_acceleration=self.max_acceleration,
        )
