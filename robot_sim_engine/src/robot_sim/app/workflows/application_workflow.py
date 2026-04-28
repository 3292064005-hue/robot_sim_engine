from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.application.dto import FKRequest
from robot_sim.application.request_builders import build_ik_request, build_trajectory_request
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService
from robot_sim.application.services.scene_session_authority import SceneSessionAuthority
from robot_sim.core.collision.scene import PlanningScene
from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.model.execution_graph import ExecutionGraphDescriptor
from robot_sim.model.pose import Pose
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.session_state import SessionState
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.runtime_snapshots import RuntimeContextSnapshot, StartupSummarySnapshot

from .import_resolution import ResolvedImportBundle, resolve_import, resolve_spec_reference
from .session_projection import build_session_state as build_session_state_projection
from .session_projection import imported_robot_result_from_loaded as project_imported_robot_result

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.app.container import AppContainer, AppRegistryBundle, AppServiceBundle, AppWorkflowBundle
    from robot_sim.model.benchmark_report import BenchmarkReport


@dataclass(frozen=True)
class ApplicationWorkflowFacade:
    """Single application workflow façade shared by GUI and headless surfaces."""

    registries: 'AppRegistryBundle'
    services: 'AppServiceBundle'
    workflows: 'AppWorkflowBundle'
    runtime_context: RuntimeContextSnapshot | None = None
    startup_summary: StartupSummarySnapshot | None = None
    validate_uc: ValidateTrajectoryUseCase = ValidateTrajectoryUseCase()

    @classmethod
    def from_container(cls, container: 'AppContainer') -> 'ApplicationWorkflowFacade':
        return cls(
            registries=container.registry_bundle,
            services=container.service_bundle,
            workflows=container.workflow_bundle,
            runtime_context=getattr(container, 'runtime_context', None),
            startup_summary=getattr(container, 'startup_summary', None),
        )

    @property
    def runtime_asset_service(self) -> RobotRuntimeAssetService:
        runtime_asset_service = getattr(self.services, 'runtime_asset_service', None)
        if runtime_asset_service is None:  # pragma: no cover - defensive fallback
            runtime_feature_policy = getattr(self.services, 'runtime_feature_policy', None)
            runtime_asset_service = RobotRuntimeAssetService(
                experimental_collision_backends_enabled=bool(
                    getattr(runtime_feature_policy, 'experimental_backends_enabled', False)
                )
            )
            runtime_asset_service.bind_runtime_context(
                profile_id=str(getattr(getattr(self.services, 'config_service', None), 'profile', 'default') or 'default'),
                collision_backend_scope='experimental' if bool(getattr(runtime_feature_policy, 'experimental_backends_enabled', False)) else 'stable',
                experimental_collision_backends_enabled=bool(getattr(runtime_feature_policy, 'experimental_backends_enabled', False)),
            )
        return runtime_asset_service

    def robot_names(self) -> list[str]:
        return self.registries.robot_registry.list_names()

    def robot_entries(self):
        return self.registries.robot_registry.list_entries()

    def available_specs(self):
        return self.registries.robot_registry.list_specs()

    def importer_entries(self):
        return list(self.registries.importer_registry.descriptors())

    def load_robot_spec(self, name: str) -> RobotSpec:
        return self.registries.robot_registry.load(name)

    def resolve_spec_reference(
        self,
        *,
        robot: str | None = None,
        source: str | Path | None = None,
        importer_id: str | None = None,
    ) -> RobotSpec:
        return resolve_spec_reference(self, robot=robot, source=source, importer_id=importer_id)

    def resolve_import(
        self,
        source: str | Path,
        *,
        importer_id: str | None = None,
        persist: bool,
    ) -> ResolvedImportBundle:
        return resolve_import(self, source, importer_id=importer_id, persist=persist)

    def run_fk(self, spec: RobotSpec, q) -> object:
        return self.workflows.fk_uc.execute(FKRequest(spec, np.asarray(q, dtype=float)))

    def run_ik(
        self,
        spec: RobotSpec,
        *,
        target: Pose,
        q0,
        config: IKConfig,
        execution_graph: ExecutionGraphDescriptor,
    ) -> object:
        request = build_ik_request(
            spec=spec,
            target=target,
            q0=np.asarray(q0, dtype=float),
            config=config,
            execution_graph=execution_graph,
        )
        return self.workflows.ik_uc.execute(request)

    @staticmethod
    def _planning_scene_input(planning_scene, fallback_scene) -> tuple[PlanningScene | None, str]:
        """Resolve the canonical planning scene for one application workflow call.

        Args:
            planning_scene: Caller/session scene supplied by GUI, headless, or session replay.
            fallback_scene: Baseline runtime scene produced from the robot specification.

        Returns:
            tuple[object | None, str]: The scene to pass into request/validation boundaries and
            a stable source label. ``caller_scene`` is always preferred when supplied; otherwise
            the runtime-derived baseline is used.

        Raises:
            ValueError: If a caller or fallback scene is not a ``PlanningScene`` instance.

        Boundary behavior:
            The runtime asset cache is a materialization source, not the session scene truth. This
            method therefore never lets a rebuilt asset scene override an explicit caller scene.
        """
        resolution = SceneSessionAuthority.resolve(
            planning_scene=planning_scene,
            fallback_scene=fallback_scene,
        )
        return resolution.scene, resolution.source

    def plan_trajectory(
        self,
        spec: RobotSpec,
        *,
        q_start,
        q_goal,
        duration: float,
        dt: float,
        mode,
        target_pose: Pose | None,
        ik_config: IKConfig | None,
        planner_id: str | None,
        max_velocity: float | None,
        max_acceleration: float | None,
        validation_layers: tuple[str, ...] | None,
        pipeline_id: str | None,
        execution_graph: ExecutionGraphDescriptor,
        robot_geometry: RobotGeometry | None = None,
        collision_geometry: RobotGeometry | None = None,
        planning_scene=None,
    ) -> JointTrajectory:
        if planning_scene is not None and not isinstance(planning_scene, PlanningScene):
            raise ValueError('planning_scene must be a PlanningScene instance or None')
        scene_materialization_revision_key = (
            SceneSessionAuthority.revision_key(planning_scene, source='caller_scene')
            if planning_scene is not None
            else None
        )
        assets = self.runtime_asset_service.build_assets(
            spec,
            robot_geometry=robot_geometry,
            collision_geometry=collision_geometry,
            scene_materialization_revision_key=scene_materialization_revision_key,
        )
        resolved_scene, planning_scene_source = self._planning_scene_input(planning_scene, assets.planning_scene)
        request = build_trajectory_request(
            q_start=np.asarray(q_start, dtype=float),
            q_goal=None if q_goal is None else np.asarray(q_goal, dtype=float),
            duration=duration,
            dt=dt,
            spec=spec,
            mode=mode,
            target_pose=target_pose,
            ik_config=ik_config,
            planner_id=planner_id,
            max_velocity=max_velocity,
            max_acceleration=max_acceleration,
            planning_scene=resolved_scene,
            planning_scene_source=planning_scene_source,
            validation_layers=validation_layers,
            pipeline_id=pipeline_id,
            execution_graph=execution_graph,
        )
        return self.workflows.traj_uc.execute(request)

    def validate_trajectory(
        self,
        spec: RobotSpec,
        trajectory: JointTrajectory,
        *,
        target_pose: Pose | None,
        q_goal,
        validation_layers: tuple[str, ...] | None,
        robot_geometry: RobotGeometry | None = None,
        collision_geometry: RobotGeometry | None = None,
        planning_scene=None,
    ):
        if planning_scene is not None and not isinstance(planning_scene, PlanningScene):
            raise ValueError('planning_scene must be a PlanningScene instance or None')
        scene_materialization_revision_key = (
            SceneSessionAuthority.revision_key(planning_scene, source='caller_scene')
            if planning_scene is not None
            else None
        )
        assets = self.runtime_asset_service.build_assets(
            spec,
            robot_geometry=robot_geometry,
            collision_geometry=collision_geometry,
            scene_materialization_revision_key=scene_materialization_revision_key,
        )
        resolved_scene, planning_scene_source = self._planning_scene_input(planning_scene, assets.planning_scene)
        normalized_q_goal = None if q_goal is None else np.asarray(q_goal, dtype=float)
        return self.validate_uc.execute(
            trajectory,
            target_pose=target_pose,
            spec=spec,
            q_goal=normalized_q_goal,
            planning_scene=resolved_scene,
            planning_scene_source=planning_scene_source,
            validation_layers=validation_layers,
        )

    def run_benchmark(
        self,
        spec: RobotSpec,
        *,
        config: IKConfig,
        execution_graph: ExecutionGraphDescriptor,
    ) -> 'BenchmarkReport':
        return self.workflows.benchmark_uc.execute(spec, config, execution_graph=execution_graph)

    def export_session(self, name: str, state: SessionState, **kwargs):
        return self.workflows.save_session_uc.execute(name, state, **kwargs)

    def export_package(self, name: str, files: list[Path], **manifest_kwargs):
        return self.workflows.export_package_uc.execute(name, files, **manifest_kwargs)

    def export_trajectory_bundle(
        self,
        name: str,
        trajectory: JointTrajectory,
        *,
        robot_id: str | None = None,
        solver_id: str | None = None,
        planner_id: str | None = None,
    ) -> Path:
        """Persist a trajectory artifact through the canonical export service."""
        return self.services.export_service.save_trajectory_bundle(
            name,
            trajectory,
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=planner_id,
        )

    def export_benchmark_report(self, name: str, payload: dict[str, object]) -> Path:
        """Persist a benchmark payload through the canonical export service."""
        return self.services.export_service.save_benchmark_report(name, payload)

    def build_session_state(
        self,
        spec: RobotSpec,
        *,
        q_current,
        trajectory: JointTrajectory | None = None,
        benchmark_report: BenchmarkReport | None = None,
        robot_geometry: RobotGeometry | None = None,
        collision_geometry: RobotGeometry | None = None,
        planning_scene=None,
    ) -> SessionState:
        return build_session_state_projection(
            self,
            spec,
            q_current=q_current,
            trajectory=trajectory,
            benchmark_report=benchmark_report,
            robot_geometry=robot_geometry,
            collision_geometry=collision_geometry,
            planning_scene=planning_scene,
        )

    def imported_robot_result_from_loaded(
        self,
        resolved: ResolvedImportBundle,
        *,
        fk_result,
        loaded_spec: RobotSpec,
    ):
        return project_imported_robot_result(
            resolved,
            fk_result=fk_result,
            loaded_spec=loaded_spec,
        )
