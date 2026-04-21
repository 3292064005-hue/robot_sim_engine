from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path

import yaml

from robot_sim.infra.schema import ConfigSchema
from robot_sim.model.app_config import AppConfig, PlotConfig, RenderAdviceConfig, RenderConfig, WindowConfig
from robot_sim.model.solver_config import (
    IKConfig,
    SolverSettings,
    TrajectoryConfig,
    TrajectoryPipelineConfig,
    TrajectoryStageCatalogEntry,
)


class ConfigService:
    """Load application and solver configuration with profile-aware overrides.

    The typed dataclass defaults are now the code-level single source of truth. Checked-in
    profile files only provide profile-scoped overrides, feature flags, and optional extension
    catalogs.
    """

    DEFAULT_PROFILE = 'default'
    PROFILE_DIR_NAME = 'profiles'
    LOCAL_OVERRIDE_DIR_NAME = 'local'
    APP_CONFIG_NAME = 'app.yaml'
    SOLVER_CONFIG_NAME = 'solver.yaml'
    APP_LOCAL_OVERRIDE_NAME = 'app.local.yaml'
    SOLVER_LOCAL_OVERRIDE_NAME = 'solver.local.yaml'
    LOCAL_OVERRIDE_DIR_ENV = 'ROBOT_SIM_CONFIG_LOCAL_DIR'
    APP_LOCAL_OVERRIDE_ENV = 'ROBOT_SIM_APP_CONFIG_OVERRIDE'
    SOLVER_LOCAL_OVERRIDE_ENV = 'ROBOT_SIM_SOLVER_CONFIG_OVERRIDE'
    PLUGIN_MANIFEST_NAME = 'plugins.yaml'
    PROFILE_PLUGIN_MANIFEST_SUFFIX = '.plugins.yaml'
    DEFAULT_APP_CONFIG: dict[str, object] = AppConfig().as_dict()
    DEFAULT_SOLVER_CONFIG: dict[str, object] = SolverSettings(ik=IKConfig(retry_count=1)).as_dict()

    def __init__(
        self,
        config_dir: str | Path,
        *,
        profile: str = DEFAULT_PROFILE,
        local_override_dir: str | Path | None = None,
    ) -> None:
        normalized_profile = str(profile or '').strip()
        if not normalized_profile:
            raise ValueError('ConfigService profile must be a non-empty string')
        self.config_dir = Path(config_dir)
        self.profile = normalized_profile
        self._explicit_local_override_dir = Path(local_override_dir) if local_override_dir is not None else None

    @property
    def profile_dir(self) -> Path:
        return self.config_dir / self.PROFILE_DIR_NAME

    @property
    def default_local_override_dir(self) -> Path:
        return self.config_dir / self.LOCAL_OVERRIDE_DIR_NAME

    def available_profiles(self) -> tuple[str, ...]:
        if not self.profile_dir.exists():
            return ()
        return tuple(
            sorted(
                path.stem
                for path in self.profile_dir.glob('*.yaml')
                if path.is_file() and not path.name.endswith(self.PROFILE_PLUGIN_MANIFEST_SUFFIX)
            )
        )

    def describe_resolution(self) -> dict[str, object]:
        default_profile_path = self.profile_dir / f'{self.DEFAULT_PROFILE}.yaml'
        active_profile_path = self.profile_dir / f'{self.profile}.yaml'
        local_sources = self._local_override_sources()
        applied_chain: list[str] = ['typed_code_defaults', 'profiles/default.yaml']
        if self.profile != self.DEFAULT_PROFILE:
            applied_chain.append(f'profiles/{self.profile}.yaml')
        if local_sources['app'] is not None:
            applied_chain.append(str(local_sources['app'].relative_to(self.config_dir)) if local_sources['app'].is_relative_to(self.config_dir) else str(local_sources['app']))
        if local_sources['solver'] is not None:
            applied_chain.append(str(local_sources['solver'].relative_to(self.config_dir)) if local_sources['solver'].is_relative_to(self.config_dir) else str(local_sources['solver']))
        return {
            'config_root': str(self.config_dir),
            'active_profile': self.profile,
            'resolution_order': tuple(applied_chain),
            'default_profile_path': str(default_profile_path),
            'active_profile_path': str(active_profile_path),
            'default_truth_source': 'typed_code_defaults',
            'local_override_dir': str(self._resolved_local_override_dir()),
            'local_override_paths': {
                'app': None if local_sources['app'] is None else str(local_sources['app']),
                'solver': None if local_sources['solver'] is None else str(local_sources['solver']),
            },
            'existing_files': {
                'default_profile': default_profile_path.exists(),
                'active_profile': active_profile_path.exists(),
                'local_app_override': local_sources['app'] is not None and local_sources['app'].exists(),
                'local_solver_override': local_sources['solver'] is not None and local_sources['solver'].exists(),
            },
        }

    def load_yaml(self, name: str) -> dict:
        return self.load_yaml_path(self.config_dir / name)

    def load_yaml_path(self, path: str | Path) -> dict:
        resolved = Path(path)
        if not resolved.exists():
            return {}
        with resolved.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f'config must be a mapping: {resolved}')
        return data

    def load_profile_yaml(self, profile: str | None = None) -> dict:
        resolved_profile = str(profile or self.profile).strip()
        profile_path = self.profile_dir / f'{resolved_profile}.yaml'
        if not profile_path.exists():
            return {}
        with profile_path.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f'profile config must be a mapping: {profile_path}')
        return data

    def describe_effective_snapshot(self) -> dict[str, object]:
        return {
            'profile': self.profile,
            'app': self.load_app_config(),
            'solver': self.load_solver_config(),
            'resolution': self.describe_resolution(),
        }

    def plugin_manifest_paths(self) -> tuple[Path, ...]:
        manifest_paths: list[Path] = []
        shared_manifest = self.config_dir / self.PLUGIN_MANIFEST_NAME
        if shared_manifest.exists():
            manifest_paths.append(shared_manifest)
        profile_manifest = self.profile_dir / f'{self.profile}{self.PROFILE_PLUGIN_MANIFEST_SUFFIX}'
        if profile_manifest.exists() and profile_manifest not in manifest_paths:
            manifest_paths.append(profile_manifest)
        return tuple(manifest_paths)

    def load_app_config(self) -> dict[str, object]:
        merged = self._merge_profile_section(self.DEFAULT_APP_CONFIG, section_keys=('window', 'plots', 'render'), local_kind='app')
        return ConfigSchema.validate_app_config(merged)

    def load_solver_config(self) -> dict[str, object]:
        raw = self._merge_profile_section(self.DEFAULT_SOLVER_CONFIG, section_keys=('ik', 'trajectory'), local_kind='solver')
        normalized = deepcopy(raw)
        ik = normalized.setdefault('ik', {})
        if 'damping_lambda' not in ik and 'damping' in ik:
            ik['damping_lambda'] = ik['damping']
        return ConfigSchema.validate_solver_config(normalized)

    def load_app_settings(self) -> AppConfig:
        config = self.load_app_config()
        window = dict(config.get('window', {}) or {})
        plots = dict(config.get('plots', {}) or {})
        render = dict(config.get('render', {}) or {})
        advice = dict(render.get('advice', {}) or {})
        return AppConfig(
            window=WindowConfig(
                title=str(window.get('title', WindowConfig.title)),
                width=int(window.get('width', WindowConfig.width)),
                height=int(window.get('height', WindowConfig.height)),
                splitter_sizes=tuple(int(v) for v in window.get('splitter_sizes', WindowConfig.splitter_sizes) or WindowConfig.splitter_sizes),
                vertical_splitter_sizes=tuple(int(v) for v in window.get('vertical_splitter_sizes', WindowConfig.vertical_splitter_sizes) or WindowConfig.vertical_splitter_sizes),
            ),
            plots=PlotConfig(max_points=int(plots.get('max_points', PlotConfig.max_points))),
            render=RenderConfig(
                advice=RenderAdviceConfig(
                    high_p95_ms=float(advice.get('high_p95_ms', RenderAdviceConfig.high_p95_ms)),
                    high_average_ms=float(advice.get('high_average_ms', RenderAdviceConfig.high_average_ms)),
                    high_failure_ratio=float(advice.get('high_failure_ratio', RenderAdviceConfig.high_failure_ratio)),
                    high_span_rate_per_sec=float(advice.get('high_span_rate_per_sec', RenderAdviceConfig.high_span_rate_per_sec)),
                ),
            ),
        )

    def load_solver_settings(self) -> SolverSettings:
        config = self.load_solver_config()
        ik = dict(config.get('ik', {}) or {})
        trajectory = dict(config.get('trajectory', {}) or {})
        validation_layers = trajectory.get('validation_layers', TrajectoryConfig.validation_layers)
        if validation_layers in (None, (), []):
            resolved_layers = TrajectoryConfig.validation_layers
        else:
            resolved_layers = tuple(str(item).strip() for item in validation_layers)
        raw_pipeline_configs = trajectory.get('pipelines', ()) or ()
        resolved_pipelines: list[TrajectoryPipelineConfig] = []
        for item in raw_pipeline_configs:
            payload = dict(item or {})
            resolved_pipelines.append(
                TrajectoryPipelineConfig(
                    pipeline_id=str(payload.get('id', payload.get('pipeline_id', 'default')) or 'default'),
                    planner_stage_id=str(payload.get('planner_stage', payload.get('planner_stage_id', 'default_planner')) or 'default_planner'),
                    retime_stage_id=str(payload.get('retime_stage', payload.get('retime_stage_id', 'builtin_scaling')) or 'builtin_scaling'),
                    validate_stage_id=str(payload.get('validate_stage', payload.get('validate_stage_id', 'validate_trajectory')) or 'validate_trajectory'),
                    postprocessor_stage_ids=tuple(payload.get('postprocessors', payload.get('postprocessor_stage_ids', ())) or ()),
                    aliases=tuple(payload.get('aliases', ()) or ()),
                    metadata=dict(payload.get('metadata', {}) or {}),
                )
            )
        raw_stage_catalog = trajectory.get('stage_catalog', ()) or ()
        resolved_stage_catalog: list[TrajectoryStageCatalogEntry] = []
        for item in raw_stage_catalog:
            payload = dict(item or {})
            resolved_stage_catalog.append(
                TrajectoryStageCatalogEntry(
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
            )
        return SolverSettings(
            ik=IKConfig(**ik),
            trajectory=TrajectoryConfig(
                duration=float(trajectory.get('duration', TrajectoryConfig.duration)),
                dt=float(trajectory.get('dt', TrajectoryConfig.dt)),
                validation_layers=resolved_layers,
                pipeline_id=str(trajectory.get('pipeline_id', TrajectoryConfig.pipeline_id) or TrajectoryConfig.pipeline_id),
                pipelines=tuple(resolved_pipelines) if resolved_pipelines else TrajectoryConfig().pipelines,
                stage_catalog=tuple(resolved_stage_catalog),
            ),
        )

    def _merge_profile_section(self, base: dict[str, object], *, section_keys: tuple[str, ...], local_kind: str) -> dict[str, object]:
        merged = deepcopy(base)
        default_overlay = self._filtered_profile_overlay(self.DEFAULT_PROFILE, section_keys)
        if default_overlay:
            merged = self._deep_merge(merged, default_overlay)
        if self.profile != self.DEFAULT_PROFILE:
            profile_overlay = self._filtered_profile_overlay(self.profile, section_keys)
            if profile_overlay:
                merged = self._deep_merge(merged, profile_overlay)
        local_override = self._load_local_override(local_kind)
        if local_override:
            merged = self._deep_merge(merged, local_override)
        return merged

    def _filtered_profile_overlay(self, profile: str, section_keys: tuple[str, ...]) -> dict[str, object]:
        overlay = self.load_profile_yaml(profile)
        if not overlay:
            return {}
        return {str(key): deepcopy(value) for key, value in overlay.items() if str(key) in section_keys}

    def _resolved_local_override_dir(self) -> Path:
        if self._explicit_local_override_dir is not None:
            return self._explicit_local_override_dir
        env_dir = str(os.environ.get(self.LOCAL_OVERRIDE_DIR_ENV, '') or '').strip()
        if env_dir:
            return Path(env_dir)
        return self.default_local_override_dir

    def _local_override_sources(self) -> dict[str, Path | None]:
        override_dir = self._resolved_local_override_dir()
        app_env = str(os.environ.get(self.APP_LOCAL_OVERRIDE_ENV, '') or '').strip()
        solver_env = str(os.environ.get(self.SOLVER_LOCAL_OVERRIDE_ENV, '') or '').strip()
        app_path = Path(app_env) if app_env else override_dir / self.APP_LOCAL_OVERRIDE_NAME
        solver_path = Path(solver_env) if solver_env else override_dir / self.SOLVER_LOCAL_OVERRIDE_NAME
        return {
            'app': app_path if app_path.exists() else None,
            'solver': solver_path if solver_path.exists() else None,
        }

    def _load_local_override(self, local_kind: str) -> dict[str, object]:
        normalized_kind = str(local_kind).strip().lower()
        if normalized_kind not in {'app', 'solver'}:
            raise ValueError(f'unsupported local override kind: {local_kind}')
        preferred_sources = self._local_override_sources()
        preferred = preferred_sources[normalized_kind]
        if preferred is not None:
            return self.load_yaml_path(preferred)
        return {}

    def _deep_merge(self, base: dict, override: dict) -> dict:
        merged = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
