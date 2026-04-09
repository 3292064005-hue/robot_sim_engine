from __future__ import annotations
<<<<<<< HEAD

from pathlib import Path

import numpy as np

from robot_sim.application.services.robot_registry import RobotRegistry



=======
import numpy as np
from robot_sim.application.services.robot_registry import RobotRegistry


>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
def test_robot_registry_roundtrip(project_root, tmp_path):
    src = RobotRegistry(project_root / 'configs' / 'robots')
    dst = RobotRegistry(tmp_path)
    spec = src.load('planar_2dof')
    path = dst.save(spec, name='roundtrip_planar')
    loaded = dst.load('roundtrip_planar')
    assert path.exists()
<<<<<<< HEAD
    assert loaded.name == 'roundtrip_planar'
    assert loaded.dof == spec.dof
    assert np.allclose(loaded.home_q, spec.home_q)



def test_robot_registry_lists_and_loads_bundled_readonly_defaults(project_root, tmp_path: Path) -> None:
    registry = RobotRegistry(tmp_path / 'user-robots', readonly_roots=(project_root / 'configs' / 'robots',))

    names = registry.list_names()

    assert 'planar_2dof' in names
    loaded = registry.load('planar_2dof')
    assert loaded.name == 'planar_2dof'
    assert loaded.dof == 2



def test_robot_registry_allows_override_name_when_import_source_is_bundled_default(project_root, tmp_path: Path) -> None:
    bundled_root = project_root / 'configs' / 'robots'
    bundled_path = bundled_root / 'planar_2dof.yaml'
    registry = RobotRegistry(tmp_path / 'user-robots', readonly_roots=(bundled_root,))

    allocated = registry.next_available_name('planar_2dof', exclude_path=bundled_path)

    assert allocated == 'planar_2dof'



def test_robot_registry_avoids_shadowing_bundled_default_for_unrelated_import(project_root, tmp_path: Path) -> None:
    registry = RobotRegistry(tmp_path / 'user-robots', readonly_roots=(project_root / 'configs' / 'robots',))

    allocated = registry.next_available_name('planar_2dof')

    assert allocated == 'planar_2dof_2'
=======
    assert loaded.name == spec.name
    assert loaded.dof == spec.dof
    assert np.allclose(loaded.home_q, spec.home_q)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
