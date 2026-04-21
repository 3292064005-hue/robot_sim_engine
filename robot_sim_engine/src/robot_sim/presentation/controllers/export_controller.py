from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.workflow_services import ExportWorkflowService

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.app.workflow_facade import ApplicationWorkflowFacade


class ExportController:
    LEGACY_SURFACE_ID = 'compatibility.export_controller.v1'

    """Compatibility export controller that delegates to the canonical export workflow.

    The controller remains available for legacy callers, but it must not maintain an
    independent export orchestration path. All public export operations delegate to
    :class:`ExportWorkflowService`, which in turn delegates application-level writes to
    :class:`ApplicationWorkflowFacade`.
    """

    def __init__(
        self,
        state_store: StateStore,
        exporter: ExportService,
        export_report_uc: ExportReportUseCase,
        save_session_uc: SaveSessionUseCase,
        export_package_uc: ExportPackageUseCase | None = None,
        *,
        runtime_facade: object | None = None,
        application_workflow: 'ApplicationWorkflowFacade | None' = None,
    ) -> None:
        """Create the compatibility export controller.

        Args:
            state_store: Shared presentation state store.
            exporter: Low-level export service for raw artifact writes.
            export_report_uc: Report export use case.
            save_session_uc: Session export use case.
            export_package_uc: Optional package export use case.
            runtime_facade: Runtime metadata facade consumed when building manifests.
            application_workflow: Canonical application workflow facade. Required for
                session/package/trajectory/benchmark export orchestration.

        Returns:
            None: Stores a delegate workflow service.

        Raises:
            None: Construction only stores references. Runtime validation happens when
                callers invoke export operations.
        """
        self._workflow = ExportWorkflowService(
            state_store=state_store,
            exporter=exporter,
            export_report_use_case=export_report_uc,
            save_session_use_case=save_session_uc,
            export_package_use_case=export_package_uc,
            runtime_facade=runtime_facade,
            application_workflow=application_workflow,
        )

    def export_trajectory_bundle(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name):
        """Export the active trajectory bundle through the canonical workflow service."""
        return self._workflow.export_trajectory_bundle(name)

    def export_trajectory_metrics(self, name: str = DEFAULT_EXPORT_ARTIFACTS.trajectory_metrics_name, metrics: dict | None = None):
        """Export trajectory metrics as JSON through the canonical workflow service."""
        return self._workflow.export_trajectory_metrics(name, metrics or {})

    def export_benchmark(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name):
        """Export the active benchmark summary JSON through the canonical workflow service."""
        return self._workflow.export_benchmark(name)

    def export_benchmark_cases_csv(self, name: str = DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name):
        """Export benchmark case rows as CSV through the canonical workflow service."""
        return self._workflow.export_benchmark_cases_csv(name)

    def export_session(self, name: str = DEFAULT_EXPORT_ARTIFACTS.session_name, *, telemetry_detail: str = 'full'):
        """Export the active session snapshot through the canonical workflow service."""
        return self._workflow.export_session(name, telemetry_detail=telemetry_detail)

    def export_package(self, name: str = DEFAULT_EXPORT_ARTIFACTS.package_name, *, telemetry_detail: str = 'minimal') -> Path:
        """Export the current artifact package through the canonical workflow service."""
        return self._workflow.export_package(name, telemetry_detail=telemetry_detail)
