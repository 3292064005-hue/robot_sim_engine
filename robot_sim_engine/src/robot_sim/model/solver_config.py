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
SUPPORTED_TRAJECTORY_STAGE_KINDS: tuple[str, ...] = ('planner', 'retime', 'validate', 'postprocessor')
SUPPORTED_STAGE_PROVIDER_STATUSES: tuple[str, ...] = ('stable', 'beta', 'experimental', 'internal', 'deprecated')
SUPPORTED_STAGE_PROVIDER_DEPLOYMENT_TIERS: tuple[str, ...] = ('production', 'experimental', 'fixture', 'compatibility')
SUPPORTED_TRAJECTORY_PLANNER_STAGES: tuple[str, ...] = ('default_planner',)
SUPPORTED_TRAJECTORY_RETIME_STAGES: tuple[str, ...] = ('builtin_scaling', 'no_retime')
SUPPORTED_TRAJECTORY_VALIDATE_STAGES: tuple[str, ...] = ('validate_trajectory', 'validate_goal_only')
SUPPORTED_TRAJECTORY_POSTPROCESSOR_STAGES: tuple[str, ...] = ('noop_postprocessor',)


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
    retry_count: int = 1
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
class TrajectoryStageCatalogEntry:
    """One externally declared trajectory stage provider.

    The catalog now models governance and runtime capability separately. ``stage_id`` remains the
    runtime stage selector referenced by pipelines, while ``provider_id`` identifies the declared
    provider surface used by policy/audit summaries.
    """

    stage_id: str
    kind: str
    factory: str
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
    provider_id: str = ''
    enabled_profiles: tuple[str, ...] = ()
    status: str = 'stable'
    deployment_tier: str = 'production'
    required_host_capabilities: tuple[str, ...] = ()
    optional_host_capabilities: tuple[str, ...] = ()
    fallback_stage_id: str = ''
    replace: bool = False

    def __post_init__(self) -> None:
        if not str(self.stage_id).strip():
            raise ValueError('TrajectoryStageCatalogEntry.stage_id must be a non-empty string')
        if str(self.kind).strip() not in SUPPORTED_TRAJECTORY_STAGE_KINDS:
            raise ValueError(
                f'TrajectoryStageCatalogEntry.kind must be one of {SUPPORTED_TRAJECTORY_STAGE_KINDS!r}'
            )
        if not str(self.factory).strip():
            raise ValueError('TrajectoryStageCatalogEntry.factory must be a non-empty string')
        if str(self.status).strip() not in SUPPORTED_STAGE_PROVIDER_STATUSES:
            raise ValueError(
                f'TrajectoryStageCatalogEntry.status must be one of {SUPPORTED_STAGE_PROVIDER_STATUSES!r}'
            )
        if str(self.deployment_tier).strip() not in SUPPORTED_STAGE_PROVIDER_DEPLOYMENT_TIERS:
            raise ValueError(
                'TrajectoryStageCatalogEntry.deployment_tier must be one of '
                f'{SUPPORTED_STAGE_PROVIDER_DEPLOYMENT_TIERS!r}'
            )
        object.__setattr__(self, 'provider_id', str(self.provider_id or self.stage_id).strip() or str(self.stage_id))
        object.__setattr__(self, 'aliases', tuple(str(item) for item in self.aliases if str(item).strip()))
        object.__setattr__(self, 'enabled_profiles', tuple(str(item) for item in self.enabled_profiles if str(item).strip()))
        object.__setattr__(self, 'required_host_capabilities', tuple(str(item) for item in self.required_host_capabilities if str(item).strip()))
        object.__setattr__(self, 'optional_host_capabilities', tuple(str(item) for item in self.optional_host_capabilities if str(item).strip()))
        object.__setattr__(self, 'fallback_stage_id', str(self.fallback_stage_id or '').strip())
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))

    def allows_profile(self, profile: str) -> bool:
        if not self.enabled_profiles:
            return True
        return str(profile) in set(self.enabled_profiles)

    def as_dict(self) -> dict[str, object]:
        return {
            'id': str(self.stage_id),
            'provider_id': str(self.provider_id),
            'kind': str(self.kind),
            'factory': str(self.factory),
            'aliases': list(self.aliases),
            'metadata': dict(self.metadata),
            'enabled_profiles': list(self.enabled_profiles),
            'status': str(self.status),
            'deployment_tier': str(self.deployment_tier),
            'required_host_capabilities': list(self.required_host_capabilities),
            'optional_host_capabilities': list(self.optional_host_capabilities),
            'fallback_stage_id': str(self.fallback_stage_id),
            'replace': bool(self.replace),
        }


@dataclass(frozen=True)
class TrajectoryPipelineConfig:
    """Typed definition for one named trajectory pipeline."""

    pipeline_id: str = 'default'
    planner_stage_id: str = 'default_planner'
    retime_stage_id: str = 'builtin_scaling'
    validate_stage_id: str = 'validate_trajectory'
    postprocessor_stage_ids: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(
        default_factory=lambda: {
            'path_stage': 'planner',
            'retimer_id': 'builtin_scaling',
            'validation_stage': 'validate_trajectory',
            'compatibility_surface': 'stable_default_pipeline',
        }
    )

    def __post_init__(self) -> None:
        if not str(self.pipeline_id).strip():
            raise ValueError('TrajectoryPipelineConfig.pipeline_id must be a non-empty string')
        if not str(self.planner_stage_id).strip():
            raise ValueError('TrajectoryPipelineConfig.planner_stage_id must be a non-empty string')
        if not str(self.retime_stage_id).strip():
            raise ValueError('TrajectoryPipelineConfig.retime_stage_id must be a non-empty string')
        if not str(self.validate_stage_id).strip():
            raise ValueError('TrajectoryPipelineConfig.validate_stage_id must be a non-empty string')
        object.__setattr__(self, 'postprocessor_stage_ids', tuple(str(item) for item in self.postprocessor_stage_ids if str(item).strip()))
        object.__setattr__(self, 'aliases', tuple(str(item) for item in self.aliases if str(item).strip()))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))

    def as_dict(self) -> dict[str, object]:
        return {
            'id': str(self.pipeline_id),
            'planner_stage': str(self.planner_stage_id),
            'retime_stage': str(self.retime_stage_id),
            'validate_stage': str(self.validate_stage_id),
            'postprocessors': list(self.postprocessor_stage_ids),
            'aliases': list(self.aliases),
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class TrajectoryConfig:
    """Typed trajectory runtime configuration."""

    duration: float = 3.0
    dt: float = 0.02
    validation_layers: tuple[str, ...] = SUPPORTED_TRAJECTORY_VALIDATION_LAYERS
    pipeline_id: str = 'default'
    pipelines: tuple[TrajectoryPipelineConfig, ...] = field(default_factory=lambda: (TrajectoryPipelineConfig(),))
    stage_catalog: tuple[TrajectoryStageCatalogEntry, ...] = ()

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['validation_layers'] = list(self.validation_layers)
        payload['pipelines'] = [item.as_dict() for item in self.pipelines]
        payload['stage_catalog'] = [item.as_dict() for item in self.stage_catalog]
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
