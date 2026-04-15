"""Source-tree import shim for ``python -m robot_sim.app.cli`` development workflows.

This package exists only at repository root. Installed wheels continue to import the real
package from ``src/robot_sim``. During source-tree execution the shim redirects package
submodule resolution into ``src/robot_sim`` so the canonical CLI entrypoint works without
manually exporting ``PYTHONPATH=src``.
"""
from __future__ import annotations

from pathlib import Path

_src_package = Path(__file__).resolve().parent.parent / 'src' / 'robot_sim'
if _src_package.is_dir():
    __path__ = [str(_src_package)]
else:  # pragma: no cover
    __path__ = []
