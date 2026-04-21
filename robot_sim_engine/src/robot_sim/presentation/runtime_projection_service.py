from __future__ import annotations

from dataclasses import dataclass

from robot_sim.application.dto import FKRequest
from robot_sim.application.services.runtime_asset_service import RobotRuntimeAssetService, RobotRuntimeAssets
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.domain.enums import AppExecutionState
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.presentation.state_events import RobotRuntimeLoadedEvent
from robot_sim.presentation.state_store import StateStore


@dataclass(frozen=True)
class RuntimeRobotLoadResult:
    """Stable projection result for loading one robot spec into runtime state."""

    runtime_assets: RobotRuntimeAssets
    fk_result: object
    scene_revision: int


class RuntimeProjectionService:
    """Project robot/runtime assets into the presentation state store.

    This service removes repeated controller-side wiring between FK projection, runtime asset
    construction, state-store patching, and canonical scene installation.
    """

    def __init__(
        self,
        state_store: StateStore,
        fk_uc: RunFKUseCase,
        *,
        runtime_asset_service: RobotRuntimeAssetService | None = None,
    ) -> None:
        self._state_store = state_store
        self._fk_uc = fk_uc
        self._runtime_asset_service = runtime_asset_service or RobotRuntimeAssetService()

    def load_robot_spec(
        self,
        spec: RobotSpec,
        *,
        robot_geometry=None,
        collision_geometry=None,
    ) -> RuntimeRobotLoadResult:
        """Load one robot specification into the presentation runtime.

        Args:
            spec: Canonical robot specification.
            robot_geometry: Optional visual geometry override.
            collision_geometry: Optional collision geometry override.

        Returns:
            RuntimeRobotLoadResult: FK result, runtime assets, and installed scene revision.

        Raises:
            ValueError: Propagates FK validation and runtime-asset errors.
        """
        fk = self._fk_uc.execute(FKRequest(spec, spec.home_q.copy()))
        self._runtime_asset_service.invalidate(spec, reason='runtime_projection_reload')
        runtime_assets = self._runtime_asset_service.build_assets(
            spec,
            robot_geometry=robot_geometry,
            collision_geometry=collision_geometry,
        )
        scene_revision = max(
            int(self._state_store.state.scene_revision) + 1,
            int(getattr(runtime_assets.planning_scene, 'revision', 0)),
        )
        self._state_store.dispatch(
            RobotRuntimeLoadedEvent(
                spec=spec,
                q_current=spec.home_q.copy(),
                fk_result=fk,
                scene_revision=scene_revision,
                robot_geometry=runtime_assets.robot_geometry,
                collision_geometry=runtime_assets.collision_geometry,
                planning_scene=runtime_assets.planning_scene,
                scene_summary=runtime_assets.scene_summary,
                app_state=AppExecutionState.ROBOT_READY,
            )
        )
        return RuntimeRobotLoadResult(runtime_assets=runtime_assets, fk_result=fk, scene_revision=scene_revision)
