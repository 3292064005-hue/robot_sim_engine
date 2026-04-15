from __future__ import annotations

from robot_sim.application.services.export_service import ExportService
from robot_sim.model.session_state import SessionState


class SaveSessionUseCase:
    """Persist a full session snapshot through the export service."""

    def __init__(self, exporter: ExportService) -> None:
        self._exporter = exporter

    def execute(
        self,
        name: str,
        state: SessionState,
        *,
        environment: dict[str, object] | None = None,
        config_snapshot: dict[str, object] | None = None,
        scene_snapshot: dict[str, object] | None = None,
        plugin_snapshot: dict[str, object] | None = None,
        capability_snapshot: dict[str, object] | None = None,
        telemetry_detail: str = 'full',
    ):
        """Save the current session state.

        Args:
            name: Target filename under the export root.
            state: Session state to persist.
            environment: Optional runtime environment snapshot embedded into the manifest.
            config_snapshot: Optional effective config snapshot embedded into the manifest.
            scene_snapshot: Optional planning-scene summary embedded into the manifest.
            plugin_snapshot: Optional plugin/runtime-feature snapshot embedded into the manifest.
            capability_snapshot: Optional full capability-matrix snapshot embedded into the manifest.
            telemetry_detail: Render telemetry export detail level. ``full`` preserves all
                render telemetry arrays, while ``minimal`` exports only counts and sequences.

        Returns:
            Path: Written session JSON path.

        Raises:
            ValueError: If an unsupported telemetry detail is requested.
        """
        return self._exporter.save_session(
            name,
            state,
            environment=environment,
            config_snapshot=config_snapshot,
            scene_snapshot=scene_snapshot,
            plugin_snapshot=plugin_snapshot,
            capability_snapshot=capability_snapshot,
            telemetry_detail=telemetry_detail,
        )
