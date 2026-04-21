from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.metadata
import importlib.util
import json
import platform
import sys
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeBaselineReport:
    mode: str
    platform_system: str
    python_version: str
    os_id: str | None
    os_version_id: str | None
    pyside_version: str | None
    build_available: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_json(self) -> str:
        payload = asdict(self)
        payload['ok'] = self.ok
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def read_os_release(path: str | Path = '/etc/os-release') -> dict[str, str]:
    """Parse an ``os-release`` file into a normalized dictionary.

    Args:
        path: Path to the os-release file.

    Returns:
        dict[str, str]: Parsed key/value pairs. Missing files return an empty mapping.
    """
    target = Path(path)
    if not target.exists():
        return {}
    payload: dict[str, str] = {}
    for line in target.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        payload[key.strip()] = value.strip().strip('"')
    return payload


def _python_tuple(version_info: Any | None = None) -> tuple[int, int, int]:
    current = version_info if version_info is not None else sys.version_info
    if hasattr(current, 'major'):
        return int(current.major), int(current.minor), int(getattr(current, 'micro', 0))
    return int(current[0]), int(current[1]), int(current[2] if len(current) > 2 else 0)


def _version_string(version: tuple[int, int, int]) -> str:
    return '.'.join(str(part) for part in version)


def _imported_module_version(module_name: str) -> str | None:
    if importlib.util.find_spec(module_name) is None:
        return None
    try:
        return importlib.metadata.version(module_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _build_available() -> bool:
    return importlib.util.find_spec('build') is not None


def _is_python_at_least(version: tuple[int, int, int], *, major: int, minor: int) -> bool:
    return version >= (major, minor, 0)


def _is_exact_python(version: tuple[int, int, int], *, major: int, minor: int) -> bool:
    return version[:2] == (major, minor)


def _is_version_at_least(text: str, *, major: int, minor: int) -> bool:
    parts = text.split('.')
    try:
        current_major = int(parts[0])
        current_minor = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        return False
    return (current_major, current_minor) >= (major, minor)


def evaluate_runtime_baseline(
    mode: str,
    *,
    platform_system: str | None = None,
    version_info: Any | None = None,
    os_release: dict[str, str] | None = None,
    pyside_version: str | None = None,
    build_available: bool | None = None,
) -> RuntimeBaselineReport:
    """Evaluate whether the current runtime satisfies a named validation baseline.

    Modes:
        - ``headless``: Linux + Python >= 3.10.
        - ``gui``: Ubuntu 22.04 + Python 3.10 + PySide6 >= 6.5.
        - ``release``: Linux + Python >= 3.10 + ``build`` module installed.
    """
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {'headless', 'gui', 'release'}:
        raise ValueError(f'unsupported runtime baseline mode: {mode}')

    platform_name = str(platform_system or platform.system())
    current_version = _python_tuple(version_info)
    current_os = dict(os_release or read_os_release())
    qt_version = pyside_version if pyside_version is not None else _imported_module_version('PySide6')
    has_build = bool(_build_available() if build_available is None else build_available)

    errors: list[str] = []
    warnings: list[str] = []

    if platform_name.lower() != 'linux':
        errors.append(f'{normalized_mode} baseline requires Linux, got {platform_name}')
    if not _is_python_at_least(current_version, major=3, minor=10):
        errors.append(f'{normalized_mode} baseline requires Python >= 3.10, got {_version_string(current_version)}')

    if normalized_mode == 'gui':
        if current_os.get('ID') != 'ubuntu' or current_os.get('VERSION_ID') != '22.04':
            errors.append(
                f'gui baseline requires Ubuntu 22.04, got {current_os.get("ID", "unknown")} {current_os.get("VERSION_ID", "unknown")}'
            )
        if not _is_exact_python(current_version, major=3, minor=10):
            errors.append(f'gui baseline requires Python 3.10, got {_version_string(current_version)}')
        if qt_version is None:
            errors.append('gui baseline requires PySide6 >= 6.5, but PySide6 is unavailable')
        elif not _is_version_at_least(qt_version, major=6, minor=5):
            errors.append(f'gui baseline requires PySide6 >= 6.5, got {qt_version}')
    if normalized_mode == 'release' and not has_build:
        errors.append('release baseline requires the build module (python -m build)')

    return RuntimeBaselineReport(
        mode=normalized_mode,
        platform_system=platform_name,
        python_version=_version_string(current_version),
        os_id=current_os.get('ID'),
        os_version_id=current_os.get('VERSION_ID'),
        pyside_version=qt_version,
        build_available=has_build,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description='Verify repository runtime baseline assumptions.')
    parser.add_argument('--mode', choices=('headless', 'gui', 'release'), default='headless')
    parser.add_argument('--json', action='store_true', help='Emit the evaluation report as JSON')
    args = parser.parse_args(argv)

    report = evaluate_runtime_baseline(args.mode)
    if args.json:
        print(report.to_json())
    else:
        print(f'mode={report.mode}')
        print(f'platform={report.platform_system}')
        print(f'python={report.python_version}')
        print(f'os={report.os_id or "unknown"} {report.os_version_id or "unknown"}')
        print(f'PySide6={report.pyside_version or "missing"}')
        print(f'build={"present" if report.build_available else "missing"}')
        for warning in report.warnings:
            print(f'WARNING: {warning}')
        for error in report.errors:
            print(f'ERROR: {error}')
    return 0 if report.ok else 1


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
