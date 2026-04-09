from __future__ import annotations

from dataclasses import asdict, dataclass, field

from robot_sim.domain.enums import IKSolverMode


SUPPORTED_TRAJECTORY_VALIDATION_LAYERS: tuple[str, ...] = (
    'timing',
    'path_metrics',
    'goal_metrics',
    'collision',
    'limits',
)


@dataclass(frozen=True)
class IKConfig:
    """Typed inverse-kinematics runtime configuration."""

    mode: IKSolverMode = IKSolverMode.DLS
    max_iters: int = 150
    pos_tol: float = 1.0e-4
    ori_tol: float = 1.0e-4
    damping_lambda: float = 0.05
    step_scale: float = 0.5
    enable_nullspace: bool = True
    joint_limit_weight: float = 0.03
    manipulability_weight: float = 0.0
    position_only: bool = False
    orientation_weight: float = 1.0
    max_step_norm: float = 0.35
    singularity_cond_threshold: float = 250.0
    fallback_to_dls_when_singular: bool = True
    reachability_precheck: bool = True
    retry_count: int = 0
    random_seed: int = 7
    adaptive_damping: bool = True
    min_damping_lambda: float = 1.0e-4
    max_damping_lambda: float = 1.5
    use_weighted_least_squares: bool = True
    clamp_seed_to_joint_limits: bool = True
    normalize_target_rotation: bool = True
    allow_orientation_relaxation: bool = False
    orientation_relaxation_pos_multiplier: float = 5.0
    orientation_relaxation_ori_multiplier: float = 25.0
    timeout_ms: float = 0.0

    def __post_init__(self) -> None:
        numeric_bounds = {
            'max_iters': self.max_iters,
            'pos_tol': self.pos_tol,
            'ori_tol': self.ori_tol,
            'damping_lambda': self.damping_lambda,
            'step_scale': self.step_scale,
            'orientation_weight': self.orientation_weight,
            'max_step_norm': self.max_step_norm,
            'singularity_cond_threshold': self.singularity_cond_threshold,
            'retry_count': self.retry_count,
            'min_damping_lambda': self.min_damping_lambda,
            'max_damping_lambda': self.max_damping_lambda,
            'timeout_ms': self.timeout_ms,
        }
        for label, value in numeric_bounds.items():
            if float(value) < 0.0:
                raise ValueError(f'{label} must be >= 0')
        if int(self.max_iters) <= 0:
            raise ValueError('max_iters must be > 0')
        if float(self.min_damping_lambda) > float(self.max_damping_lambda):
            raise ValueError('min_damping_lambda cannot exceed max_damping_lambda')

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['mode'] = getattr(self.mode, 'value', str(self.mode))
        return payload


@dataclass(frozen=True)
class TrajectoryConfig:
    """Typed trajectory runtime configuration.

    Attributes:
        duration: Default planned trajectory duration in seconds.
        dt: Default trajectory sampling period in seconds.
        validation_layers: Default validation phases applied when callers do not
            explicitly override the trajectory validation contract.
    """

    duration: float = 3.0
    dt: float = 0.02
    validation_layers: tuple[str, ...] = SUPPORTED_TRAJECTORY_VALIDATION_LAYERS

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['validation_layers'] = list(self.validation_layers)
        return payload


@dataclass(frozen=True)
class SolverSettings:
    """Typed container grouping solver and trajectory configuration."""

    ik: IKConfig = field(default_factory=IKConfig)
    trajectory: TrajectoryConfig = field(default_factory=TrajectoryConfig)

    def as_dict(self) -> dict[str, object]:
        return {
            'ik': self.ik.as_dict(),
            'trajectory': self.trajectory.as_dict(),
        }
