from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from robot_sim.infra.packaged_config_sync import sync_packaged_configs, verify_packaged_config_sync  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='Stage repository configs into packaged resource trees.')
    parser.add_argument('--root', type=Path, default=PROJECT_ROOT, help='Repository root.')
    parser.add_argument('--check', action='store_true', help='Refresh build staging and verify packaged config parity.')
    args = parser.parse_args()

    summary = sync_packaged_configs(args.root)
    if args.check:
        errors = verify_packaged_config_sync(args.root)
        if errors:
            for item in errors:
                print(item)
            return 1
        print(f"packaged config staging verified copied={summary['copied']} removed={summary['removed']}")
        return 0

    print(f"copied={summary['copied']} removed={summary['removed']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
