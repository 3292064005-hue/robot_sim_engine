from __future__ import annotations

from types import SimpleNamespace

import pytest

from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene
from robot_sim.presentation.scene_ui_support import (
    build_default_scene_obstacle_request,
    format_allowed_collision_pairs,
    format_vector,
    parse_allowed_collision_pairs_text,
    parse_vector_text,
)


def test_scene_ui_support_builds_default_request_from_target_pose():
    runtime_state = SimpleNamespace(
        target_pose=SimpleNamespace(p=(0.5, 0.1, 0.2)),
        fk_result=None,
        planning_scene=PlanningScene().add_obstacle('obstacle', AABB([-0.1, -0.1, -0.1], [0.1, 0.1, 0.1])),
    )

    request = build_default_scene_obstacle_request(runtime_state)

    assert request['object_id'] == 'obstacle_2'
    assert request['center'] == (0.5, 0.1, 0.2)
    assert request['size'] == (0.2, 0.2, 0.2)


def test_scene_ui_support_parses_vectors_and_collision_pairs_deterministically():
    assert format_vector((0.5, 0.0, 0.25)) == '0.500 0.000 0.250'
    assert parse_vector_text('0.5, 0, 0.25', field_name='center') == (0.5, 0.0, 0.25)
    pairs = parse_allowed_collision_pairs_text('tool, fixture\nfixture, link_1\n')
    assert pairs == (('fixture', 'tool'), ('fixture', 'link_1'))
    assert format_allowed_collision_pairs(pairs) == 'fixture, tool\nfixture, link_1'


@pytest.mark.parametrize('text', ['1 2', '1 2 3 4', '1 foo 3'])
def test_scene_ui_support_rejects_invalid_vector_fields(text):
    with pytest.raises(ValueError):
        parse_vector_text(text, field_name='center')
