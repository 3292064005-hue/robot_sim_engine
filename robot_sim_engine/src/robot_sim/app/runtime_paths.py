from __future__ import annotations

from dataclasses import dataclass
import os
from importlib.resources import files as resource_files
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    """Resolved runtime filesystem layout.

    Attributes:
        project_root: User-visible compatibility root that owns the active runtime resources.
            Source runtimes retain the requested/source checkout root; packaged runtimes project
            the packaged resource root instead of an arbitrary ancestor directory.
        resource_root: Root containing runtime configuration assets.
        config_root: Directory containing app/solver/plugins/profile configuration files.
        robot_root: Writable directory containing persisted robot YAML files.
        bundled_robot_root: Read-only directory containing bundled robot YAML files shipped with
            the source tree or installed package resources.
        profiles_root: Directory containing profile overlays.
        logging_config_path: Logging configuration file consumed during bootstrap.
        plugin_manifest_path: Plugin manifest path.
        app_config_path: App/window configuration file.
        solver_config_path: Solver/trajectory configuration file.
        export_root: Writable directory used for screenshots, reports, and bundles.
        source_layout_available: Whether runtime assets were resolved from the repository layout.
    """

    project_root: Path
    resource_root: Path
    config_root: Path
    robot_root: Path
    bundled_robot_root: Path
    profiles_root: Path
    logging_config_path: Path
    plugin_manifest_path: Path
    app_config_path: Path
    solver_config_path: Path
    export_root: Path
    source_layout_available: bool

    @property
    def layout_mode(self) -> str:
        """Return the normalized runtime layout mode for diagnostics."""
        return 'source' if self.source_layout_available else 'packaged'


_PACKAGE_CONFIG_ROOT = resource_files('robot_sim.resources').joinpath('configs')
_APP_DATA_DIR_NAME = 'robot-sim-engine'
_EXPORT_SUBDIR_NAME = 'exports'
_ROBOT_LIBRARY_SUBDIR_NAME = 'robots'
_LEGACY_EXPORT_POLICY = 'legacy_cwd'
_PLATFORM_EXPORT_POLICY = 'platform_default'


def _package_config_root() -> Path:
    """Return the discovered packaged configuration root.

    Returns:
        Path: Filesystem path for packaged configuration resources.

    Raises:
        FileNotFoundError: If neither installed package resources nor an already-built
            staged mirror are available.

    Boundary behavior:
        The resolver is intentionally side-effect free. It does not attempt to stage or
        repair packaged configs at runtime; build/CI remain solely responsible for
        producing wheel resources and any read-only staged mirrors.
    """
    path = Path(str(_PACKAGE_CONFIG_ROOT))
    if path.exists():
        return path

    from robot_sim.infra.packaged_config_sync import packaged_config_root

    repo_root = Path(__file__).resolve().parents[3]
    staged_root = packaged_config_root(repo_root)
    if staged_root.exists():
        return staged_root

    raise FileNotFoundError(f'packaged runtime configs not found: {path}')


def _repository_root() -> Path:
    """Return the source-checkout root that owns the runtime-path resolver module."""
    return Path(__file__).resolve().parents[3]


def _normalize_project_root(project_root: str | Path | None) -> Path:
    if project_root is None:
        return _repository_root()
    return Path(project_root)


def _source_config_root(root: Path) -> Path:
    """Return the conventional source-layout config directory for a candidate root."""
    return root / 'configs'


def _user_data_root() -> Path:
    """Return the writable per-user data root used by packaged execution.

    Boundary behavior:
        The function prefers ``XDG_DATA_HOME`` on Linux and falls back to
        ``~/.local/share`` when the XDG variable is unset. This keeps packaged
        exports and user-owned robot-library writes independent from the current
        working directory and from read-only package resources.
    """
    xdg_root = str(os.environ.get('XDG_DATA_HOME', '') or '').strip()
    if xdg_root:
        return Path(xdg_root) / _APP_DATA_DIR_NAME
    return Path.home() / '.local' / 'share' / _APP_DATA_DIR_NAME


def _resolve_packaged_export_root() -> Path:
    policy = str(os.environ.get('ROBOT_SIM_EXPORT_POLICY', _PLATFORM_EXPORT_POLICY) or _PLATFORM_EXPORT_POLICY).strip() or _PLATFORM_EXPORT_POLICY
    if policy == _LEGACY_EXPORT_POLICY:
        return Path.cwd() / _EXPORT_SUBDIR_NAME
    return _user_data_root() / _EXPORT_SUBDIR_NAME


def _resolve_packaged_robot_root(*, create_dirs: bool = True) -> Path:
    """Return the writable packaged robot-library directory.

    Returns:
        Path: User-owned directory used for robot imports and save operations.

    Raises:
        None: The directory is created on demand.

    Boundary behavior:
        Installed wheels treat bundled robot YAML files as read-only assets. User saves and
        imports must therefore target a per-user writable overlay instead of ``site-packages``.
    """
    robot_root = _user_data_root() / _ROBOT_LIBRARY_SUBDIR_NAME
    if create_dirs:
        robot_root.mkdir(parents=True, exist_ok=True)
    return robot_root


def _resolve_export_root(*, root: Path, source_layout_available: bool, create_dirs: bool = True) -> Path:
    export_override = str(os.environ.get('ROBOT_SIM_EXPORT_DIR', '') or '').strip()
    if export_override:
        export_root = Path(export_override)
    elif source_layout_available:
        export_root = root / _EXPORT_SUBDIR_NAME
    else:
        export_root = _resolve_packaged_export_root()
    if create_dirs:
        export_root.mkdir(parents=True, exist_ok=True)
    return export_root


def resolve_runtime_paths(project_root: str | Path | None = None, *, create_dirs: bool = True) -> RuntimePaths:
    """Resolve runtime paths for both source-tree and installed-wheel execution.

    Args:
        project_root: Optional preferred project root. Existing source-tree callers pass the
            repository root here; installed-wheel callers may omit it.

    Returns:
        RuntimePaths: Normalized runtime path bundle.

    Raises:
        FileNotFoundError: If neither source-tree nor packaged runtime resources can be found.
    """
    root = _normalize_project_root(project_root)
    requested_source_config_root = _source_config_root(root)
    repository_root = _repository_root()
    repository_source_config_root = _source_config_root(repository_root)

    if requested_source_config_root.is_dir():
        source_layout_available = True
        resource_root = root
        config_root = requested_source_config_root
        robot_root = config_root / 'robots'
    elif repository_source_config_root.is_dir():
        source_layout_available = True
        resource_root = repository_root
        config_root = repository_source_config_root
        robot_root = repository_source_config_root / 'robots'
    else:
        config_root = _package_config_root()
        source_layout_available = False
        resource_root = config_root.parent
        robot_root = _resolve_packaged_robot_root(create_dirs=create_dirs)

    export_root = _resolve_export_root(root=root, source_layout_available=source_layout_available, create_dirs=create_dirs)
    bundled_robot_root = config_root / 'robots'

    compatibility_project_root = root if source_layout_available else resource_root

    return RuntimePaths(
        project_root=compatibility_project_root,
        resource_root=resource_root,
        config_root=config_root,
        robot_root=robot_root,
        bundled_robot_root=bundled_robot_root,
        profiles_root=config_root / 'profiles',
        logging_config_path=config_root / 'logging.yaml',
        plugin_manifest_path=config_root / 'plugins.yaml',
        app_config_path=config_root / 'app.yaml',
        solver_config_path=config_root / 'solver.yaml',
        export_root=export_root,
        source_layout_available=source_layout_available,
    )
