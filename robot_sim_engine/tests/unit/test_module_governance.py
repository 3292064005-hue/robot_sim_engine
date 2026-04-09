from __future__ import annotations

from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.domain.module_governance import verify_experimental_module_governance
from robot_sim.domain.runtime_contracts import MODULE_STATUSES, render_module_status_markdown


def test_experimental_modules_all_have_promotion_policies(project_root) -> None:
    assert verify_experimental_module_governance(MODULE_STATUSES, repo_root=str(project_root)) == []


def test_module_status_service_projects_governance_details() -> None:
    details = ModuleStatusService(runtime_feature_policy=RuntimeFeaturePolicy(active_profile='research', experimental_modules_enabled=True)).snapshot_details()
    collision_panel = details['presentation.widgets.collision_panel']
    assert collision_panel['enabled'] is True
    assert collision_panel['governance']['owner'] == 'presentation-runtime'
    assert 'gui_smoke' in collision_panel['governance']['required_quality_gates']
    assert collision_panel['promotion_ready'] is False
    assert 'gui_smoke' in collision_panel['governance']['missing_quality_gates']


def test_module_status_service_marks_promotion_ready_only_with_gate_results() -> None:
    quality_gate_results = {
        'headless_runtime_baseline': True,
        'unit_and_regression': True,
        'compatibility_budget': True,
        'docs_sync': True,
        'gui_smoke': True,
    }
    details = ModuleStatusService(
        runtime_feature_policy=RuntimeFeaturePolicy(active_profile='research', experimental_modules_enabled=True),
        quality_gate_results=quality_gate_results,
    ).snapshot_details()
    collision_panel = details['presentation.experimental.widgets.collision_panel']
    assert collision_panel['promotion_ready'] is False
    assert collision_panel['governance']['failed_quality_gates'] == []
    assert collision_panel['governance']['missing_quality_gates'] == []
    assert collision_panel['governance']['promotion_blockers']


def test_render_module_status_markdown_includes_governance_for_experimental_modules() -> None:
    markdown = render_module_status_markdown(ModuleStatusService().snapshot_details())
    assert 'owner: `presentation-runtime`' in markdown
    assert 'required_quality_gates:' in markdown
    assert 'promotion_ready:' in markdown


def test_verify_module_governance_requires_executed_gate_results_when_requested(project_root) -> None:
    errors = verify_experimental_module_governance(
        MODULE_STATUSES,
        repo_root=str(project_root),
        gate_results={'headless_runtime_baseline': True},
        require_gate_results=True,
    )
    assert any('missing executed quality gate results' in item for item in errors)


def test_verify_module_governance_reports_failed_gate_results(project_root) -> None:
    errors = verify_experimental_module_governance(
        {'presentation.widgets.collision_panel': 'experimental'},
        repo_root=str(project_root),
        gate_results={
            'headless_runtime_baseline': True,
            'unit_and_regression': True,
            'compatibility_budget': False,
            'docs_sync': True,
            'gui_smoke': True,
        },
        require_gate_results=True,
    )
    assert any('failed executed quality gates' in item for item in errors)
