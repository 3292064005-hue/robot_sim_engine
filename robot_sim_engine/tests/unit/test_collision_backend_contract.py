from __future__ import annotations

import numpy as np

from robot_sim.core.collision.capsule_backend import CapsuleCollisionBackend
from robot_sim.core.collision.geometry import AABB


def test_capsule_backend_contract_reports_enabled_status_and_supported_ops():
    backend = CapsuleCollisionBackend()
    payload = backend.check_state_collision(np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float))
    assert backend.backend_id == 'capsule'
    assert payload['backend_id'] == 'capsule'
    assert payload['availability'] == 'enabled'
    assert payload['fallback_backend'] == 'aabb'
    assert payload['reason'] == ''
    assert payload['supported'] is True
    assert set(payload['supported_operations']) == {'state_collision', 'path_collision', 'min_distance', 'contact_pairs'}


def test_capsule_backend_detects_environment_collision_for_segment_capsule():
    backend = CapsuleCollisionBackend()
    obstacle = AABB(minimum=np.array([0.45, -0.05, -0.05]), maximum=np.array([0.55, 0.05, 0.05]))
    payload = backend.check_state_collision(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float),
        obstacles=[('wall', obstacle)],
        link_names=['link_0'],
        link_radii=[0.02],
    )
    assert payload['environment_collision'] is True
    assert ('link_0', 'wall') in payload['environment_pairs']
    assert payload['clearance_metric'] <= 0.0
