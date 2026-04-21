from __future__ import annotations

from robot_sim.core.collision.scene import PlanningScene
from robot_sim.domain.collision_fidelity import collision_fidelity_descriptor, summarize_collision_fidelity
from robot_sim.domain.enums import CollisionLevel


def test_collision_fidelity_descriptor_reports_stable_surface_for_aabb() -> None:
    descriptor = collision_fidelity_descriptor(CollisionLevel.AABB)
    assert descriptor.collision_level == 'aabb'
    assert descriptor.stable_surface is True
    assert descriptor.promotion_state == 'stable'
    assert descriptor.roadmap_stage == 'stable'
    assert descriptor.geometry_requirements == ('declaration_projection', 'query_aabb')


def test_summarize_collision_fidelity_projects_backend_and_precision() -> None:
    summary = summarize_collision_fidelity(
        collision_level=CollisionLevel.CAPSULE,
        collision_backend='capsule',
        scene_fidelity='runtime_approximation',
        experimental_backends_enabled=True,
    )
    assert summary['collision_level'] == 'capsule'
    assert summary['precision'] == 'capsule_narrow_phase'
    assert summary['promotion_state'] == 'stable'
    assert summary['roadmap_stage'] == 'stable'
    assert summary['stable_surface_target'] == 'stable'
    assert summary['geometry_requirements'] == ['capsule_primitives', 'link_radii']
    assert summary['degradation_policy'] == 'fallback_to_aabb_when_capsule_contract_missing'
    assert summary['scene_fidelity'] == 'runtime_approximation'
    assert summary['capability_contract_version'] == 'v2'
    assert summary['policy_source']


def test_planning_scene_summary_exposes_collision_fidelity_descriptor() -> None:
    scene = PlanningScene().with_collision_backend('aabb')
    summary = scene.summary()
    fidelity = dict(summary['collision_fidelity'])
    assert fidelity['collision_backend'] == 'aabb'
    assert fidelity['precision'] == 'broad_phase'
    assert fidelity['promotion_state'] == 'stable'
    assert fidelity['roadmap_stage'] == 'stable'
    assert fidelity['capability_contract_version'] == 'v2'
