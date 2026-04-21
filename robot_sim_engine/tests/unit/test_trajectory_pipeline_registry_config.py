from __future__ import annotations

import numpy as np

from robot_sim.app.container import build_container
from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.pipelines.trajectory_pipeline_registry import build_trajectory_pipeline_registry
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.model.solver_config import TrajectoryPipelineConfig


def test_trajectory_pipeline_registry_builds_config_defined_pipeline() -> None:
    registry = build_trajectory_pipeline_registry(
        (
            TrajectoryPipelineConfig(),
            TrajectoryPipelineConfig(
                pipeline_id='research_fast_path',
                retime_stage_id='no_retime',
                validate_stage_id='validate_goal_only',
                postprocessor_stage_ids=('noop_postprocessor',),
                metadata={'profile_scope': 'research'},
            ),
        )
    )
    assert registry.ids() == ['default', 'research_fast_path']
    pipeline = registry.get('research_fast_path')
    assert pipeline.retime_stage.stage_id == 'no_retime'
    assert pipeline.validate_stage.stage_id == 'validate_goal_only'
    assert pipeline.metadata['profile_scope'] == 'research'
    assert pipeline.metadata['configured_externally'] is True



def test_trajectory_pipeline_registry_builds_declared_stage_catalog_pipeline() -> None:
    registry = build_trajectory_pipeline_registry(
        (
            TrajectoryPipelineConfig(),
            TrajectoryPipelineConfig(
                pipeline_id='external_validate_path',
                validate_stage_id='validate_layers_only',
                postprocessor_stage_ids=('noop_external',),
            ),
        ),
        stage_catalog=(
            {
                'id': 'validate_layers_only',
                'kind': 'validate',
                'factory': 'robot_sim.application.pipelines.trajectory_stage_factories:build_validate_stage',
                'metadata': {'layer_override': ['timing']},
            },
            {
                'id': 'noop_external',
                'kind': 'postprocessor',
                'factory': 'robot_sim.application.pipelines.trajectory_stage_factories:build_noop_postprocessor_stage',
            },
        ),
    )
    pipeline = registry.get('external_validate_path')
    assert pipeline.validate_stage.stage_id == 'validate_layers_only'
    assert pipeline.postprocessors[0].stage_id == 'noop_external'
    assert pipeline.metadata['stage_catalog_enabled'] is True



def test_container_profile_can_select_config_defined_pipeline(project_root, monkeypatch) -> None:
    monkeypatch.setenv('ROBOT_SIM_PROFILE', 'research')
    container = build_container(project_root)
    settings = container.config_service.load_solver_settings()
    assert settings.trajectory.pipeline_id == 'research_fast_path'
    spec = container.robot_registry.load('planar_2dof')
    traj = container.traj_uc.execute(
        TrajectoryRequest(
            q_start=np.asarray(spec.home_q, dtype=float),
            q_goal=np.asarray(spec.q_mid(), dtype=float),
            duration=1.0,
            dt=0.05,
            spec=spec,
            pipeline_id=settings.trajectory.pipeline_id,
        )
    )
    assert traj.metadata['pipeline_id'] == 'research_fast_path'
    assert traj.metadata['retimer_id'] == 'no_retime'
    assert traj.metadata['validation_stage'] == 'validate_goal_only'


def test_trajectory_stage_catalog_respects_profile_capability_policy_and_fallbacks() -> None:
    registry = build_trajectory_pipeline_registry(
        (
            TrajectoryPipelineConfig(
                pipeline_id='policy_path',
                validate_stage_id='validate_layers_only',
                postprocessor_stage_ids=('post_external',),
            ),
        ),
        stage_catalog=(
            {
                'id': 'validate_layers_only',
                'provider_id': 'provider.validate_layers_only',
                'kind': 'validate',
                'factory': 'robot_sim.application.pipelines.trajectory_stage_factories:build_validate_stage',
                'status': 'beta',
                'enabled_profiles': ['research'],
                'required_host_capabilities': ['trajectory_stage_provider:v1', 'profile:research'],
                'metadata': {'layer_override': ['timing']},
                'fallback_stage_id': 'validate_goal_only',
            },
            {
                'id': 'post_external',
                'provider_id': 'provider.post_external',
                'kind': 'postprocessor',
                'factory': 'robot_sim.application.pipelines.trajectory_stage_factories:build_noop_postprocessor_stage',
                'status': 'stable',
                'enabled_profiles': ['research'],
                'required_host_capabilities': ['trajectory_stage_provider:v1', 'profile:research'],
            },
        ),
        runtime_feature_policy=RuntimeFeaturePolicy(
            active_profile='research',
            experimental_modules_enabled=True,
            plugin_status_allowlist=('stable', 'beta', 'deprecated'),
        ),
    )
    pipeline = registry.get('policy_path')
    assert pipeline.validate_stage.stage_id == 'validate_layers_only'
    assert pipeline.postprocessors[0].stage_id == 'post_external'
    provider_catalog = pipeline.metadata['stage_provider_catalog']
    assert provider_catalog['enabled_provider_count'] >= 2
    providers = {row['provider_id']: row for row in provider_catalog['providers']}
    assert providers['provider.validate_layers_only']['enabled'] is True
    assert providers['provider.validate_layers_only']['reason'] == 'enabled'

    fallback_registry = build_trajectory_pipeline_registry(
        (
            TrajectoryPipelineConfig(
                pipeline_id='fallback_path',
                validate_stage_id='validate_layers_only',
            ),
        ),
        stage_catalog=(
            {
                'id': 'validate_layers_only',
                'provider_id': 'provider.validate_layers_only',
                'kind': 'validate',
                'factory': 'robot_sim.application.pipelines.trajectory_stage_factories:build_validate_stage',
                'status': 'experimental',
                'enabled_profiles': ['research'],
                'required_host_capabilities': ['trajectory_stage_provider:v1', 'profile:research', 'experimental_modules'],
                'fallback_stage_id': 'validate_goal_only',
            },
        ),
        runtime_feature_policy=RuntimeFeaturePolicy(
            active_profile='research',
            experimental_modules_enabled=False,
            plugin_status_allowlist=('stable', 'beta', 'deprecated'),
        ),
    )
    fallback_pipeline = fallback_registry.get('fallback_path')
    assert fallback_pipeline.validate_stage.stage_id == 'validate_goal_only'
    assert fallback_pipeline.metadata['stage_resolution']['validate']['fallback_stage_id'] == 'validate_goal_only'
    fallback_rows = {row['provider_id']: row for row in fallback_pipeline.metadata['stage_provider_catalog']['providers']}
    assert fallback_rows['provider.validate_layers_only']['enabled'] is False
    assert fallback_rows['provider.validate_layers_only']['reason'] in {'status_disabled', 'required_host_capability_missing'}
