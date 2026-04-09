from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _configure_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / 'src'
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_configure_path()

from robot_sim.infra.release_environment_gate import ReleaseEnvironmentGate  # noqa: E402
from robot_sim.infra.release_package import build_release_zip  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Build a clean release zip excluding caches and local artifacts.')
    parser.add_argument('--root', type=Path, default=REPO_ROOT, help='Repository root to package')
    parser.add_argument('--output', type=Path, required=True, help='Output zip path')
    parser.add_argument('--top-level-dir', type=str, default=None, help='Optional top-level directory inside zip')
    parser.add_argument('--allow-unsupported-environment', action='store_true', help='Package even when the checked-in release environment contract is not satisfied')
    args = parser.parse_args()

    gate = ReleaseEnvironmentGate(args.root / 'configs' / 'release_environment.yaml')
    report = gate.evaluate('release')
    if not args.allow_unsupported_environment and not report.ok:
        for warning in report.warnings:
            print(f'WARNING: {warning}')
        for error in report.errors:
            print(f'ERROR: {error}')
        raise SystemExit('release packaging requires a verified release environment; pass --allow-unsupported-environment to override')
    archive = build_release_zip(args.root, args.output, top_level_dir=args.top_level_dir)
    print(archive)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
