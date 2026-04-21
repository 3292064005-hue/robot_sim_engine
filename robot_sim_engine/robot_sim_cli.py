from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run the source-tree CLI without relying on a repository-root package shim.

    Args:
        argv: Optional argument vector forwarded to the canonical CLI entrypoint.

    Returns:
        int: Process exit code from ``robot_sim.app.cli.main``.

    Raises:
        None: Import/runtime failures propagate from the canonical CLI module.
    """
    repo_root = Path(__file__).resolve().parent
    src_root = repo_root / 'src'
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from robot_sim.app.cli import main as cli_main

    return int(cli_main(argv))


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
