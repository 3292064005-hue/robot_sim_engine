from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from robot_sim.infra.quality_gate_catalog import ensure_quality_gates_registered


@dataclass(frozen=True)
class ModulePromotionPolicy:
    """Promotion policy attached to an experimental runtime module."""

    owner: str
    stable_ui_surface: str = ''
    exit_criteria: tuple[str, ...] = ()
    required_quality_gates: tuple[str, ...] = ()
    promotion_blockers: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def evaluate(self, gate_results: Mapping[str, bool] | None = None) -> dict[str, object]:
        results = {str(key): bool(value) for key, value in dict(gate_results or {}).items()}
        missing_quality_gates = [gate for gate in self.required_quality_gates if gate not in results]
        failed_quality_gates = [gate for gate in self.required_quality_gates if gate in results and not results[gate]]
        active_promotion_blockers = [str(item) for item in self.promotion_blockers if str(item).strip()]
        promotion_ready = not missing_quality_gates and not failed_quality_gates and not active_promotion_blockers
        return {
            'owner': str(self.owner),
            'stable_ui_surface': str(self.stable_ui_surface or ''),
            'exit_criteria': [str(item) for item in self.exit_criteria],
            'required_quality_gates': [str(item) for item in self.required_quality_gates],
            'promotion_blockers': active_promotion_blockers,
            'notes': [str(item) for item in self.notes],
            'metadata': dict(self.metadata or {}),
            'missing_quality_gates': missing_quality_gates,
            'failed_quality_gates': failed_quality_gates,
            'promotion_ready': bool(promotion_ready),
        }

    def summary(self) -> dict[str, object]:
        return self.evaluate({})


DEFAULT_PROMOTION_GATES: tuple[str, ...] = (
    'headless_runtime_baseline',
    'unit_and_regression',
    'compatibility_budget',
    'docs_sync',
)

RENDER_PROMOTION_GATES: tuple[str, ...] = DEFAULT_PROMOTION_GATES + ('gui_smoke', 'scene_capture_baseline')
COLLISION_PROMOTION_GATES: tuple[str, ...] = DEFAULT_PROMOTION_GATES + ('planning_scene_regression', 'collision_validation_matrix')
WIDGET_PROMOTION_GATES: tuple[str, ...] = DEFAULT_PROMOTION_GATES + ('gui_smoke',)

EXPERIMENTAL_MODULE_GOVERNANCE: dict[str, ModulePromotionPolicy] = {
    'core.collision.capsule_backend': ModulePromotionPolicy(
        owner='collision-runtime',
        stable_ui_surface='planning_scene',
        exit_criteria=(
            'capsule backend must remain within the configured compatibility budget',
            'collision backend contract tests must pass on clean headless mainline',
            'planning-scene regression and validation baselines must stay reproducible',
        ),
        required_quality_gates=COLLISION_PROMOTION_GATES,
        promotion_blockers=(
            'backend is still profile-gated and not advertised on the stable capability surface by default',
            'scene authority still defaults to AABB for stable runtime validation',
        ),
        notes=('promotion requires stable capsule fidelity claims in docs and export/session surfaces',),
    ),
    'presentation.widgets.collision_panel': ModulePromotionPolicy(
        owner='presentation-runtime',
        stable_ui_surface='main_window_ui',
        exit_criteria=(
            'widget must mount through the stable main window builder without experimental aliases',
            'task orchestration must remain on explicit coordinator dependency routes',
        ),
        required_quality_gates=WIDGET_PROMOTION_GATES,
        promotion_blockers=('stable UI intentionally hides the panel until promotion criteria are satisfied',),
    ),
    'presentation.widgets.export_panel': ModulePromotionPolicy(
        owner='presentation-runtime',
        stable_ui_surface='main_window_ui',
        exit_criteria=(
            'export widget must project only through stable view contracts',
            'background export worker lifecycle must remain intact under GUI smoke',
        ),
        required_quality_gates=WIDGET_PROMOTION_GATES,
        promotion_blockers=('stable UI intentionally hides the panel until promotion criteria are satisfied',),
    ),
    'presentation.widgets.scene_options_panel': ModulePromotionPolicy(
        owner='presentation-runtime',
        stable_ui_surface='main_window_ui',
        exit_criteria=(
            'scene options widget must consume typed scene authority summaries only',
            'GUI smoke and planning-scene regressions must remain green',
        ),
        required_quality_gates=WIDGET_PROMOTION_GATES,
        promotion_blockers=('stable UI intentionally hides the panel until promotion criteria are satisfied',),
    ),
    'presentation.experimental.widgets.collision_panel': ModulePromotionPolicy(
        owner='presentation-runtime',
        stable_ui_surface='main_window_ui',
        exit_criteria=('legacy experimental namespace must be removed before stable exposure',),
        required_quality_gates=WIDGET_PROMOTION_GATES,
        promotion_blockers=('legacy experimental namespace retained only for migration compatibility',),
    ),
    'presentation.experimental.widgets.export_panel': ModulePromotionPolicy(
        owner='presentation-runtime',
        stable_ui_surface='main_window_ui',
        exit_criteria=('legacy experimental namespace must be removed before stable exposure',),
        required_quality_gates=WIDGET_PROMOTION_GATES,
        promotion_blockers=('legacy experimental namespace retained only for migration compatibility',),
    ),
    'presentation.experimental.widgets.scene_options_panel': ModulePromotionPolicy(
        owner='presentation-runtime',
        stable_ui_surface='main_window_ui',
        exit_criteria=('legacy experimental namespace must be removed before stable exposure',),
        required_quality_gates=WIDGET_PROMOTION_GATES,
        promotion_blockers=('legacy experimental namespace retained only for migration compatibility',),
    ),
    'render.picking': ModulePromotionPolicy(
        owner='render-runtime',
        stable_ui_surface='scene_3d_widget',
        exit_criteria=(
            'picking must expose provenance-aware diagnostics in render runtime state',
            'GUI smoke must verify picking does not degrade screenshot fallback semantics',
        ),
        required_quality_gates=RENDER_PROMOTION_GATES,
        promotion_blockers=('stable render pipeline still defaults to placeholder/snapshot fallback when live picking is unavailable',),
    ),
    'render.plot_sync': ModulePromotionPolicy(
        owner='render-runtime',
        stable_ui_surface='scene_3d_widget',
        exit_criteria=(
            'plot sync must not bypass typed render telemetry projections',
            'GUI smoke must validate sync lifecycle under offscreen Qt runtime',
        ),
        required_quality_gates=RENDER_PROMOTION_GATES,
        promotion_blockers=('plot sync remains disabled outside experimental profiles',),
    ),
    'render.experimental.picking': ModulePromotionPolicy(
        owner='render-runtime',
        stable_ui_surface='scene_3d_widget',
        exit_criteria=('legacy experimental namespace must be removed before stable exposure',),
        required_quality_gates=RENDER_PROMOTION_GATES,
        promotion_blockers=('legacy experimental namespace retained only for compatibility',),
    ),
    'render.experimental.plot_sync': ModulePromotionPolicy(
        owner='render-runtime',
        stable_ui_surface='scene_3d_widget',
        exit_criteria=('legacy experimental namespace must be removed before stable exposure',),
        required_quality_gates=RENDER_PROMOTION_GATES,
        promotion_blockers=('legacy experimental namespace retained only for compatibility',),
    ),
}


def governance_for_module(module_id: str) -> ModulePromotionPolicy | None:
    return EXPERIMENTAL_MODULE_GOVERNANCE.get(str(module_id))


def verify_experimental_module_governance(
    module_statuses: Mapping[str, str],
    *,
    repo_root: str | None = None,
    gate_results: Mapping[str, bool] | None = None,
    require_gate_results: bool = False,
) -> list[str]:
    """Verify that every experimental module has an explicit promotion policy and optionally enforce executed gate results."""
    errors: list[str] = []
    normalized_gate_results = {str(key): bool(value) for key, value in dict(gate_results or {}).items()}
    experimental_modules = {str(module_id) for module_id, status in dict(module_statuses).items() if str(status) == 'experimental'}
    governed_modules = set(EXPERIMENTAL_MODULE_GOVERNANCE)
    for module_id in sorted(experimental_modules - governed_modules):
        errors.append(f'missing promotion policy for experimental module: {module_id}')
    for module_id in sorted(governed_modules - experimental_modules):
        errors.append(f'promotion policy declared for non-experimental module: {module_id}')
    for module_id in sorted(experimental_modules & governed_modules):
        policy = EXPERIMENTAL_MODULE_GOVERNANCE[module_id]
        if not str(policy.owner).strip():
            errors.append(f'experimental module promotion policy missing owner: {module_id}')
        if not tuple(policy.exit_criteria):
            errors.append(f'experimental module promotion policy missing exit criteria: {module_id}')
        if not tuple(policy.required_quality_gates):
            errors.append(f'experimental module promotion policy missing required quality gates: {module_id}')
        errors.extend(
            f'{module_id}: {error}' for error in ensure_quality_gates_registered(policy.required_quality_gates, repo_root=repo_root)
        )
        if require_gate_results:
            evaluation = policy.evaluate(normalized_gate_results)
            missing = tuple(str(item) for item in evaluation.get('missing_quality_gates', ()) or ())
            failed = tuple(str(item) for item in evaluation.get('failed_quality_gates', ()) or ())
            if missing:
                errors.append(f'{module_id}: missing executed quality gate results: {list(missing)!r}')
            if failed:
                errors.append(f'{module_id}: failed executed quality gates: {list(failed)!r}')
    return errors
