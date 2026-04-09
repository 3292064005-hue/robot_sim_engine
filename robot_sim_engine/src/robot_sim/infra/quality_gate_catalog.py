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
    metadata: dict[str, object] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        return {
            'gate_id': str(self.gate_id),
            'description': str(self.description),
            'commands': [list(command) for command in self.commands],
            'evidence_paths': list(self.evidence_paths),
            'environment': str(self.environment or 'headless'),
            'metadata': dict(self.metadata or {}),
        }


QUALITY_GATE_CATALOG: dict[str, QualityGateDefinition] = {
    'quick_quality': QualityGateDefinition(
        gate_id='quick_quality',
        description='Static analysis plus headless runtime contracts.',
        commands=(
            ('ruff', 'check', 'src', 'tests'),
            ('mypy',),
            ('python', 'scripts/verify_quality_contracts.py'),
        ),
        evidence_paths=('scripts/verify_quality_contracts.py', 'docs/quality_gates.md'),
    ),
    'performance_smoke': QualityGateDefinition(
        gate_id='performance_smoke',
        description='Measured IK smoke performance budget.',
        commands=(( 'pytest', 'tests/performance/test_ik_smoke.py', '-q'),),
        evidence_paths=('tests/performance/test_ik_smoke.py', 'configs/perf_budgets.yaml'),
    ),
    'gui_smoke': QualityGateDefinition(
        gate_id='gui_smoke',
        description='Offscreen GUI smoke with explicit GUI runtime contract.',
        commands=(
            ('python', 'scripts/verify_runtime_baseline.py', '--mode', 'gui'),
            ('python', 'scripts/verify_release_environment.py', '--mode', 'gui'),
            ('pytest', 'tests/gui', '-q'),
        ),
        evidence_paths=('tests/gui', 'scripts/verify_release_environment.py'),
        environment='gui',
    ),
    'headless_runtime_baseline': QualityGateDefinition(
        gate_id='headless_runtime_baseline',
        description='Canonical headless runtime baseline.',
        commands=(( 'python', 'scripts/verify_runtime_baseline.py', '--mode', 'headless'),),
        evidence_paths=('scripts/verify_runtime_baseline.py',),
    ),
    'unit_and_regression': QualityGateDefinition(
        gate_id='unit_and_regression',
        description='Core unit/regression validation surface.',
        commands=(( 'pytest', 'tests/unit', 'tests/regression', '-q'),),
        evidence_paths=('tests/unit', 'tests/regression'),
    ),
    'compatibility_budget': QualityGateDefinition(
        gate_id='compatibility_budget',
        description='Compatibility-budget regression contract.',
        commands=(( 'python', 'scripts/verify_compatibility_budget.py', '--scenario', 'clean_headless_mainline'),),
        evidence_paths=('scripts/verify_compatibility_budget.py', 'tests/unit/test_compatibility_matrix.py'),
    ),
    'docs_sync': QualityGateDefinition(
        gate_id='docs_sync',
        description='Generated contract docs must match checked-in docs.',
        commands=(( 'python', 'scripts/regenerate_quality_contracts.py'),),
        evidence_paths=('scripts/regenerate_quality_contracts.py', 'docs/quality_gates.md', 'docs/module_status.md'),
    ),
    'planning_scene_regression': QualityGateDefinition(
        gate_id='planning_scene_regression',
        description='Planning-scene regression tests.',
        commands=(( 'pytest', 'tests/unit/test_planning_scene_v2.py', 'tests/unit/test_scene_authority_service.py', '-q'),),
        evidence_paths=('tests/unit/test_planning_scene_v2.py', 'tests/unit/test_scene_authority_service.py'),
    ),
    'collision_validation_matrix': QualityGateDefinition(
        gate_id='collision_validation_matrix',
        description='Collision validation coverage matrix.',
        commands=(( 'pytest', 'tests/unit/test_planning_scene_validation.py', 'tests/unit/test_scene_capability_surface.py', '-q'),),
        evidence_paths=('tests/unit/test_planning_scene_validation.py', 'tests/unit/test_scene_capability_surface.py'),
    ),
    'scene_capture_baseline': QualityGateDefinition(
        gate_id='scene_capture_baseline',
        description='Scene capture fallback/live capability baseline.',
        commands=(( 'pytest', 'tests/unit/test_scene_capture_support.py', 'tests/unit/test_scene_render_contracts.py', '-q'),),
        evidence_paths=('tests/unit/test_scene_capture_support.py', 'tests/unit/test_scene_render_contracts.py'),
    ),
}


def quality_gate_definition(gate_id: str) -> QualityGateDefinition | None:
    return QUALITY_GATE_CATALOG.get(str(gate_id))


def ensure_quality_gates_registered(gate_ids: Iterable[str], *, repo_root: str | Path | None = None) -> list[str]:
    """Return contract errors for missing or unwired quality-gate definitions."""
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
]
