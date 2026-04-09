from __future__ import annotations

from copy import deepcopy
<<<<<<< HEAD
import os
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from pathlib import Path

import yaml

from robot_sim.infra.schema import ConfigSchema
from robot_sim.model.app_config import AppConfig, PlotConfig, WindowConfig
<<<<<<< HEAD
from robot_sim.model.solver_config import (
    IKConfig,
    SUPPORTED_TRAJECTORY_VALIDATION_LAYERS,
    SolverSettings,
    TrajectoryConfig,
)
=======
from robot_sim.model.solver_config import IKConfig, SolverSettings, TrajectoryConfig
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


class ConfigService:
    """Load application and solver configuration with profile-aware overrides.

<<<<<<< HEAD
    The shipped repository/profile configuration is the authoritative runtime baseline.
    Optional local overrides are resolved separately so repository-managed defaults do not
    silently flatten per-profile differences.
=======
    Resolution order is deliberately explicit so release, CI, GUI, and local development
    can share a common baseline without duplicating the full configuration tree.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    """

    DEFAULT_PROFILE = 'default'
    PROFILE_DIR_NAME = 'profiles'
<<<<<<< HEAD
    LOCAL_OVERRIDE_DIR_NAME = 'local'
    APP_CONFIG_NAME = 'app.yaml'
    SOLVER_CONFIG_NAME = 'solver.yaml'
    APP_LOCAL_OVERRIDE_NAME = 'app.local.yaml'
    SOLVER_LOCAL_OVERRIDE_NAME = 'solver.local.yaml'
    LOCAL_OVERRIDE_DIR_ENV = 'ROBOT_SIM_CONFIG_LOCAL_DIR'
    APP_LOCAL_OVERRIDE_ENV = 'ROBOT_SIM_APP_CONFIG_OVERRIDE'
    SOLVER_LOCAL_OVERRIDE_ENV = 'ROBOT_SIM_SOLVER_CONFIG_OVERRIDE'
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    DEFAULT_APP_CONFIG: dict[str, object] = {
        'window': {
            'title': 'Robot Sim Engine',
            'width': 1680,
            'height': 980,
            'splitter_sizes': [420, 820, 360],
            'vertical_splitter_sizes': [700, 260],
        },
        'plots': {
            'max_points': 5000,
        },
    }
    DEFAULT_SOLVER_CONFIG: dict[str, object] = {
        'ik': {
            'mode': 'dls',
            'max_iters': 150,
            'pos_tol': 1.0e-4,
            'ori_tol': 1.0e-4,
            'damping_lambda': 0.05,
            'step_scale': 0.5,
            'enable_nullspace': True,
            'joint_limit_weight': 0.03,
            'manipulability_weight': 0.0,
            'position_only': False,
            'orientation_weight': 1.0,
            'max_step_norm': 0.35,
            'fallback_to_dls_when_singular': True,
            'reachability_precheck': True,
            'retry_count': 1,
            'random_seed': 7,
            'adaptive_damping': True,
            'min_damping_lambda': 1.0e-4,
            'max_damping_lambda': 1.5,
            'use_weighted_least_squares': True,
            'clamp_seed_to_joint_limits': True,
            'normalize_target_rotation': True,
            'allow_orientation_relaxation': False,
            'orientation_relaxation_pos_multiplier': 5.0,
            'orientation_relaxation_ori_multiplier': 25.0,
        },
        'trajectory': {
            'duration': 3.0,
            'dt': 0.02,
<<<<<<< HEAD
            'validation_layers': list(SUPPORTED_TRAJECTORY_VALIDATION_LAYERS),
        },
    }

    def __init__(
        self,
        config_dir: str | Path,
        *,
        profile: str = DEFAULT_PROFILE,
        allow_legacy_local_override: bool = False,
        local_override_dir: str | Path | None = None,
    ) -> None:
        """Create the config service.

        Args:
            config_dir: Directory containing shipped config resources and profile overlays.
            profile: Active configuration profile. ``default`` uses only the shared baseline
                unless an explicit local override source is enabled.
            allow_legacy_local_override: Deprecated no-op retained for constructor
                compatibility. Repository-level ``app.yaml`` / ``solver.yaml`` override
                loading has been retired; only explicit local override files are supported.
            local_override_dir: Optional explicit directory containing
                ``app.local.yaml`` / ``solver.local.yaml`` override files.
=======
        },
    }

    def __init__(self, config_dir: str | Path, *, profile: str = DEFAULT_PROFILE) -> None:
        """Create the config service.

        Args:
            config_dir: Directory containing ``app.yaml``, ``solver.yaml``, and optional
                ``profiles/<profile>.yaml`` overlays.
            profile: Active configuration profile. ``default`` uses only the shared
                baseline unless a local override file exists.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

        Returns:
            None: Stores configuration paths and profile state.

        Raises:
            ValueError: If ``profile`` is empty.
        """
        normalized_profile = str(profile or '').strip()
        if not normalized_profile:
            raise ValueError('ConfigService profile must be a non-empty string')
        self.config_dir = Path(config_dir)
        self.profile = normalized_profile
<<<<<<< HEAD
        self.allow_legacy_local_override = False
        self._explicit_local_override_dir = Path(local_override_dir) if local_override_dir is not None else None
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    @property
    def profile_dir(self) -> Path:
        """Return the profile-directory path."""
        return self.config_dir / self.PROFILE_DIR_NAME

<<<<<<< HEAD
    @property
    def default_local_override_dir(self) -> Path:
        """Return the default local override directory under the config root."""
        return self.config_dir / self.LOCAL_OVERRIDE_DIR_NAME

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def available_profiles(self) -> tuple[str, ...]:
        """Return the available configuration profile identifiers.

        Returns:
            tuple[str, ...]: Sorted profile identifiers discovered on disk.

        Raises:
            None: Missing profile directories simply yield an empty tuple.
        """
        if not self.profile_dir.exists():
            return ()
        return tuple(sorted(path.stem for path in self.profile_dir.glob('*.yaml') if path.is_file()))

<<<<<<< HEAD
    def describe_resolution(self) -> dict[str, object]:
        """Describe the active configuration resolution chain.

        Returns:
            dict[str, object]: Stable source summary for diagnostics, docs, and startup logs.

        Raises:
            None: Pure projection of filesystem and profile state.
        """
        default_profile_path = self.profile_dir / f'{self.DEFAULT_PROFILE}.yaml'
        active_profile_path = self.profile_dir / f'{self.profile}.yaml'
        local_sources = self._local_override_sources()
        applied_chain: list[str] = ['code_defaults', 'profiles/default.yaml']
        if self.profile != self.DEFAULT_PROFILE:
            applied_chain.append(f'profiles/{self.profile}.yaml')
        if local_sources['app'] is not None:
            applied_chain.append(str(local_sources['app'].relative_to(self.config_dir)) if local_sources['app'].is_relative_to(self.config_dir) else str(local_sources['app']))
        if local_sources['solver'] is not None:
            applied_chain.append(str(local_sources['solver'].relative_to(self.config_dir)) if local_sources['solver'].is_relative_to(self.config_dir) else str(local_sources['solver']))
        base_sources = self._base_config_sources()
        app_base_path = base_sources['app']
        solver_base_path = base_sources['solver']
        return {
            'config_root': str(self.config_dir),
            'active_profile': self.profile,
            'resolution_order': tuple(applied_chain),
            'default_profile_path': str(default_profile_path),
            'active_profile_path': str(active_profile_path),
            'local_override_dir': str(self._resolved_local_override_dir()),
            'local_override_paths': {
                'app': None if local_sources['app'] is None else str(local_sources['app']),
                'solver': None if local_sources['solver'] is None else str(local_sources['solver']),
            },
            'base_config_paths': {
                'app': str(app_base_path),
                'solver': str(solver_base_path),
            },
            'legacy_override_paths': {
                'app': str(app_base_path),
                'solver': str(solver_base_path),
            },
            'legacy_local_override_enabled': False,
            'existing_files': {
                'base_app_config': app_base_path.exists(),
                'base_solver_config': solver_base_path.exists(),
                'default_profile': default_profile_path.exists(),
                'active_profile': active_profile_path.exists(),
                'local_app_override': local_sources['app'] is not None and local_sources['app'].exists(),
                'local_solver_override': local_sources['solver'] is not None and local_sources['solver'].exists(),
                'legacy_app_override': False,
                'legacy_solver_override': False,
            },
            'ignored_legacy_override_files': {
                'app': app_base_path.exists(),
                'solver': solver_base_path.exists(),
            },
        }

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def load_yaml(self, name: str) -> dict:
        """Load a YAML mapping from the config directory.

        Args:
            name: Relative YAML filename under ``config_dir``.

        Returns:
            dict: Parsed mapping or an empty mapping when the file is absent.

        Raises:
            ValueError: If the YAML payload is not a mapping.
        """
<<<<<<< HEAD
        return self.load_yaml_path(self.config_dir / name)

    def load_yaml_path(self, path: str | Path) -> dict:
        """Load a YAML mapping from an explicit path.

        Args:
            path: Explicit YAML path.

        Returns:
            dict: Parsed mapping or an empty mapping when the file is absent.

        Raises:
            ValueError: If the YAML payload is not a mapping.
        """
        resolved = Path(path)
        if not resolved.exists():
            return {}
        with resolved.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f'config must be a mapping: {resolved}')
=======
        path = self.config_dir / name
        if not path.exists():
            return {}
        with path.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f'config must be a mapping: {path}')
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        return data

    def load_profile_yaml(self, profile: str | None = None) -> dict:
        """Load a profile overlay mapping.

        Args:
            profile: Optional explicit profile name. Defaults to the active profile.

        Returns:
            dict: Profile mapping or an empty mapping when no overlay is defined.

        Raises:
            ValueError: If the profile YAML payload is not a mapping.
        """
        resolved_profile = str(profile or self.profile).strip()
<<<<<<< HEAD
        profile_path = self.profile_dir / f'{resolved_profile}.yaml'
=======
        if resolved_profile == self.DEFAULT_PROFILE:
            profile_path = self.profile_dir / f'{self.DEFAULT_PROFILE}.yaml'
        else:
            profile_path = self.profile_dir / f'{resolved_profile}.yaml'
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        if not profile_path.exists():
            return {}
        with profile_path.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f'profile config must be a mapping: {profile_path}')
        return data

    def load_app_config(self) -> dict[str, object]:
        """Load the validated application UI configuration as a plain mapping."""
<<<<<<< HEAD
        merged = self._merge_profile_section(self.DEFAULT_APP_CONFIG, section_keys=('window', 'plots'), local_kind='app')
=======
        merged = self._merge_profile_section(self.DEFAULT_APP_CONFIG, section_keys=('window', 'plots'), local_name='app.yaml')
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        return ConfigSchema.validate_app_config(merged)

    def load_solver_config(self) -> dict[str, object]:
        """Load the validated solver and trajectory configuration as a plain mapping."""
<<<<<<< HEAD
        raw = self._merge_profile_section(self.DEFAULT_SOLVER_CONFIG, section_keys=('ik', 'trajectory'), local_kind='solver')
=======
        raw = self._merge_profile_section(self.DEFAULT_SOLVER_CONFIG, section_keys=('ik', 'trajectory'), local_name='solver.yaml')
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        normalized = deepcopy(raw)
        ik = normalized.setdefault('ik', {})
        if 'damping_lambda' not in ik and 'damping' in ik:
            ik['damping_lambda'] = ik['damping']
        return ConfigSchema.validate_solver_config(normalized)

    def load_app_settings(self) -> AppConfig:
        """Load the application configuration as typed settings objects.

        Returns:
            AppConfig: Typed application configuration.

        Raises:
            SchemaError: If the underlying app configuration is invalid.
        """
        config = self.load_app_config()
        window = dict(config.get('window', {}) or {})
        plots = dict(config.get('plots', {}) or {})
        return AppConfig(
            window=WindowConfig(
                title=str(window.get('title', WindowConfig.title)),
                width=int(window.get('width', WindowConfig.width)),
                height=int(window.get('height', WindowConfig.height)),
                splitter_sizes=tuple(int(v) for v in window.get('splitter_sizes', WindowConfig.splitter_sizes) or WindowConfig.splitter_sizes),
                vertical_splitter_sizes=tuple(int(v) for v in window.get('vertical_splitter_sizes', WindowConfig.vertical_splitter_sizes) or WindowConfig.vertical_splitter_sizes),
            ),
            plots=PlotConfig(
                max_points=int(plots.get('max_points', PlotConfig.max_points)),
            ),
        )

    def load_solver_settings(self) -> SolverSettings:
        """Load the solver configuration as typed settings objects.

        Returns:
            SolverSettings: Typed solver and trajectory configuration bundle.

        Raises:
            SchemaError: If the underlying solver configuration is invalid.
        """
        config = self.load_solver_config()
        ik = dict(config.get('ik', {}) or {})
        trajectory = dict(config.get('trajectory', {}) or {})
<<<<<<< HEAD
        validation_layers = trajectory.get('validation_layers', TrajectoryConfig.validation_layers)
        if validation_layers in (None, (), []):
            resolved_layers = TrajectoryConfig.validation_layers
        else:
            resolved_layers = tuple(str(item).strip() for item in validation_layers)
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        return SolverSettings(
            ik=IKConfig(**ik),
            trajectory=TrajectoryConfig(
                duration=float(trajectory.get('duration', TrajectoryConfig.duration)),
                dt=float(trajectory.get('dt', TrajectoryConfig.dt)),
<<<<<<< HEAD
                validation_layers=resolved_layers,
            ),
        )

    def _merge_profile_section(self, base: dict[str, object], *, section_keys: tuple[str, ...], local_kind: str) -> dict[str, object]:
        """Merge baseline, profile, and optional local overrides for a logical config section.
=======
            ),
        )

    def _merge_profile_section(self, base: dict[str, object], *, section_keys: tuple[str, ...], local_name: str) -> dict[str, object]:
        """Merge baseline, profile, and local overrides for a logical config section.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

        Args:
            base: Shared in-code defaults.
            section_keys: Top-level keys owned by the logical section.
<<<<<<< HEAD
            local_kind: Logical config kind, either ``app`` or ``solver``.
=======
            local_name: Local override filename under ``config_dir``.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

        Returns:
            dict[str, object]: Deep-merged configuration mapping.

        Raises:
            ValueError: Propagates malformed YAML mapping errors from profile or local files.
        """
        merged = deepcopy(base)
<<<<<<< HEAD
        base_config = self._load_base_config(local_kind)
        if base_config:
            merged = self._deep_merge(merged, base_config)
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        default_overlay = self._filtered_profile_overlay(self.DEFAULT_PROFILE, section_keys)
        if default_overlay:
            merged = self._deep_merge(merged, default_overlay)
        if self.profile != self.DEFAULT_PROFILE:
            profile_overlay = self._filtered_profile_overlay(self.profile, section_keys)
            if profile_overlay:
                merged = self._deep_merge(merged, profile_overlay)
<<<<<<< HEAD
        local_override = self._load_local_override(local_kind)
=======
        local_override = self.load_yaml(local_name)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        if local_override:
            merged = self._deep_merge(merged, local_override)
        return merged

    def _filtered_profile_overlay(self, profile: str, section_keys: tuple[str, ...]) -> dict[str, object]:
        overlay = self.load_profile_yaml(profile)
        if not overlay:
            return {}
        return {str(key): deepcopy(value) for key, value in overlay.items() if str(key) in section_keys}

<<<<<<< HEAD

    def _uses_authoritative_base_files(self) -> bool:
        """Return whether ``app.yaml`` / ``solver.yaml`` should be treated as shipped base config.

        The authoritative repository layout keeps configuration under a dedicated ``configs``
        directory or exposes a ``profiles`` subtree. Ad-hoc temp directories that merely contain
        ``app.yaml`` / ``solver.yaml`` are treated as retired repository-level overrides and are
        ignored unless promoted into the canonical layout.
        """
        return self.config_dir.name == 'configs' or self.profile_dir.exists()

    def _base_config_sources(self) -> dict[str, Path]:
        """Return canonical shipped base-config file paths for app and solver config kinds."""
        return {
            'app': self.config_dir / self.APP_CONFIG_NAME,
            'solver': self.config_dir / self.SOLVER_CONFIG_NAME,
        }

    def _load_base_config(self, local_kind: str) -> dict[str, object]:
        """Load the shipped base config mapping for ``app`` or ``solver``."""
        normalized_kind = str(local_kind).strip().lower()
        if normalized_kind not in {'app', 'solver'}:
            raise ValueError(f'unsupported base config kind: {local_kind}')
        if not self._uses_authoritative_base_files():
            return {}
        return self.load_yaml_path(self._base_config_sources()[normalized_kind])

    def _resolved_local_override_dir(self) -> Path:
        """Return the preferred local override directory.

        Resolution order:
            1. Explicit constructor override.
            2. ``ROBOT_SIM_CONFIG_LOCAL_DIR`` environment variable.
            3. ``<config_root>/local``.
        """
        if self._explicit_local_override_dir is not None:
            return self._explicit_local_override_dir
        env_dir = str(os.environ.get(self.LOCAL_OVERRIDE_DIR_ENV, '') or '').strip()
        if env_dir:
            return Path(env_dir)
        return self.default_local_override_dir

    def _local_override_sources(self) -> dict[str, Path | None]:
        """Return resolved local override file paths for app and solver config kinds."""
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
        """Load optional explicit local override YAML for the requested config kind.

        Args:
            local_kind: ``app`` or ``solver``.

        Returns:
            dict[str, object]: Override mapping or an empty mapping when no override is active.

        Raises:
            ValueError: If a discovered local override file is not a mapping.
        """
        normalized_kind = str(local_kind).strip().lower()
        if normalized_kind not in {'app', 'solver'}:
            raise ValueError(f'unsupported local override kind: {local_kind}')
        preferred_sources = self._local_override_sources()
        preferred = preferred_sources[normalized_kind]
        if preferred is not None:
            return self.load_yaml_path(preferred)
        return {}

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep-merge two configuration mappings.

        Args:
            base: Base configuration mapping.
            override: Override configuration mapping.

        Returns:
            dict: Deep-merged mapping.

        Raises:
            None: The merge operation is structural only.
        """
        merged = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
