from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import import_module
from typing import Protocol

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.planner_capabilities import resolve_default_planner_id
from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.core.trajectory.retiming import retime_trajectory
from robot_sim.model.solver_config import TrajectoryPipelineConfig, TrajectoryStageCatalogEntry
from robot_sim.model.trajectory import JointTrajectory


class TrajectoryPlannerStage(Protocol):
    stage_id: str

    def resolve_planner_id(self, req: TrajectoryRequest) -> str: ...

    def run(self, req: TrajectoryRequest, planner_registry) -> tuple[str, JointTrajectory]: ...


class TrajectoryRetimeStage(Protocol):
    stage_id: str

    def run(self, req: TrajectoryRequest, trajectory: JointTrajectory) -> JointTrajectory: ...


class TrajectoryValidateStage(Protocol):
    stage_id: str

    def run(self, req: TrajectoryRequest, trajectory: JointTrajectory, validate_uc: ValidateTrajectoryUseCase) -> object: ...


class TrajectoryPostprocessorStage(Protocol):
    stage_id: str

    def run(self, req: TrajectoryRequest, trajectory: JointTrajectory, diagnostics: object) -> JointTrajectory: ...


class DefaultPlannerStage:
    """Planner stage that resolves the runtime planner id from the request surface."""

    stage_id = 'default_planner'

    def resolve_planner_id(self, req: TrajectoryRequest) -> str:
        if req.planner_id:
            return str(req.planner_id)
        return resolve_default_planner_id(req.mode, waypoint_graph_present=req.waypoint_graph is not None)

    def run(self, req: TrajectoryRequest, planner_registry) -> tuple[str, JointTrajectory]:
        planner_id = self.resolve_planner_id(req)
        planner = planner_registry.get(planner_id)
        return planner_id, planner.plan(req)


class BuiltinRetimeStage:
    """Stable retiming stage backed by the repository-built scaling retimer."""

    stage_id = 'builtin_scaling'

    def run(self, req: TrajectoryRequest, trajectory: JointTrajectory) -> JointTrajectory:
        return retime_trajectory(trajectory, max_velocity=req.max_velocity, max_acceleration=req.max_acceleration)


class NoopRetimeStage:
    """Compatibility retime stage that preserves the planner trajectory unchanged."""

    stage_id = 'no_retime'

    def run(self, req: TrajectoryRequest, trajectory: JointTrajectory) -> JointTrajectory:
        return trajectory


class ValidateTrajectoryStage:
    """Validation stage that respects request validation layers."""

    stage_id = 'validate_trajectory'

    def __init__(self, *, layer_override: tuple[str, ...] | None = None, stage_id: str | None = None) -> None:
        self._layer_override = None if layer_override in (None, (), []) else tuple(str(item) for item in layer_override)
        if stage_id is not None:
            self.stage_id = str(stage_id)

    def run(self, req: TrajectoryRequest, trajectory: JointTrajectory, validate_uc: ValidateTrajectoryUseCase) -> object:
        validation_layers = self._layer_override if self._layer_override is not None else req.validation_layers
        return validate_uc.execute(
            trajectory,
            target_pose=req.target_pose,
            spec=req.spec,
            q_goal=req.q_goal,
            planning_scene=req.planning_scene,
            validation_layers=validation_layers,
        )


class NoopPostprocessorStage:
    """Postprocessor hook that preserves the final trajectory unchanged."""

    stage_id = 'noop_postprocessor'

    def run(self, req: TrajectoryRequest, trajectory: JointTrajectory, diagnostics: object) -> JointTrajectory:
        return trajectory


@dataclass(frozen=True)
class TrajectoryPipelineDefinition:
    pipeline_id: str
    planner_stage: TrajectoryPlannerStage
    retime_stage: TrajectoryRetimeStage
    validate_stage: TrajectoryValidateStage
    postprocessors: tuple[TrajectoryPostprocessorStage, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


class TrajectoryPipelineRegistry:
    """Registry of named trajectory pipelines."""

    def __init__(self) -> None:
        self._pipelines: dict[str, TrajectoryPipelineDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, pipeline: TrajectoryPipelineDefinition, *, aliases: tuple[str, ...] = ()) -> None:
        pipeline_id = str(pipeline.pipeline_id)
        if pipeline_id in self._pipelines:
            raise ValueError(f'duplicate trajectory pipeline id: {pipeline_id}')
        self._pipelines[pipeline_id] = pipeline
        for alias in aliases:
            normalized = str(alias)
            if normalized == pipeline_id:
                continue
            if normalized in self._aliases and self._aliases[normalized] != pipeline_id:
                raise ValueError(f'duplicate trajectory pipeline alias: {normalized}')
            self._aliases[normalized] = pipeline_id

    def get(self, pipeline_id: str) -> TrajectoryPipelineDefinition:
        canonical = self.resolve_id(pipeline_id)
        if canonical not in self._pipelines:
            raise KeyError(f'unknown trajectory pipeline: {pipeline_id}')
        return self._pipelines[canonical]

    def resolve_id(self, pipeline_id: str) -> str:
        return self._aliases.get(str(pipeline_id), str(pipeline_id))

    def ids(self) -> list[str]:
        return sorted(self._pipelines)


@dataclass(frozen=True)
class StageRegistryBundle:
    planner_stages: dict[str, TrajectoryPlannerStage]
    retime_stages: dict[str, TrajectoryRetimeStage]
    validate_stages: dict[str, TrajectoryValidateStage]
    postprocessor_stages: dict[str, TrajectoryPostprocessorStage]
    provider_catalog: tuple[dict[str, object], ...] = ()


def _resolve_stage_factory(factory_path: str):
    module_name, _, attr_name = str(factory_path).partition(':')
    if not module_name or not attr_name:
        raise ValueError(f'invalid trajectory stage factory path: {factory_path}')
    module = import_module(module_name)
    factory = getattr(module, attr_name)
    if not callable(factory):
        raise TypeError(f'trajectory stage factory is not callable: {factory_path}')
    return factory


def _materialize_stage(entry: TrajectoryStageCatalogEntry):
    factory = _resolve_stage_factory(entry.factory)
    signature = inspect.signature(factory)
    accepted_context: dict[str, object] = {}
    for parameter_name, parameter in signature.parameters.items():
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.POSITIONAL_ONLY):
            raise TypeError(
                'trajectory stage factories must use keyword-only or keyword-compatible parameters; '
                f'unsupported parameter {parameter_name!r} in {entry.factory}'
            )
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            accepted_context = {
                'stage_id': str(entry.stage_id),
                'provider_id': str(entry.provider_id),
                'kind': str(entry.kind),
                'metadata': dict(entry.metadata),
                'fallback_stage_id': str(entry.fallback_stage_id),
                'deployment_tier': str(entry.deployment_tier),
                'status': str(entry.status),
            }
            break
        if parameter_name == 'stage_id':
            accepted_context['stage_id'] = str(entry.stage_id)
        elif parameter_name == 'provider_id':
            accepted_context['provider_id'] = str(entry.provider_id)
        elif parameter_name == 'kind':
            accepted_context['kind'] = str(entry.kind)
        elif parameter_name == 'metadata':
            accepted_context['metadata'] = dict(entry.metadata)
        elif parameter_name == 'fallback_stage_id':
            accepted_context['fallback_stage_id'] = str(entry.fallback_stage_id)
        elif parameter_name == 'deployment_tier':
            accepted_context['deployment_tier'] = str(entry.deployment_tier)
        elif parameter_name == 'status':
            accepted_context['status'] = str(entry.status)
    stage = factory(**accepted_context)
    if stage is None:
        raise TypeError(f'trajectory stage factory returned None: {entry.factory}')
    return stage


def _register_stage_aliases(
    registry: dict[str, object],
    *,
    stage_id: str,
    aliases: Sequence[str],
    stage: object,
    replace: bool = False,
) -> None:
    normalized_stage_id = str(stage_id)
    if normalized_stage_id in registry and registry[normalized_stage_id] is not stage and not replace:
        raise ValueError(f'duplicate trajectory stage id: {normalized_stage_id}')
    registry[normalized_stage_id] = stage
    for alias in aliases:
        normalized_alias = str(alias)
        if not normalized_alias or normalized_alias == normalized_stage_id:
            continue
        if normalized_alias in registry and registry[normalized_alias] is not stage and not replace:
            raise ValueError(f'duplicate trajectory stage alias: {normalized_alias}')
        registry[normalized_alias] = stage


def _normalize_stage_entry(item: TrajectoryStageCatalogEntry | Mapping[str, object]) -> TrajectoryStageCatalogEntry:
    if isinstance(item, TrajectoryStageCatalogEntry):
        return item
    payload = dict(item or {})
    return TrajectoryStageCatalogEntry(
        stage_id=str(payload.get('id', payload.get('stage_id', '')) or ''),
        provider_id=str(payload.get('provider_id', payload.get('id', payload.get('stage_id', ''))) or ''),
        kind=str(payload.get('kind', '') or ''),
        factory=str(payload.get('factory', '') or ''),
        aliases=tuple(payload.get('aliases', ()) or ()),
        metadata=dict(payload.get('metadata', {}) or {}),
        enabled_profiles=tuple(payload.get('enabled_profiles', ()) or ()),
        status=str(payload.get('status', 'stable') or 'stable'),
        deployment_tier=str(payload.get('deployment_tier', 'production') or 'production'),
        required_host_capabilities=tuple(payload.get('required_host_capabilities', ()) or ()),
        optional_host_capabilities=tuple(payload.get('optional_host_capabilities', ()) or ()),
        fallback_stage_id=str(payload.get('fallback_stage_id', '') or ''),
        replace=bool(payload.get('replace', False)),
    )


def _stage_provider_decision(entry: TrajectoryStageCatalogEntry, policy) -> tuple[bool, str, tuple[str, ...], tuple[str, ...]]:
    active_profile = str(getattr(policy, 'active_profile', 'default') or 'default')
    if not entry.allows_profile(active_profile):
        return False, 'profile_disabled', (), ()
    status_allowlist = tuple(str(item) for item in getattr(policy, 'plugin_status_allowlist', ('stable', 'deprecated')) or ())
    if str(entry.status) not in set(status_allowlist):
        return False, 'status_disabled', (), ()
    host_capabilities = tuple(str(item) for item in getattr(policy, 'host_capabilities', ()) or ())
    host_cap_set = set(host_capabilities)
    if any(capability not in host_cap_set for capability in entry.required_host_capabilities):
        return False, 'required_host_capability_missing', (), ()
    negotiated = tuple(
        capability
        for capability in (*entry.required_host_capabilities, *entry.optional_host_capabilities)
        if capability in host_cap_set
    )
    missing_optional = tuple(
        capability for capability in entry.optional_host_capabilities if capability not in host_cap_set
    )
    return True, 'enabled', negotiated, missing_optional


def _provider_row(
    *,
    entry: TrajectoryStageCatalogEntry,
    enabled: bool,
    reason: str,
    negotiated: tuple[str, ...],
    missing_optional: tuple[str, ...],
    source: str,
) -> dict[str, object]:
    return {
        'provider_id': str(entry.provider_id),
        'id': str(entry.stage_id),
        'stage_id': str(entry.stage_id),
        'kind': str(entry.kind),
        'aliases': list(entry.aliases),
        'enabled': bool(enabled),
        'reason': str(reason),
        'status': str(entry.status),
        'deployment_tier': str(entry.deployment_tier),
        'enabled_profiles': list(entry.enabled_profiles),
        'required_host_capabilities': list(entry.required_host_capabilities),
        'optional_host_capabilities': list(entry.optional_host_capabilities),
        'negotiated_host_capabilities': list(negotiated),
        'missing_optional_host_capabilities': list(missing_optional),
        'fallback_stage_id': str(entry.fallback_stage_id),
        'replace': bool(entry.replace),
        'source': str(source),
        'metadata': dict(entry.metadata),
        'is_capability_provider': bool(enabled),
        'stage_provider_surface_version': 'v1',
    }


def _install_declared_stage(bundle: StageRegistryBundle, entry: TrajectoryStageCatalogEntry) -> None:
    stage = _materialize_stage(entry)
    actual_stage_id = str(getattr(stage, 'stage_id', '') or entry.stage_id)
    if str(actual_stage_id) != str(entry.stage_id):
        try:
            setattr(stage, 'stage_id', str(entry.stage_id))
        except (AttributeError, TypeError):
            actual_stage_id = str(entry.stage_id)
        else:
            actual_stage_id = str(entry.stage_id)
    if str(entry.kind) == 'planner':
        if not hasattr(stage, 'resolve_planner_id') or not hasattr(stage, 'run'):
            raise TypeError(f'trajectory planner stage must provide resolve_planner_id() and run(): {entry.factory}')
        _register_stage_aliases(bundle.planner_stages, stage_id=actual_stage_id, aliases=entry.aliases, stage=stage, replace=entry.replace)
    elif str(entry.kind) == 'retime':
        if not hasattr(stage, 'run'):
            raise TypeError(f'trajectory retime stage must provide run(): {entry.factory}')
        _register_stage_aliases(bundle.retime_stages, stage_id=actual_stage_id, aliases=entry.aliases, stage=stage, replace=entry.replace)
    elif str(entry.kind) == 'validate':
        if not hasattr(stage, 'run'):
            raise TypeError(f'trajectory validate stage must provide run(): {entry.factory}')
        _register_stage_aliases(bundle.validate_stages, stage_id=actual_stage_id, aliases=entry.aliases, stage=stage, replace=entry.replace)
    elif str(entry.kind) == 'postprocessor':
        if not hasattr(stage, 'run'):
            raise TypeError(f'trajectory postprocessor stage must provide run(): {entry.factory}')
        _register_stage_aliases(bundle.postprocessor_stages, stage_id=actual_stage_id, aliases=entry.aliases, stage=stage, replace=entry.replace)
    else:  # pragma: no cover - guarded by typed config validation
        raise ValueError(f'unsupported trajectory stage kind: {entry.kind}')


def build_stage_registry_bundle(
    stage_catalog: Sequence[TrajectoryStageCatalogEntry | Mapping[str, object]] | None = None,
    *,
    runtime_feature_policy=None,
) -> StageRegistryBundle:
    """Build the runtime stage catalog resolved by config-backed pipeline definitions.

    Args:
        stage_catalog: Optional typed or mapping-based declarations for externally provided stage
            implementations. Factories must return concrete stage objects compatible with the
            declared ``kind`` and may accept ``stage_id``, ``provider_id``, ``kind``, and
            ``metadata`` keyword arguments.
        runtime_feature_policy: Optional profile/capability policy controlling which external
            stage providers are enabled.

    Returns:
        StageRegistryBundle: Built-in stages plus any externally declared providers.

    Raises:
        ValueError: If duplicate ids/aliases are declared or a factory path is invalid.
        TypeError: If a factory does not return a stage compatible with the declared kind.
    """
    builtins = (
        TrajectoryStageCatalogEntry(stage_id='default_planner', provider_id='builtin.default_planner', kind='planner', factory='builtin:default_planner'),
        TrajectoryStageCatalogEntry(stage_id='builtin_scaling', provider_id='builtin.builtin_scaling', kind='retime', factory='builtin:builtin_scaling'),
        TrajectoryStageCatalogEntry(stage_id='no_retime', provider_id='builtin.no_retime', kind='retime', factory='builtin:no_retime'),
        TrajectoryStageCatalogEntry(stage_id='validate_trajectory', provider_id='builtin.validate_trajectory', kind='validate', factory='builtin:validate_trajectory'),
        TrajectoryStageCatalogEntry(stage_id='validate_goal_only', provider_id='builtin.validate_goal_only', kind='validate', factory='builtin:validate_goal_only'),
        TrajectoryStageCatalogEntry(stage_id='noop_postprocessor', provider_id='builtin.noop_postprocessor', kind='postprocessor', factory='builtin:noop_postprocessor'),
    )
    provider_catalog: list[dict[str, object]] = [
        _provider_row(entry=entry, enabled=True, reason='builtin', negotiated=(), missing_optional=(), source='builtin')
        for entry in builtins
    ]
    bundle = StageRegistryBundle(
        planner_stages={
            'default_planner': DefaultPlannerStage(),
        },
        retime_stages={
            'builtin_scaling': BuiltinRetimeStage(),
            'no_retime': NoopRetimeStage(),
        },
        validate_stages={
            'validate_trajectory': ValidateTrajectoryStage(),
            'validate_goal_only': ValidateTrajectoryStage(layer_override=('timing', 'goal_metrics'), stage_id='validate_goal_only'),
        },
        postprocessor_stages={
            'noop_postprocessor': NoopPostprocessorStage(),
        },
        provider_catalog=(),
    )
    policy = runtime_feature_policy
    for item in tuple(stage_catalog or ()):
        entry = _normalize_stage_entry(item)
        enabled, reason, negotiated, missing_optional = _stage_provider_decision(entry, policy)
        provider_catalog.append(
            _provider_row(
                entry=entry,
                enabled=enabled,
                reason=reason,
                negotiated=negotiated,
                missing_optional=missing_optional,
                source='declared_stage_catalog',
            )
        )
        if not enabled:
            continue
        _install_declared_stage(bundle, entry)
    return StageRegistryBundle(
        planner_stages=bundle.planner_stages,
        retime_stages=bundle.retime_stages,
        validate_stages=bundle.validate_stages,
        postprocessor_stages=bundle.postprocessor_stages,
        provider_catalog=tuple(provider_catalog),
    )


def default_pipeline_configs() -> tuple[TrajectoryPipelineConfig, ...]:
    """Return the shipped canonical pipeline bootstrap definitions."""
    return (
        TrajectoryPipelineConfig(
            aliases=('legacy_default_pipeline',),
            metadata={
                'path_stage': 'planner',
                'retimer_id': 'builtin_scaling',
                'validation_stage': 'validate_trajectory',
                'compatibility_surface': 'stable_default_pipeline',
            },
        ),
    )


def _resolve_config_payload(config: TrajectoryPipelineConfig | Mapping[str, object]) -> TrajectoryPipelineConfig:
    if isinstance(config, TrajectoryPipelineConfig):
        return config
    payload = dict(config or {})
    return TrajectoryPipelineConfig(
        pipeline_id=str(payload.get('id', payload.get('pipeline_id', 'default')) or 'default'),
        planner_stage_id=str(payload.get('planner_stage', payload.get('planner_stage_id', 'default_planner')) or 'default_planner'),
        retime_stage_id=str(payload.get('retime_stage', payload.get('retime_stage_id', 'builtin_scaling')) or 'builtin_scaling'),
        validate_stage_id=str(payload.get('validate_stage', payload.get('validate_stage_id', 'validate_trajectory')) or 'validate_trajectory'),
        postprocessor_stage_ids=tuple(payload.get('postprocessors', payload.get('postprocessor_stage_ids', ())) or ()),
        aliases=tuple(payload.get('aliases', ()) or ()),
        metadata=dict(payload.get('metadata', {}) or {}),
    )


def _provider_index(bundle: StageRegistryBundle) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    for row in bundle.provider_catalog:
        stage_id = str(row.get('stage_id', row.get('id', '')) or '')
        provider_id = str(row.get('provider_id', '') or '')
        if stage_id:
            index.setdefault(stage_id, row)
        if provider_id:
            index.setdefault(provider_id, row)
        for alias in row.get('aliases', ()) or ():
            alias_key = str(alias or '').strip()
            if alias_key:
                index.setdefault(alias_key, row)
    return index


def _resolve_stage_reference(
    registry: Mapping[str, object],
    *,
    stage_id: str,
    kind: str,
    bundle: StageRegistryBundle,
) -> tuple[object, str, dict[str, object] | None]:
    normalized_stage_id = str(stage_id)
    if normalized_stage_id in registry:
        return registry[normalized_stage_id], normalized_stage_id, None
    row = _provider_index(bundle).get(normalized_stage_id)
    fallback_stage_id = '' if row is None else str(row.get('fallback_stage_id', '') or '')
    if fallback_stage_id and fallback_stage_id in registry:
        return registry[fallback_stage_id], fallback_stage_id, row
    raise KeyError(f'unknown trajectory {kind} stage: {normalized_stage_id}')


def _stage_provider_summary(bundle: StageRegistryBundle) -> dict[str, object]:
    rows = list(bundle.provider_catalog)
    return {
        'surface_version': 'v1',
        'declared_provider_count': int(len(rows)),
        'enabled_provider_count': int(sum(1 for row in rows if bool(row.get('enabled', False)))),
        'disabled_provider_count': int(sum(1 for row in rows if not bool(row.get('enabled', False)))),
        'providers': [dict(row) for row in rows],
    }


def build_trajectory_pipeline_registry(
    pipeline_configs: Sequence[TrajectoryPipelineConfig | Mapping[str, object]] | None = None,
    *,
    stage_catalog: Sequence[TrajectoryStageCatalogEntry | Mapping[str, object]] | None = None,
    stage_registry_bundle: StageRegistryBundle | None = None,
    runtime_feature_policy=None,
) -> TrajectoryPipelineRegistry:
    """Resolve config-backed named pipelines into the runtime registry.

    Args:
        pipeline_configs: Optional typed/config mapping sequence loaded from profiles or local
            overrides. When omitted the shipped default pipeline set is installed.
        stage_catalog: Optional externally declared stage providers resolved before pipeline ids
            are bound. Ignored when ``stage_registry_bundle`` is supplied explicitly.
        stage_registry_bundle: Optional explicit stage catalog used by tests or alternate hosts.
        runtime_feature_policy: Optional profile/capability policy controlling stage-provider
            availability.

    Returns:
        TrajectoryPipelineRegistry: Runtime registry of named pipeline definitions.

    Raises:
        KeyError: If a pipeline references an unknown stage id.
        ValueError: If duplicate pipeline ids or aliases are discovered.
    """
    stage_bundle = stage_registry_bundle or build_stage_registry_bundle(stage_catalog, runtime_feature_policy=runtime_feature_policy)
    normalized_configs = [
        _resolve_config_payload(item)
        for item in (tuple(pipeline_configs) if pipeline_configs not in (None, ()) else default_pipeline_configs())
    ]
    if not any(item.pipeline_id == 'default' for item in normalized_configs):
        normalized_configs.insert(0, TrajectoryPipelineConfig())
    registry = TrajectoryPipelineRegistry()
    for config in normalized_configs:
        try:
            planner_stage, resolved_planner_stage_id, planner_fallback = _resolve_stage_reference(
                stage_bundle.planner_stages,
                stage_id=str(config.planner_stage_id),
                kind='planner',
                bundle=stage_bundle,
            )
            retime_stage, resolved_retime_stage_id, retime_fallback = _resolve_stage_reference(
                stage_bundle.retime_stages,
                stage_id=str(config.retime_stage_id),
                kind='retime',
                bundle=stage_bundle,
            )
            validate_stage, resolved_validate_stage_id, validate_fallback = _resolve_stage_reference(
                stage_bundle.validate_stages,
                stage_id=str(config.validate_stage_id),
                kind='validate',
                bundle=stage_bundle,
            )
        except KeyError as exc:
            raise KeyError(f'unknown trajectory pipeline stage referenced by {config.pipeline_id}: {exc.args[0]}') from exc
        postprocessors: list[TrajectoryPostprocessorStage] = []
        postprocessor_resolution: list[dict[str, object]] = []
        for stage_id in config.postprocessor_stage_ids:
            try:
                stage, resolved_stage_id, fallback_row = _resolve_stage_reference(
                    stage_bundle.postprocessor_stages,
                    stage_id=str(stage_id),
                    kind='postprocessor',
                    bundle=stage_bundle,
                )
                postprocessors.append(stage)
                postprocessor_resolution.append({
                    'requested_stage_id': str(stage_id),
                    'resolved_stage_id': str(resolved_stage_id),
                    'fallback_stage_id': None if fallback_row is None else str(fallback_row.get('fallback_stage_id', '') or ''),
                })
            except KeyError as exc:
                raise KeyError(f'unknown trajectory pipeline postprocessor referenced by {config.pipeline_id}: {exc.args[0]}') from exc
        pipeline = TrajectoryPipelineDefinition(
            pipeline_id=str(config.pipeline_id),
            planner_stage=planner_stage,
            retime_stage=retime_stage,
            validate_stage=validate_stage,
            postprocessors=tuple(postprocessors),
            metadata={
                **dict(config.metadata),
                'planner_stage_id': str(config.planner_stage_id),
                'retime_stage_id': str(config.retime_stage_id),
                'validate_stage_id': str(config.validate_stage_id),
                'postprocessor_stage_ids': list(config.postprocessor_stage_ids),
                'configured_externally': True,
                'stage_catalog_enabled': bool(stage_catalog or stage_registry_bundle),
                'stage_provider_surface_version': 'v1',
                'stage_provider_catalog': _stage_provider_summary(stage_bundle),
                'stage_resolution': {
                    'planner': {
                        'requested_stage_id': str(config.planner_stage_id),
                        'resolved_stage_id': str(resolved_planner_stage_id),
                        'fallback_stage_id': None if planner_fallback is None else str(planner_fallback.get('fallback_stage_id', '') or ''),
                    },
                    'retime': {
                        'requested_stage_id': str(config.retime_stage_id),
                        'resolved_stage_id': str(resolved_retime_stage_id),
                        'fallback_stage_id': None if retime_fallback is None else str(retime_fallback.get('fallback_stage_id', '') or ''),
                    },
                    'validate': {
                        'requested_stage_id': str(config.validate_stage_id),
                        'resolved_stage_id': str(resolved_validate_stage_id),
                        'fallback_stage_id': None if validate_fallback is None else str(validate_fallback.get('fallback_stage_id', '') or ''),
                    },
                    'postprocessors': postprocessor_resolution,
                },
            },
        )
        registry.register(pipeline, aliases=tuple(config.aliases))
    return registry


def build_default_trajectory_pipeline_registry() -> TrajectoryPipelineRegistry:
    """Backward-compatible helper that returns the shipped default pipeline registry."""
    return build_trajectory_pipeline_registry(default_pipeline_configs())
