from __future__ import annotations

import numpy as np

from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.presentation.runtime_projection_service import RuntimeProjectionService
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.workflow_services import RobotWorkflowService

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.app.workflow_facade import ApplicationWorkflowFacade


class RobotController:
    """Legacy compatibility adapter for robot workflow operations.

    New presentation startup paths must depend on ``RobotWorkflowService`` directly. This class is
    kept only for downstream imports and compatibility tests; it does not own robot-editing,
    import, FK, or runtime-projection business logic. All public methods delegate to the canonical
    workflow service so no second source of truth can diverge from the active presentation graph.
    """

    LEGACY_SURFACE_ID = 'robot_controller_compat_adapter_v2'

    def __init__(
        self,
        state_store: StateStore,
        registry: RobotRegistry,
        fk_uc: RunFKUseCase,
        import_robot_uc=None,
        *,
        runtime_projection_service: RuntimeProjectionService | None = None,
        runtime_asset_service=None,
        application_workflow: 'ApplicationWorkflowFacade | None' = None,
    ) -> None:
        """Create a legacy robot-controller adapter.

        Args:
            state_store: Presentation state store shared with the canonical workflow.
            registry: Robot registry used by save/load operations.
            fk_uc: FK use case used by runtime projection.
            import_robot_uc: Retained for historical constructor compatibility.
            runtime_projection_service: Optional canonical runtime projector. A service is created
                only for compatibility callers that instantiate this adapter directly.
            runtime_asset_service: Optional runtime-asset service used when creating a projection
                service for direct compatibility callers.
            application_workflow: Required for import/load/FK operations that cross into the
                application layer.

        Returns:
            None: Stores only an adapter-owned workflow reference.

        Raises:
            None: Runtime configuration errors are raised by delegated workflow calls.

        Boundary behavior:
            This adapter is intentionally excluded from the active startup graph. Direct callers get
            the same behavior as the canonical workflow service, including scene/runtime projection
            semantics, because every operation delegates to ``RobotWorkflowService``.
        """
        self._state_store = state_store
        runtime_projection = runtime_projection_service or RuntimeProjectionService(
            state_store,
            fk_uc,
            runtime_asset_service=runtime_asset_service,
        )
        self._workflow = RobotWorkflowService(
            registry=registry,
            fk_uc=fk_uc,
            state_store=state_store,
            runtime_projection_service=runtime_projection,
            importer_registry=None,
            import_robot_uc=import_robot_uc,
            application_workflow=application_workflow,
        )

    def load_robot(self, name: str):
        """Delegate robot loading to the canonical workflow service."""
        return self._workflow.load_robot(name)

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        """Delegate editor-to-spec conversion to the canonical workflow service."""
        return self._workflow.build_robot_from_editor(existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        """Delegate robot persistence to the canonical workflow service."""
        return self._workflow.save_current_robot(rows=rows, home_q=home_q, name=name)

    def import_robot(self, source: str, importer_id: str | None = None, *, persist: bool = True):
        """Delegate import/projection to the canonical workflow service."""
        return self._workflow.import_robot(source, importer_id=importer_id, persist=persist)

    def run_fk(self, q=None):
        """Delegate FK execution to the canonical workflow service."""
        return self._workflow.run_fk(q)

    def sample_ee_positions(self, q_samples) -> np.ndarray:
        """Delegate batch FK sampling to the canonical workflow service."""
        return self._workflow.sample_ee_positions(q_samples)
