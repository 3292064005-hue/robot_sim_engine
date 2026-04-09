from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkTargetContract:
    selector: str
    runtime_surface: str
    importer_variant: str
    scene_variant: str
    solver_suite: str
    capture_mode: str
    execution_environment: str = 'headless'

    def summary(self) -> dict[str, str]:
        return {
            'selector': self.selector,
            'runtime_surface': self.runtime_surface,
            'importer_variant': self.importer_variant,
            'scene_variant': self.scene_variant,
            'solver_suite': self.solver_suite,
            'capture_mode': self.capture_mode,
            'execution_environment': self.execution_environment,
        }


BENCHMARK_TARGET_CONTRACTS: dict[str, BenchmarkTargetContract] = {
    'tests/integration/test_ik_planar.py::test_dls_ik_planar_reachable': BenchmarkTargetContract(
        selector='tests/integration/test_ik_planar.py::test_dls_ik_planar_reachable',
        runtime_surface='headless_runtime', importer_variant='yaml_like', scene_variant='clean_scene',
        solver_suite='ik_planar_smoke', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'tests/performance/test_ik_smoke.py::test_ik_smoke_produces_stable_elapsed_statistics': BenchmarkTargetContract(
        selector='tests/performance/test_ik_smoke.py::test_ik_smoke_produces_stable_elapsed_statistics',
        runtime_surface='headless_runtime', importer_variant='yaml_like', scene_variant='clean_scene',
        solver_suite='ik_planar_smoke', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'tests/unit/test_importer_fidelity_levels.py::test_yaml_and_urdf_importers_expose_fidelity': BenchmarkTargetContract(
        selector='tests/unit/test_importer_fidelity_levels.py::test_yaml_and_urdf_importers_expose_fidelity',
        runtime_surface='headless_runtime', importer_variant='urdf_skeleton', scene_variant='obstacle_single_box',
        solver_suite='ik_planar_default_suite', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'tests/unit/test_scene_authority_service.py::test_scene_authority_service_applies_obstacle_and_allowed_pairs': BenchmarkTargetContract(
        selector='tests/unit/test_scene_authority_service.py::test_scene_authority_service_applies_obstacle_and_allowed_pairs',
        runtime_surface='headless_runtime', importer_variant='urdf_skeleton', scene_variant='obstacle_single_box',
        solver_suite='ik_planar_default_suite', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'tests/integration/test_import_robot_into_scene_pipeline.py::test_imported_robot_bundle_can_seed_planning_scene': BenchmarkTargetContract(
        selector='tests/integration/test_import_robot_into_scene_pipeline.py::test_imported_robot_bundle_can_seed_planning_scene',
        runtime_surface='headless_runtime', importer_variant='urdf_model', scene_variant='obstacle_dense',
        solver_suite='trajectory_plan_smoke', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'tests/integration/test_trajectory_pipeline_lifecycle.py::test_trajectory_pipeline_runs_joint_quintic_end_to_end': BenchmarkTargetContract(
        selector='tests/integration/test_trajectory_pipeline_lifecycle.py::test_trajectory_pipeline_runs_joint_quintic_end_to_end',
        runtime_surface='headless_runtime', importer_variant='urdf_model', scene_variant='obstacle_dense',
        solver_suite='trajectory_plan_smoke', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'tests/gui/test_scene_capture_offscreen.py::test_scene_widget_snapshot_available_without_plotter': BenchmarkTargetContract(
        selector='tests/gui/test_scene_capture_offscreen.py::test_scene_widget_snapshot_available_without_plotter',
        runtime_surface='gui_offscreen', importer_variant='urdf_model', scene_variant='clean_scene',
        solver_suite='ik_planar_smoke', capture_mode='live_capture_capability_probe', execution_environment='gui',
    ),
    'tests/gui/test_scene_render_runtime_offscreen.py::test_scene_widget_exposes_render_runtime_snapshot_offscreen': BenchmarkTargetContract(
        selector='tests/gui/test_scene_render_runtime_offscreen.py::test_scene_widget_exposes_render_runtime_snapshot_offscreen',
        runtime_surface='gui_offscreen', importer_variant='urdf_model', scene_variant='clean_scene',
        solver_suite='ik_planar_smoke', capture_mode='live_capture_capability_probe', execution_environment='gui',
    ),
}


def benchmark_target_contract(selector: str) -> BenchmarkTargetContract | None:
    return BENCHMARK_TARGET_CONTRACTS.get(str(selector))
