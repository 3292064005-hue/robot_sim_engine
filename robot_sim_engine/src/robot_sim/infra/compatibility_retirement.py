from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from robot_sim.app.compatibility_matrix import COMPATIBILITY_MATRIX, CompatibilityEntry


@dataclass(frozen=True)
class CompatibilityConsumerRecord:
    consumer_id: str
    scope: str
    usage_kind: str
    status: str
    evidence: str = ''
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            'consumer_id': str(self.consumer_id),
            'scope': str(self.scope),
            'usage_kind': str(self.usage_kind),
            'status': str(self.status),
            'evidence': str(self.evidence or ''),
            'notes': [str(item) for item in self.notes],
        }


@dataclass(frozen=True)
class CompatibilityRetirementEntry:
    surface: str
    owner: str
    removal_target: str
    inventory_scope: str
    out_of_tree_status: str
    migration_owner: str
    inventory_evidence: tuple[str, ...]
    known_consumers: tuple[CompatibilityConsumerRecord, ...]
    removal_checklist: tuple[str, ...]
    rollback_strategy: tuple[str, ...]

    def summary(self) -> dict[str, object]:
        return {
            'surface': str(self.surface),
            'owner': str(self.owner),
            'removal_target': str(self.removal_target),
            'inventory_scope': str(self.inventory_scope),
            'out_of_tree_status': str(self.out_of_tree_status),
            'migration_owner': str(self.migration_owner),
            'inventory_evidence': [str(item) for item in self.inventory_evidence],
            'known_consumers': [item.to_dict() for item in self.known_consumers],
            'removal_checklist': [str(item) for item in self.removal_checklist],
            'rollback_strategy': [str(item) for item in self.rollback_strategy],
        }


@dataclass(frozen=True)
class OutOfTreeAuditRecord:
    audited_on: str
    auditor: str
    evidence: tuple[str, ...]
    observed_consumers: tuple[CompatibilityConsumerRecord, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompatibilityDownstreamInventoryEntry:
    surface: str
    inventory_evidence: tuple[str, ...]
    known_consumers: tuple[CompatibilityConsumerRecord, ...]
    out_of_tree_status: str
    out_of_tree_audit: OutOfTreeAuditRecord


def _consumer_signature(consumer: CompatibilityConsumerRecord) -> tuple[str, str, str, str, str]:
    return (consumer.consumer_id, consumer.scope, consumer.usage_kind, consumer.status, consumer.evidence)


def _load_consumer_records(raw_consumers: object, *, field_name: str) -> tuple[CompatibilityConsumerRecord, ...]:
    consumers: list[CompatibilityConsumerRecord] = []
    for raw_consumer in raw_consumers or ():
        if not isinstance(raw_consumer, Mapping):
            raise ValueError(f'{field_name} entries must be mappings')
        consumers.append(
            CompatibilityConsumerRecord(
                consumer_id=str(raw_consumer.get('consumer_id', '') or ''),
                scope=str(raw_consumer.get('scope', '') or ''),
                usage_kind=str(raw_consumer.get('usage_kind', '') or ''),
                status=str(raw_consumer.get('status', '') or ''),
                evidence=str(raw_consumer.get('evidence', '') or ''),
                notes=tuple(str(note) for note in raw_consumer.get('notes', ()) or ()),
            )
        )
    return tuple(consumers)


def load_compatibility_downstream_inventory(path: str | Path) -> dict[str, CompatibilityDownstreamInventoryEntry]:
    payload = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    if not isinstance(payload, Mapping):
        raise ValueError(f'compatibility downstream inventory must be a mapping: {path}')
    root = payload.get('compatibility_downstream_inventory')
    if not isinstance(root, Mapping):
        raise ValueError(f'compatibility_downstream_inventory root must be a mapping: {path}')
    surfaces = root.get('surfaces')
    if not isinstance(surfaces, list):
        raise ValueError(f'compatibility_downstream_inventory.surfaces must be a list: {path}')
    entries: dict[str, CompatibilityDownstreamInventoryEntry] = {}
    for item in surfaces:
        if not isinstance(item, Mapping):
            raise ValueError('compatibility_downstream_inventory surface entries must be mappings')
        out_of_tree_payload = item.get('out_of_tree_audit', {}) or {}
        if not isinstance(out_of_tree_payload, Mapping):
            raise ValueError('out_of_tree_audit entries must be mappings')
        observed_consumers = _load_consumer_records(
            out_of_tree_payload.get('observed_consumers', ()) or (),
            field_name='observed_consumers',
        )
        entry = CompatibilityDownstreamInventoryEntry(
            surface=str(item.get('surface', '') or ''),
            inventory_evidence=tuple(str(value) for value in item.get('inventory_evidence', ()) or ()),
            known_consumers=_load_consumer_records(item.get('known_consumers', ()) or (), field_name='known_consumers'),
            out_of_tree_status=str(item.get('out_of_tree_status', '') or ''),
            out_of_tree_audit=OutOfTreeAuditRecord(
                audited_on=str(out_of_tree_payload.get('audited_on', '') or ''),
                auditor=str(out_of_tree_payload.get('auditor', '') or ''),
                evidence=tuple(str(value) for value in out_of_tree_payload.get('evidence', ()) or ()),
                observed_consumers=observed_consumers,
                notes=tuple(str(note) for note in out_of_tree_payload.get('notes', ()) or ()),
            ),
        )
        if entry.surface in entries:
            raise ValueError(f'duplicate compatibility downstream inventory surface: {entry.surface}')
        entries[entry.surface] = entry
    return entries


_ALLOWED_OUT_OF_TREE_STATUSES = {'audited_absent', 'confirmed'}
_ALLOWED_CONSUMER_SCOPES = {'in_repo', 'out_of_tree'}
_ALLOWED_CONSUMER_STATUSES = {'active', 'deprecated', 'pending_removal'}
_ALLOWED_INVENTORY_SCOPES = {'audited_downstream_inventory'}
_REQUIRED_SUPPORT_BOUNDARY_EVIDENCE = 'docs/compatibility_support_boundary.md'
_REQUIRED_DOWNSTREAM_INVENTORY_CONFIG = 'configs/compatibility_downstream_inventory.yaml'
_REQUIRED_DOWNSTREAM_INVENTORY_DOC = 'docs/compatibility_downstream_inventory.md'


def load_compatibility_retirement_plan(path: str | Path) -> dict[str, CompatibilityRetirementEntry]:
    payload = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    if not isinstance(payload, Mapping):
        raise ValueError(f'compatibility retirement plan must be a mapping: {path}')
    root = payload.get('compatibility_retirement')
    if not isinstance(root, list):
        raise ValueError(f'compatibility_retirement root must be a list: {path}')
    entries: dict[str, CompatibilityRetirementEntry] = {}
    for item in root:
        if not isinstance(item, Mapping):
            raise ValueError('compatibility_retirement entries must be mappings')
        entry = CompatibilityRetirementEntry(
            surface=str(item.get('surface', '') or ''),
            owner=str(item.get('owner', '') or ''),
            removal_target=str(item.get('removal_target', '') or ''),
            inventory_scope=str(item.get('inventory_scope', '') or ''),
            out_of_tree_status=str(item.get('out_of_tree_status', '') or ''),
            migration_owner=str(item.get('migration_owner', '') or ''),
            inventory_evidence=tuple(str(value) for value in item.get('inventory_evidence', ()) or ()),
            known_consumers=_load_consumer_records(item.get('known_consumers', ()) or (), field_name='known_consumers'),
            removal_checklist=tuple(str(check) for check in item.get('removal_checklist', ()) or ()),
            rollback_strategy=tuple(str(step) for step in item.get('rollback_strategy', ()) or ()),
        )
        if entry.surface in entries:
            raise ValueError(f'duplicate compatibility retirement surface: {entry.surface}')
        entries[entry.surface] = entry
    return entries


def verify_compatibility_retirement_plan(path: str | Path) -> list[str]:
    plan_path = Path(path)
    repo_root = plan_path.resolve().parents[1] if plan_path.name == 'compatibility_retirement.yaml' and plan_path.parent.name == 'configs' else plan_path.resolve().parent
    entries = load_compatibility_retirement_plan(plan_path)
    downstream_inventory_path = repo_root / _REQUIRED_DOWNSTREAM_INVENTORY_CONFIG
    downstream_entries = load_compatibility_downstream_inventory(downstream_inventory_path)
    errors: list[str] = []
    matrix_by_surface: dict[str, CompatibilityEntry] = {entry.surface: entry for entry in COMPATIBILITY_MATRIX}

    for surface in sorted(matrix_by_surface):
        if surface not in entries:
            errors.append(f'missing retirement-plan entry for compatibility surface: {surface}')
        if surface not in downstream_entries:
            errors.append(f'missing downstream-inventory entry for compatibility surface: {surface}')
    for surface in sorted(entries):
        if surface not in matrix_by_surface:
            errors.append(f'retirement-plan entry declared for unknown compatibility surface: {surface}')
            continue
        entry = entries[surface]
        matrix = matrix_by_surface[surface]
        downstream = downstream_entries.get(surface)
        if entry.owner != matrix.owner:
            errors.append(f'{surface}: retirement owner drifted from compatibility matrix: expected {matrix.owner}, got {entry.owner}')
        if entry.removal_target != matrix.removal_target:
            errors.append(f'{surface}: removal target drifted from compatibility matrix: expected {matrix.removal_target}, got {entry.removal_target}')
        if entry.inventory_scope not in _ALLOWED_INVENTORY_SCOPES:
            errors.append(f'{surface}: invalid inventory_scope {entry.inventory_scope!r}')
        if entry.out_of_tree_status not in _ALLOWED_OUT_OF_TREE_STATUSES:
            errors.append(f'{surface}: invalid out_of_tree_status {entry.out_of_tree_status!r}')
        if not entry.migration_owner:
            errors.append(f'{surface}: migration_owner is required')
        if len(entry.inventory_evidence) < 1:
            errors.append(f'{surface}: inventory_evidence must contain at least one concrete source of truth')
        if not entry.known_consumers:
            errors.append(f'{surface}: known_consumers must not be empty')
        if len(entry.removal_checklist) < 3:
            errors.append(f'{surface}: removal_checklist must contain at least three explicit steps')
        if len(entry.rollback_strategy) < 1:
            errors.append(f'{surface}: rollback_strategy must contain at least one explicit step')
        for evidence_path in entry.inventory_evidence:
            if not (repo_root / evidence_path).exists():
                errors.append(f'{surface}: inventory evidence path does not exist: {evidence_path}')
        if downstream is None:
            continue
        if entry.inventory_scope != 'audited_downstream_inventory':
            errors.append(f'{surface}: retirement inventory scope must be audited_downstream_inventory')
        if entry.out_of_tree_status != downstream.out_of_tree_status:
            errors.append(f'{surface}: out_of_tree_status drifted from downstream inventory: expected {downstream.out_of_tree_status}, got {entry.out_of_tree_status}')
        if tuple(entry.inventory_evidence) != tuple(downstream.inventory_evidence):
            errors.append(f'{surface}: inventory_evidence drifted from downstream inventory')
        if {_consumer_signature(c) for c in entry.known_consumers} != {_consumer_signature(c) for c in downstream.known_consumers}:
            errors.append(f'{surface}: known_consumers drifted from downstream inventory')
        if entry.out_of_tree_status == 'audited_absent':
            if downstream.out_of_tree_audit.observed_consumers:
                errors.append(f'{surface}: audited_absent cannot declare out_of_tree observed consumers')
            for required_path in (_REQUIRED_SUPPORT_BOUNDARY_EVIDENCE, _REQUIRED_DOWNSTREAM_INVENTORY_CONFIG, _REQUIRED_DOWNSTREAM_INVENTORY_DOC):
                if required_path not in entry.inventory_evidence:
                    errors.append(f'{surface}: audited downstream inventory must cite {required_path}')
        if entry.out_of_tree_status == 'confirmed' and not downstream.out_of_tree_audit.observed_consumers:
            errors.append(f'{surface}: out_of_tree_status confirmed requires at least one observed out_of_tree consumer')
        if not downstream.out_of_tree_audit.audited_on:
            errors.append(f'{surface}: downstream inventory must record out_of_tree_audit.audited_on')
        if not downstream.out_of_tree_audit.auditor:
            errors.append(f'{surface}: downstream inventory must record out_of_tree_audit.auditor')
        if not downstream.out_of_tree_audit.evidence:
            errors.append(f'{surface}: downstream inventory must record out_of_tree audit evidence')
        for evidence_path in downstream.out_of_tree_audit.evidence:
            if not (repo_root / evidence_path).exists():
                errors.append(f'{surface}: out_of_tree audit evidence path does not exist: {evidence_path}')
        for consumer in entry.known_consumers:
            if not consumer.consumer_id:
                errors.append(f'{surface}: known consumer is missing consumer_id')
            if consumer.consumer_id.startswith('release_review/'):
                errors.append(f'{surface}: consumer {consumer.consumer_id!r} must be replaced with a concrete inventory record')
            if consumer.scope not in _ALLOWED_CONSUMER_SCOPES:
                errors.append(f'{surface}: consumer {consumer.consumer_id!r} has invalid scope {consumer.scope!r}')
            if not consumer.usage_kind:
                errors.append(f'{surface}: consumer {consumer.consumer_id!r} must declare usage_kind')
            if consumer.status not in _ALLOWED_CONSUMER_STATUSES:
                errors.append(f'{surface}: consumer {consumer.consumer_id!r} has invalid status {consumer.status!r}')
            if not consumer.evidence:
                errors.append(f'{surface}: consumer {consumer.consumer_id!r} must declare evidence')
            elif not (repo_root / consumer.evidence).exists():
                errors.append(f'{surface}: consumer {consumer.consumer_id!r} evidence path does not exist: {consumer.evidence}')
        for consumer in downstream.out_of_tree_audit.observed_consumers:
            if consumer.scope != 'out_of_tree':
                errors.append(f'{surface}: observed out_of_tree consumer {consumer.consumer_id!r} must use scope out_of_tree')
            if consumer.status not in _ALLOWED_CONSUMER_STATUSES:
                errors.append(f'{surface}: observed out_of_tree consumer {consumer.consumer_id!r} has invalid status {consumer.status!r}')
            if not consumer.evidence:
                errors.append(f'{surface}: observed out_of_tree consumer {consumer.consumer_id!r} must declare evidence')
    return errors
