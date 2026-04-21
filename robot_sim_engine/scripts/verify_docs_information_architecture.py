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

from robot_sim.infra.docs_information_architecture import verify_docs_information_architecture  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify docs information architecture metadata, entry pages, and canonical targets.')
    parser.add_argument('--root', type=Path, default=REPO_ROOT, help='Repository root to validate')
    args = parser.parse_args()

    errors = verify_docs_information_architecture(args.root)
    if errors:
        for item in errors:
            print(item)
        return 1
    print('docs information architecture verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
