from __future__ import annotations

import pytest

from robot_sim.application.services.execution_scope_service import ExecutionScopeService
from robot_sim.application.services.robot_registry import RobotRegistry


@pytest.fixture()
def planar_spec(project_root):
    return RobotRegistry(project_root / 'configs' / 'robots').load('planar_2dof')


def test_execution_scope_service_enriches_support_matrix(planar_spec) -> None:
    descriptor = ExecutionScopeService().resolve_descriptor(planar_spec, {})
    summary = descriptor.summary()
    metadata = summary['metadata']
    assert summary['strategy'] == 'active_path_over_tree'
    assert metadata['execution_scope_policy'] == 'fail_closed'
    assert metadata['branched_tree_execution_mode'] == 'active_path_over_tree'
    assert metadata['supports_full_tree_execution'] is False
    assert metadata['mobile_base_supported'] is False

    assert metadata['execution_capability_matrix']['supports_active_path_execution'] is True
    assert metadata['execution_capability_matrix']['supports_full_tree_execution'] is False
    assert summary['source_topology']['capability_matrix']['execution_strategy'] == 'active_path_over_tree'
    assert summary['selected_execution_level'] == 'l1_active_path_over_tree'
    assert summary['supported_execution_levels'] == ['l0_serial_tree', 'l1_active_path_over_tree']
    assert metadata['execution_capability_ontology']['ontology_version'] == 'v2'


def test_execution_scope_service_rejects_unsupported_strategy(planar_spec) -> None:
    with pytest.raises(ValueError, match='requested execution scope is incompatible with the current runtime'):
        ExecutionScopeService().resolve_descriptor(planar_spec, {'strategy': 'full_tree'})


def test_execution_scope_service_rejects_closed_loop_override(planar_spec) -> None:
    with pytest.raises(ValueError, match='closed-loop'):
        ExecutionScopeService().resolve_descriptor(planar_spec, {'closed_loop_requested': True})


def test_execution_scope_service_projects_source_selected_and_supported_scope(planar_spec) -> None:
    descriptor = ExecutionScopeService().resolve_descriptor(planar_spec, {'target_links': [planar_spec.runtime_link_names[-1]]})
    summary = descriptor.summary()
    assert summary['source_topology']['joint_names'] == list(planar_spec.runtime_joint_names)
    assert summary['selected_scope']['target_links'] == [planar_spec.runtime_link_names[-1]]
    assert summary['supported_scope']['strategy'] == 'active_path_over_tree'
    assert summary['supported_scope']['allow_joint_subset_selection'] is True
