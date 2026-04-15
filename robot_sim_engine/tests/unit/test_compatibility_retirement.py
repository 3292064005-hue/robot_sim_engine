from __future__ import annotations

from pathlib import Path

from robot_sim.infra.compatibility_retirement import (
    load_compatibility_downstream_inventory,
    load_compatibility_retirement_plan,
    verify_compatibility_retirement_plan,
)


def test_checked_in_compatibility_retirement_plan_is_valid(project_root: Path) -> None:
    config_path = project_root / 'configs' / 'compatibility_retirement.yaml'
    entries = load_compatibility_retirement_plan(config_path)
    assert 'presentation facade alias adapters' in entries
    assert verify_compatibility_retirement_plan(config_path) == []


DOWNSTREAM_INVENTORY_CONFIG = 'configs/compatibility_downstream_inventory.yaml'
DOWNSTREAM_INVENTORY_DOC = 'docs/compatibility_downstream_inventory.md'
SUPPORT_BOUNDARY_DOC = 'docs/compatibility_support_boundary.md'


def test_checked_in_compatibility_retirement_plan_has_audited_downstream_inventory_contract(project_root: Path) -> None:
    config_path = project_root / 'configs' / 'compatibility_retirement.yaml'
    entries = load_compatibility_retirement_plan(config_path)
    downstream = load_compatibility_downstream_inventory(project_root / DOWNSTREAM_INVENTORY_CONFIG)
    for surface, entry in entries.items():
        assert entry.inventory_scope == 'audited_downstream_inventory'
        assert entry.out_of_tree_status == 'audited_absent'
        assert DOWNSTREAM_INVENTORY_CONFIG in entry.inventory_evidence
        assert DOWNSTREAM_INVENTORY_DOC in entry.inventory_evidence
        assert SUPPORT_BOUNDARY_DOC in entry.inventory_evidence
        assert entry.inventory_evidence
        assert all(not consumer.consumer_id.startswith('release_review/') for consumer in entry.known_consumers)
        assert {consumer.consumer_id for consumer in entry.known_consumers} == {consumer.consumer_id for consumer in downstream[surface].known_consumers}
        assert downstream[surface].out_of_tree_audit.observed_consumers == ()


def test_compatibility_retirement_plan_requires_audited_downstream_inventory_contract(tmp_path: Path) -> None:
    config_dir = tmp_path / 'configs'
    docs_dir = tmp_path / 'docs'
    config_dir.mkdir()
    docs_dir.mkdir()
    (docs_dir / 'compatibility_support_boundary.md').write_text('boundary', encoding='utf-8')
    (docs_dir / 'compatibility_downstream_inventory.md').write_text('inventory doc', encoding='utf-8')
    (config_dir / 'compatibility_downstream_inventory.yaml').write_text(
        """compatibility_downstream_inventory:
  audited_release: v0
  audited_on: 2026-04-14
  auditor: qa
  surfaces:
    - surface: bootstrap iterable unpacking
      out_of_tree_status: audited_absent
      inventory_evidence:
        - configs/compatibility_downstream_inventory.yaml
        - docs/compatibility_downstream_inventory.md
        - docs/compatibility_support_boundary.md
      known_consumers:
        - consumer_id: tests/unit/example.py::test_surface
          scope: in_repo
          usage_kind: bootstrap_destructuring_regression
          status: deprecated
          evidence: tests/unit/example.py
      out_of_tree_audit:
        audited_on: 2026-04-14
        auditor: qa
        evidence:
          - docs/compatibility_support_boundary.md
        observed_consumers: []
""",
        encoding='utf-8',
    )
    config_path = config_dir / 'compatibility_retirement.yaml'
    config_path.write_text(
        """compatibility_retirement:
  - surface: bootstrap iterable unpacking
    owner: robot_sim.app.bootstrap.bootstrap
    removal_target: v0.9
    inventory_scope: audited_downstream_inventory
    out_of_tree_status: audited_absent
    migration_owner: runtime
    inventory_evidence:
      - docs/compatibility_support_boundary.md
    known_consumers:
      - consumer_id: release_review/bootstrap_destructuring_audit
        scope: in_repo
        usage_kind: audit_placeholder
        status: deprecated
        evidence: tests/unit/example.py
    removal_checklist:
      - one
      - two
      - three
    rollback_strategy:
      - rollback
""",
        encoding='utf-8',
    )
    errors = verify_compatibility_retirement_plan(config_path)
    assert any('must cite configs/compatibility_downstream_inventory.yaml' in item for item in errors)
    assert any('must cite docs/compatibility_downstream_inventory.md' in item for item in errors)
    assert any('must be replaced with a concrete inventory record' in item for item in errors)
    assert any('known_consumers drifted from downstream inventory' in item for item in errors)
