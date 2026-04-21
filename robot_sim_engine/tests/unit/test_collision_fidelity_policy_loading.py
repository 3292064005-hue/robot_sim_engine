from __future__ import annotations

from pathlib import Path

from robot_sim.domain import collision_fidelity as fidelity_mod
from robot_sim.domain.enums import CollisionLevel


def test_collision_fidelity_policy_reports_loaded_source_and_accepts_external_override(tmp_path: Path, monkeypatch) -> None:
    policy_path = tmp_path / 'collision_fidelity.yaml'
    policy_path.write_text(
        'contract_version: v9\n'
        'roadmap_owner: qa\n'
        'levels:\n'
        '  none:\n'
        '    collision_level: none\n'
        '    precision: none\n'
        '    stable_surface: false\n'
        '    promotion_state: disabled\n'
        '    summary: disabled\n'
        '  aabb:\n'
        '    collision_level: aabb\n'
        '    precision: broad_phase\n'
        '    stable_surface: true\n'
        '    promotion_state: stable\n'
        '    summary: custom aabb\n'
        '    roadmap_stage: stable\n'
        '    stable_surface_target: stable\n'
        '    geometry_requirements: [declaration_projection]\n'
        '    degradation_policy: native_broad_phase\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('ROBOT_SIM_COLLISION_FIDELITY_CONFIG', str(policy_path))
    fidelity_mod.collision_fidelity_policy.cache_clear()
    fidelity_mod._descriptor_table.cache_clear()

    policy = fidelity_mod.collision_fidelity_policy()
    descriptor = fidelity_mod.collision_fidelity_descriptor(CollisionLevel.AABB)

    assert policy['contract_version'] == 'v9'
    assert policy['policy_source'] == str(policy_path)
    assert descriptor.summary == 'custom aabb'

    fidelity_mod.collision_fidelity_policy.cache_clear()
    fidelity_mod._descriptor_table.cache_clear()
