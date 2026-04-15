from __future__ import annotations

from robot_sim.infra.compatibility_usage import compatibility_usage_counts, reset_compatibility_usage_counts
from robot_sim.presentation.facades import ExportFacade, RobotFacade, SolverFacade
from robot_sim.presentation.runtime_bundles import WorkflowFacadeBundle, WorkflowServiceBundle


class _RobotWorkflow:
    registry = 'registry'

    def robot_names(self):
        return ['planar']


class _MotionWorkflow:
    ik_use_case = 'ik_uc'

    def solver_defaults(self):
        return {'mode': 'dls'}


class _ExportWorkflow:
    def export_trajectory_bundle(self, name='trajectory_bundle.npz'):
        return name



def test_facade_alias_adapters_preserve_concrete_types_and_record_usage() -> None:
    workflows = WorkflowServiceBundle(
        robot_workflow=_RobotWorkflow(),
        motion_workflow=_MotionWorkflow(),
        export_workflow=_ExportWorkflow(),
    )
    reset_compatibility_usage_counts()
    facades = WorkflowFacadeBundle.from_workflows(workflows)

    assert isinstance(facades.robot_facade, RobotFacade)
    assert isinstance(facades.solver_facade, SolverFacade)
    assert isinstance(facades.export_facade, ExportFacade)
    assert facades.robot_facade.workflow is workflows.robot_workflow
    assert facades.solver_facade.workflow is workflows.motion_workflow
    assert facades.export_facade.workflow is workflows.export_workflow
    assert facades.robot_facade.robot_names() == ['planar']
    assert facades.solver_facade.solver_defaults() == {'mode': 'dls'}
    assert facades.export_facade.export_trajectory_bundle() == 'trajectory_bundle.npz'
    assert facades.solver_facade.ik_use_case == 'ik_uc'
    assert facades.robot_facade.registry == 'registry'

    counts = compatibility_usage_counts()
    assert counts['presentation facade alias adapters'] >= 5
