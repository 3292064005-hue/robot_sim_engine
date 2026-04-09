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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify release or GUI environment against the checked-in contract.')
    parser.add_argument('--mode', choices=('release', 'gui'), default='release')
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    gate = ReleaseEnvironmentGate(repo_root / 'configs' / 'release_environment.yaml')
    report = gate.evaluate(args.mode)
    for warning in report.warnings:
        print(f'WARNING: {warning}')
    for error in report.errors:
        print(f'ERROR: {error}')
    if report.ok:
        print(f'{args.mode} environment verified')
        raise SystemExit(0)
    raise SystemExit(1)
