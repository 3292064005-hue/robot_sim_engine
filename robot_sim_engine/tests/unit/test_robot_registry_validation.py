from __future__ import annotations

import pytest
import yaml

from robot_sim.application.services.robot_registry import RobotRegistry


def test_robot_registry_rejects_invalid_joint_limits(tmp_path):
    registry = RobotRegistry(tmp_path)
    payload = {
        'name': 'Bad Robot',
        'home_q': [0.0],
        'dh_rows': [
            {'a': 1.0, 'alpha': 0.0, 'd': 0.0, 'theta_offset': 0.0, 'joint_type': 'revolute', 'q_min': 1.0, 'q_max': -1.0},
        ],
    }
    (tmp_path / 'bad_robot.yaml').write_text(yaml.safe_dump(payload), encoding='utf-8')
    with pytest.raises(ValueError):
        registry.load('bad_robot')


def test_robot_registry_save_normalizes_source_paths_to_relative(project_root, tmp_path):
    source_registry = RobotRegistry(project_root / 'configs' / 'robots')
    writable_registry = RobotRegistry(tmp_path / 'robots', readonly_roots=(project_root / 'configs' / 'robots',))
    spec = source_registry.load('planar_2dof')

    saved = writable_registry.save(spec, name='planar_copy')
    payload = yaml.safe_load(saved.read_text(encoding='utf-8')) or {}

    imported_package = dict(payload.get('imported_package') or {})
    assert imported_package.get('source_path') == 'configs/robots/planar_2dof.yaml'
    geometry_metadata = dict((imported_package.get('geometry_model') or {}).get('metadata') or {})
    assert geometry_metadata.get('source_path') == 'configs/robots/planar_2dof.yaml'
    imported_summary = dict(payload.get('imported_package_summary') or {})
    assert imported_summary.get('source_path') == 'configs/robots/planar_2dof.yaml'
