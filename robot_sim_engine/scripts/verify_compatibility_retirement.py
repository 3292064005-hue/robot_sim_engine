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

from robot_sim.infra.compatibility_retirement import verify_compatibility_retirement_plan  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Verify compatibility retirement inventory and removal checklists.')
    parser.add_argument('--root', type=Path, default=REPO_ROOT, help='Repository root containing configs/compatibility_retirement.yaml')
    args = parser.parse_args(argv)

    errors = verify_compatibility_retirement_plan(args.root / 'configs' / 'compatibility_retirement.yaml')
    if errors:
        for item in errors:
            print(item)
        return 1
    print('compatibility retirement plan verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
