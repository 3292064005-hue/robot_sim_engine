from __future__ import annotations

from pathlib import Path
import sys

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / 'src'))

from robot_sim.infra.packaged_config_sync import install_packaged_configs, sync_packaged_configs  # noqa: E402


class build_py(_build_py):
    """Build command that installs packaged configs into the build-lib output tree.

    The repository now keeps ``configs/`` as the single checked-in config source of truth.
    Packaging stages a build-local mirror under ``build/packaged_config_staging`` for
    verification and copies the same files directly into ``build_lib/robot_sim/resources``
    for wheel/sdist output.
    """

    def run(self) -> None:
        sync_packaged_configs(REPO_ROOT)
        super().run()
        install_packaged_configs(self.build_lib, REPO_ROOT)


setup(cmdclass={'build_py': build_py})
