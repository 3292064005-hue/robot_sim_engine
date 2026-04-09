from __future__ import annotations
<<<<<<< HEAD

from pathlib import Path

import pytest

from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.infra.qt_runtime import configure_qt_platform_for_pytest


configure_qt_platform_for_pytest()

=======
from pathlib import Path
import pytest

from robot_sim.application.services.robot_registry import RobotRegistry
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

<<<<<<< HEAD

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
@pytest.fixture
def planar_spec(project_root):
    return RobotRegistry(project_root / "configs" / "robots").load("planar_2dof")

<<<<<<< HEAD

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
@pytest.fixture
def puma_spec(project_root):
    return RobotRegistry(project_root / "configs" / "robots").load("puma_like_6dof")
