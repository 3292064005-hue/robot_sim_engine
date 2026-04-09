from __future__ import annotations

from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.core.collision.scene import PlanningScene, SceneObject
import numpy as np


def test_planning_scene_revision_and_object_ids_regression():
    obstacle = SceneObject('fixture', aabb_from_points(np.array([[0, 0, 0], [1, 1, 1]], dtype=float)))
<<<<<<< HEAD
    scene = PlanningScene(obstacles=(obstacle,), revision=9).attach_object('tool', aabb_from_points(np.array([[1, 1, 1], [2, 2, 2]], dtype=float)))
    assert scene.revision == 10
    assert scene.obstacle_ids == ('fixture',)
    assert scene.attached_object_ids == ('tool',)
    summary = scene.summary()
    assert summary['obstacle_ids'] == ['fixture']
    assert summary['attached_object_ids'] == ['tool']
    assert summary['obstacle_count'] == 1
    assert summary['attached_object_count'] == 1
    assert summary['obstacles'][0]['resolved_geometry']['kind'] == 'aabb'
    assert summary['attached_objects'][0]['declared_geometry']['kind'] == 'aabb'
=======
    scene = PlanningScene(obstacles=(obstacle,), revision=9)
    assert scene.revision == 9
    assert scene.obstacle_ids == ('fixture',)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


def test_allowed_collision_matrix_regression():
    acm = AllowedCollisionMatrix.from_pairs([('link_1', 'fixture')])
    assert acm.allows('fixture', 'link_1')
    assert not acm.allows('fixture', 'link_2')
