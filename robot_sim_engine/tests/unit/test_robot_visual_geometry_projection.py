from __future__ import annotations

import numpy as np

from robot_sim.model.robot_geometry import GeometryPrimitive, LinkGeometry, RobotGeometry
from robot_sim.render.robot_visual import RobotVisual


def test_robot_visual_describes_runtime_geometry_links():
    points = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.5, 0.0, 0.0]], dtype=float)
    geometry = RobotGeometry(
        links=(
            LinkGeometry(name='base', radius=0.05, visual_primitives=(GeometryPrimitive(kind='box', params={'size': '0.2 0.3 1.0'}),)),
            LinkGeometry(name='tip', radius=0.04, visual_primitives=(GeometryPrimitive(kind='sphere', params={'radius': '0.1'}),)),
        ),
        source='urdf_model',
        fidelity='serial_with_visual',
        collision_backend_hint='capsule',
    )
    visual = RobotVisual()

    descriptors = visual.describe_renderables(points, robot_geometry=geometry)

    assert len(descriptors) == 2
    assert descriptors[0]['kind'] == 'box'
    assert descriptors[0]['link_name'] == 'base'
    assert np.allclose(descriptors[0]['center'], [0.5, 0.0, 0.0])
    assert descriptors[1]['kind'] == 'sphere'
    assert descriptors[1]['link_name'] == 'tip'


def test_robot_visual_falls_back_to_capsules_without_geometry():
    points = np.asarray([[0.0, 0.0, 0.0], [0.0, 0.5, 0.0]], dtype=float)
    visual = RobotVisual()

    descriptors = visual.describe_renderables(points, robot_geometry=None)

    assert len(descriptors) == 1
    assert descriptors[0]['kind'] == 'capsule'
    assert float(descriptors[0]['length']) == 0.5
