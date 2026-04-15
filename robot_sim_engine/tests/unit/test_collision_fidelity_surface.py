from __future__ import annotations

from robot_sim.core.collision.scene import PlanningScene
from robot_sim.domain.collision_fidelity import collision_fidelity_descriptor, summarize_collision_fidelity
from robot_sim.domain.enums import CollisionLevel


def test_collision_fidelity_descriptor_reports_stable_surface_for_aabb() -> None:
    descriptor = collision_fidelity_descriptor(CollisionLevel.AABB)
    assert descriptor.collision_level == 'aabb'
    assert descriptor.stable_surface is True
    assert descriptor.promotion_state == 'stable'


def test_summarize_collision_fidelity_projects_backend_and_precision() -> None:
    summary = summarize_collision_fidelity(
        collision_level=CollisionLevel.CAPSULE,
        collision_backend='capsule',
        scene_fidelity='runtime_approximation',
        experimental_backends_enabled=True,
    )
    assert summary['collision_level'] == 'capsule'
    assert summary['precision'] == 'capsule_narrow_phase'
    assert summary['promotion_state'] == 'profile_gated'
    assert summary['scene_fidelity'] == 'runtime_approximation'


def test_planning_scene_summary_exposes_collision_fidelity_descriptor() -> None:
    scene = PlanningScene().with_collision_backend('aabb')
    summary = scene.summary()
    fidelity = dict(summary['collision_fidelity'])
    assert fidelity['collision_backend'] == 'aabb'
    assert fidelity['precision'] == 'broad_phase'
    assert fidelity['promotion_state'] == 'stable'
