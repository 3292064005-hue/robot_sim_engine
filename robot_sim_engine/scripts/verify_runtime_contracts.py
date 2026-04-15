from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(command: tuple[str, ...]) -> int:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify runtime-facing repository contracts.')
    parser.add_argument(
        '--mode',
        choices=('headless', 'gui'),
        default='headless',
        help='Contract surface to verify. GUI mode requires real PySide6 and a GUI-capable environment.',
    )
    parser.add_argument('--check-packaged-configs', action='store_true', help='Also verify packaged config staging.')
    args = parser.parse_args()

    commands: list[tuple[str, ...]] = []
    if args.check_packaged_configs:
        commands.append((sys.executable, 'scripts/sync_packaged_configs.py', '--check'))
    commands.append((sys.executable, 'scripts/verify_runtime_baseline.py', '--mode', args.mode))
    if args.mode == 'gui':
        commands.append((sys.executable, 'scripts/verify_release_environment.py', '--mode', 'gui'))

    for command in commands:
        rc = _run(command)
        if rc != 0:
            return rc
    print(f'runtime contracts verified ({args.mode})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
