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
    'runtime_case:yaml_like.clean_scene.ik_planar_smoke.snapshot_capture': BenchmarkTargetContract(
        selector='runtime_case:yaml_like.clean_scene.ik_planar_smoke.snapshot_capture',
        runtime_surface='headless_runtime', importer_variant='yaml_like', scene_variant='clean_scene',
        solver_suite='ik_planar_smoke', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'runtime_case:urdf_skeleton.obstacle_single_box.ik_planar_default_suite.snapshot_capture': BenchmarkTargetContract(
        selector='runtime_case:urdf_skeleton.obstacle_single_box.ik_planar_default_suite.snapshot_capture',
        runtime_surface='headless_runtime', importer_variant='urdf_skeleton', scene_variant='obstacle_single_box',
        solver_suite='ik_planar_default_suite', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'runtime_case:urdf_model.obstacle_dense.trajectory_plan_smoke.snapshot_capture': BenchmarkTargetContract(
        selector='runtime_case:urdf_model.obstacle_dense.trajectory_plan_smoke.snapshot_capture',
        runtime_surface='headless_runtime', importer_variant='urdf_model', scene_variant='obstacle_dense',
        solver_suite='trajectory_plan_smoke', capture_mode='snapshot_capture', execution_environment='headless',
    ),
    'runtime_case:gui_offscreen.urdf_model.clean_scene.live_capture_capability_probe': BenchmarkTargetContract(
        selector='runtime_case:gui_offscreen.urdf_model.clean_scene.live_capture_capability_probe',
        runtime_surface='gui_offscreen', importer_variant='urdf_model', scene_variant='clean_scene',
        solver_suite='ik_planar_smoke', capture_mode='live_capture_capability_probe', execution_environment='gui',
    ),
}


def benchmark_target_contract(selector: str) -> BenchmarkTargetContract | None:
    return BENCHMARK_TARGET_CONTRACTS.get(str(selector))
