from __future__ import annotations

from pathlib import Path

from robot_sim.infra.compatibility_retirement import (
    load_compatibility_downstream_inventory,
    load_compatibility_retirement_plan,
    verify_compatibility_retirement_plan,
)


def test_checked_in_compatibility_retirement_plan_is_empty_and_valid(project_root: Path) -> None:
    config_path = project_root / 'configs' / 'compatibility_retirement.yaml'
    entries = load_compatibility_retirement_plan(config_path)
    assert entries == {}
    assert verify_compatibility_retirement_plan(config_path) == []


def test_checked_in_compatibility_downstream_inventory_is_empty(project_root: Path) -> None:
    inventory = load_compatibility_downstream_inventory(project_root / 'configs' / 'compatibility_downstream_inventory.yaml')
    assert inventory == {}


def test_compatibility_retirement_plan_rejects_unknown_surface_when_matrix_is_empty(tmp_path: Path) -> None:
    config_dir = tmp_path / 'configs'
    docs_dir = tmp_path / 'docs'
    config_dir.mkdir()
    docs_dir.mkdir()
    (docs_dir / 'compatibility_support_boundary.md').write_text('boundary', encoding='utf-8')
    (docs_dir / 'compatibility_downstream_inventory.md').write_text('inventory doc', encoding='utf-8')
    (config_dir / 'compatibility_downstream_inventory.yaml').write_text(
        """compatibility_downstream_inventory:
  audited_release: v0
  audited_on: 2026-04-15
  auditor: qa
  surfaces: []
""",
        encoding='utf-8',
    )
    config_path = config_dir / 'compatibility_retirement.yaml'
    config_path.write_text(
        """compatibility_retirement:
  - surface: obsolete_surface
    owner: owner
    removal_target: v0.9
    inventory_scope: audited_downstream_inventory
    out_of_tree_status: audited_absent
    migration_owner: runtime
    inventory_evidence: []
    known_consumers: []
    removal_checklist: [one, two, three]
    rollback_strategy: [rollback]
""",
        encoding='utf-8',
    )
    errors = verify_compatibility_retirement_plan(config_path)
    assert any('unknown compatibility surface' in item for item in errors)
