from __future__ import annotations

from pathlib import Path
import shutil


_CONFIG_SUBDIR = Path('robot_sim') / 'resources' / 'configs'
_SOURCE_CONFIG_SUBDIR = Path('configs')
_STAGING_SUBDIR = Path('build') / 'packaged_config_staging' / 'robot_sim' / 'resources' / 'configs'


def source_config_root(repo_root: str | Path) -> Path:
    """Return the repository config root that acts as the single source of truth."""
    return Path(repo_root) / _SOURCE_CONFIG_SUBDIR



def packaged_config_root(repo_root: str | Path) -> Path:
    """Return the build-staging directory used to verify packaged config content.

    Args:
        repo_root: Repository root.

    Returns:
        Path: Build-local staging directory for packaged config verification.

    Raises:
        None: Path construction only.
    """
    return Path(repo_root) / _STAGING_SUBDIR



def build_lib_config_root(build_lib: str | Path) -> Path:
    """Return the package config directory rooted under a setuptools build-lib tree."""
    return Path(build_lib) / _CONFIG_SUBDIR



def iter_config_files(root: str | Path) -> tuple[Path, ...]:
    """Return the normalized set of config files rooted under ``root``.

    Args:
        root: Config tree root to enumerate.

    Returns:
        tuple[Path, ...]: Sorted relative file paths.

    Raises:
        FileNotFoundError: If ``root`` does not exist.
    """
    path = Path(root)
    if not path.exists():
        raise FileNotFoundError(f'config root not found: {path}')
    return tuple(sorted(item.relative_to(path) for item in path.rglob('*') if item.is_file()))



def verify_packaged_config_sync(repo_root: str | Path) -> list[str]:
    """Verify that the packaged-config staging tree mirrors repository configs.

    Boundary behavior:
        The source checkout no longer keeps a checked-in package mirror under
        ``src/robot_sim/resources/configs``. Verification therefore compares the single
        checked-in config source tree against the generated build-staging tree.
    """
    repo_root_path = Path(repo_root)
    source_root = source_config_root(repo_root_path)
    packaged_root = packaged_config_root(repo_root_path)
    source_files = set(iter_config_files(source_root))
    packaged_files = set(iter_config_files(packaged_root)) if packaged_root.exists() else set()
    errors: list[str] = []
    for rel in sorted(source_files - packaged_files):
        errors.append(f'missing staged config: {rel.as_posix()}')
    for rel in sorted(packaged_files - source_files):
        errors.append(f'extraneous staged config: {rel.as_posix()}')
    for rel in sorted(source_files & packaged_files):
        source_bytes = (source_root / rel).read_bytes()
        packaged_bytes = (packaged_root / rel).read_bytes()
        if source_bytes != packaged_bytes:
            errors.append(f'staged config drift: {rel.as_posix()}')
    return errors



def sync_packaged_configs(repo_root: str | Path) -> dict[str, int]:
    """Stage repository configs into a build-local packaged resource tree.

    Args:
        repo_root: Repository root.

    Returns:
        dict[str, int]: Summary containing copied and removed file counts.

    Raises:
        FileNotFoundError: If the source config root does not exist.
    """
    repo_root_path = Path(repo_root)
    return _sync_config_tree(source_config_root(repo_root_path), packaged_config_root(repo_root_path))



def install_packaged_configs(build_lib: str | Path, repo_root: str | Path) -> dict[str, int]:
    """Install packaged configs into the setuptools build-lib output tree.

    Args:
        build_lib: Setuptools ``build_lib`` directory.
        repo_root: Repository root containing the checked-in config source tree.

    Returns:
        dict[str, int]: Summary containing copied and removed file counts.

    Raises:
        FileNotFoundError: If the source config root does not exist.
    """
    return _sync_config_tree(source_config_root(repo_root), build_lib_config_root(build_lib))



def _sync_config_tree(source_root: str | Path, target_root: str | Path) -> dict[str, int]:
    source_path = Path(source_root)
    target_path = Path(target_root)
    source_files = set(iter_config_files(source_path))
    target_files = set(iter_config_files(target_path)) if target_path.exists() else set()
    copied = 0
    removed = 0
    target_path.mkdir(parents=True, exist_ok=True)

    for rel in sorted(target_files - source_files):
        target = target_path / rel
        target.unlink()
        removed += 1

    for rel in sorted(source_files):
        src = source_path / rel
        dst = target_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or src.read_bytes() != dst.read_bytes():
            shutil.copy2(src, dst)
            copied += 1

    for directory in sorted((item for item in target_path.rglob('*') if item.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue

    return {'copied': copied, 'removed': removed}
