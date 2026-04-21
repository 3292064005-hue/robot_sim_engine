from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class QualityGateDefinition:
    """Concrete execution contract for one named quality gate.

    Attributes:
        gate_id: Stable gate identifier referenced from governance or benchmark configs.
        description: Human-readable contract summary.
        commands: Concrete commands executed by CI or validation scripts.
        evidence_paths: Repository-relative files that must exist for the gate to be considered
            wired into the repository. These are in addition to the concrete commands.
        environment: Optional environment label such as ``headless`` or ``gui``.
    """

    gate_id: str
    description: str
    commands: tuple[tuple[str, ...], ...] = ()
    evidence_paths: tuple[str, ...] = ()
    environment: str = 'headless'
    layer: str = 'runtime_contracts'
    metadata: dict[str, object] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        """Return a JSON/YAML-safe summary used by docs and governance views."""
        return {
            'gate_id': str(self.gate_id),
            'description': str(self.description),
            'commands': [list(command) for command in self.commands],
            'evidence_paths': list(self.evidence_paths),
            'environment': str(self.environment or 'headless'),
            'layer': str(self.layer or 'runtime_contracts'),
            'metadata': dict(self.metadata or {}),
        }


QUALITY_GATE_CATALOG: dict[str, QualityGateDefinition] = {
    'runtime_contracts': QualityGateDefinition(
        gate_id='runtime_contracts',
        layer='runtime_contracts',
        description='Packaged-config staging plus canonical runtime contract checks.',
        commands=(
            ('python', 'scripts/verify_runtime_contracts.py', '--mode', 'headless', '--check-packaged-configs'),
            ('python', 'scripts/verify_compatibility_retirement.py'),
            ('python', 'scripts/verify_perf_budget_config.py'),
        ),
        evidence_paths=('scripts/verify_runtime_contracts.py', 'scripts/verify_runtime_baseline.py', 'scripts/verify_compatibility_retirement.py', 'configs/release_environment.yaml', 'configs/compatibility_retirement.yaml', 'configs/compatibility_downstream_inventory.yaml', 'docs/compatibility_support_boundary.md', 'docs/compatibility_downstream_inventory.md'),
    ),
    'governance_evidence': QualityGateDefinition(
        gate_id='governance_evidence',
        layer='governance_evidence',
        description='Executed governance and benchmark evidence artifacts.',
        commands=(
            ('python', 'scripts/verify_module_governance.py', '--execute-gates', '--evidence-out', 'artifacts/module_governance_evidence.json'),
            ('python', 'scripts/verify_benchmark_matrix.py', '--execute-gates', '--execute', '--evidence-out', 'artifacts/benchmark_matrix_evidence.json'),
        ),
        evidence_paths=('scripts/verify_module_governance.py', 'scripts/verify_benchmark_matrix.py', 'artifacts'),
    ),
    'quick_quality': QualityGateDefinition(
        gate_id='quick_quality',
        layer='release_blockers',
        description='Tool-aware quick-quality validation with deterministic fallbacks for constrained environments.',
        commands=(( 'python', 'scripts/verify_quick_quality.py'),),
        evidence_paths=('scripts/verify_quick_quality.py', 'scripts/verify_quality_contracts.py', 'docs/generated/quality_gates.md', 'docs/quality_gates.md'),
    ),
    'performance_smoke': QualityGateDefinition(
        gate_id='performance_smoke',
        layer='runtime_contracts',
        description='Measured IK smoke performance budget.',
        commands=(( 'pytest', 'tests/performance/test_ik_smoke.py', '-q'),),
        evidence_paths=('tests/performance/test_ik_smoke.py', 'configs/perf_budgets.yaml'),
    ),
    'gui_smoke': QualityGateDefinition(
        gate_id='gui_smoke',
        layer='release_blockers',
        description='Deterministic offscreen GUI smoke using real PySide6 when available and the repository-local Qt test shim otherwise.',
        commands=(( 'python', 'scripts/verify_gui_smoke.py'),),
        evidence_paths=('scripts/verify_gui_smoke.py', 'src/robot_sim/testing/qt_shims.py', 'tests/gui'),
        environment='gui',
    ),
    'headless_runtime_baseline': QualityGateDefinition(
        gate_id='headless_runtime_baseline',
        layer='runtime_contracts',
        description='Canonical headless runtime baseline.',
        commands=(( 'python', 'scripts/verify_runtime_baseline.py', '--mode', 'headless'),),
        evidence_paths=('scripts/verify_runtime_baseline.py',),
    ),
    'unit_and_regression': QualityGateDefinition(
        gate_id='unit_and_regression',
        layer='release_blockers',
        description='Core unit/regression validation surface.',
        commands=(( 'pytest', 'tests/unit', 'tests/regression', '-q'),),
        evidence_paths=('tests/unit', 'tests/regression'),
    ),
    'compatibility_budget': QualityGateDefinition(
        gate_id='compatibility_budget',
        layer='release_blockers',
        description='Compatibility-budget regression contract.',
        commands=(( 'python', 'scripts/verify_compatibility_budget.py', '--scenario', 'clean_headless_mainline'),),
        evidence_paths=('scripts/verify_compatibility_budget.py', 'tests/unit/test_compatibility_matrix.py'),
    ),
    'docs_sync': QualityGateDefinition(
        gate_id='docs_sync',
        layer='governance_evidence',
        description='Generated contract docs plus semantic doc guards must match the checked-in docs surface.',
        commands=(( 'python', 'scripts/regenerate_quality_contracts.py'), ('python', 'scripts/verify_docs_information_architecture.py')),
        evidence_paths=('scripts/regenerate_quality_contracts.py', 'scripts/verify_docs_information_architecture.py', 'docs/generated/quality_gates.md', 'docs/generated/module_status.md', 'docs/quality_gates.md', 'docs/module_status.md', 'docs/governance/documentation-governance.md'),
    ),
    'planning_scene_regression': QualityGateDefinition(
        gate_id='planning_scene_regression',
        layer='runtime_contracts',
        description='Planning-scene regression tests.',
        commands=(( 'pytest', 'tests/unit/test_planning_scene_v2.py', 'tests/unit/test_scene_authority_service.py', '-q'),),
        evidence_paths=('tests/unit/test_planning_scene_v2.py', 'tests/unit/test_scene_authority_service.py'),
    ),
    'collision_validation_matrix': QualityGateDefinition(
        gate_id='collision_validation_matrix',
        layer='runtime_contracts',
        description='Collision validation coverage matrix.',
        commands=(( 'pytest', 'tests/unit/test_planning_scene_validation.py', 'tests/unit/test_scene_capability_surface.py', '-q'),),
        evidence_paths=('tests/unit/test_planning_scene_validation.py', 'tests/unit/test_scene_capability_surface.py'),
    ),
    'scene_capture_baseline': QualityGateDefinition(
        gate_id='scene_capture_baseline',
        layer='runtime_contracts',
        description='Scene capture fallback/live capability baseline.',
        commands=(( 'pytest', 'tests/unit/test_scene_capture_support.py', 'tests/unit/test_scene_render_contracts.py', '-q'),),
        evidence_paths=('tests/unit/test_scene_capture_support.py', 'tests/unit/test_scene_render_contracts.py'),
    ),
}



def quality_gate_ids_for_layer(layer: str) -> tuple[str, ...]:
    """Return the stable gate ids that belong to one declared gate layer."""
    normalized = str(layer or '').strip()
    return tuple(gate_id for gate_id, definition in QUALITY_GATE_CATALOG.items() if definition.layer == normalized)

def quality_gate_definition(gate_id: str) -> QualityGateDefinition | None:
    """Return the registered gate definition for ``gate_id`` if one exists."""
    return QUALITY_GATE_CATALOG.get(str(gate_id))


def ensure_quality_gates_registered(gate_ids: Iterable[str], *, repo_root: str | Path | None = None) -> list[str]:
    """Validate that each referenced quality gate is defined and wired into the repo.

    Args:
        gate_ids: Stable gate identifiers referenced by governance or benchmark config.
        repo_root: Optional repository root used to verify evidence-path existence.

    Returns:
        list[str]: Validation errors. Empty means every gate is known and wired.

    Boundary behavior:
        Unknown gates and gates missing execution commands are always reported. When
        ``repo_root`` is omitted, filesystem evidence checks are skipped so callers can
        validate catalogs in isolation.
    """
    errors: list[str] = []
    root = Path(repo_root) if repo_root is not None else None
    for gate_id in tuple(str(item) for item in gate_ids):
        definition = quality_gate_definition(gate_id)
        if definition is None:
            errors.append(f'unknown quality gate: {gate_id}')
            continue
        if not definition.commands:
            errors.append(f'quality gate has no execution commands: {gate_id}')
        if root is not None:
            for rel in definition.evidence_paths:
                if not (root / rel).exists():
                    errors.append(f'quality gate evidence path missing: {gate_id} -> {rel}')
    return errors


__all__ = [
    'QUALITY_GATE_CATALOG',
    'QualityGateDefinition',
    'ensure_quality_gates_registered',
    'quality_gate_definition',
    'quality_gate_ids_for_layer',
]
