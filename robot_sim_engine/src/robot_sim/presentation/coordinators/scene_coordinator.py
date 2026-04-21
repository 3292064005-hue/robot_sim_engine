from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Mapping, cast

from robot_sim.model.render_telemetry import RenderSamplingCounter, normalize_render_sampling_history

from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.application.services.scene_capture_service import SceneCaptureService
from robot_sim.application.use_cases.capture_scene import CaptureSceneUseCase
from robot_sim.application.workers.screenshot_worker import ScreenshotWorker
from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent
from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented
from robot_sim.render.screenshot_service import ScreenshotService

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import SceneTaskView


class SceneCoordinator:
    """Own scene-toolbar orchestration for the main window."""

    def __init__(
        self,
        window: 'SceneTaskView',
        *,
        runtime=None,
        threader=None,
        screenshot_service: ScreenshotService | None = None,
        capture_scene_use_case: CaptureSceneUseCase | None = None,
        scene_authority_service: SceneAuthorityService | None = None,
        scene_capture_service: SceneCaptureService | None = None,
    ) -> None:
        """Construct the stable scene coordinator."""
        self.window = window
        self.runtime = require_dependency(runtime, 'runtime_facade')
        self.threader = require_dependency(threader, 'threader')
        self.screenshot_service = screenshot_service or ScreenshotService()
        self.capture_scene_use_case = capture_scene_use_case or CaptureSceneUseCase(self.screenshot_service)
        self.scene_capture_service = scene_capture_service or SceneCaptureService(self.capture_scene_use_case)
        self.scene_authority_service = scene_authority_service or SceneAuthorityService()

    def fit(self) -> None:
        require_view(self.window, 'project_scene_fit')

    def clear_path(self) -> None:
        require_view(self.window, 'project_scene_path_cleared')

    def add_obstacle(self) -> None:
        """Create or replace one stable obstacle through the scene authority service."""
        def action() -> None:
            request = require_view(self.window, 'read_scene_obstacle_request')
            if request is None:
                return
            edit = SceneObstacleEdit.from_mapping(request)
            scene = self.scene_authority_service.ensure_scene(
                getattr(self.runtime.state, 'planning_scene', None),
                scene_summary=dict(getattr(self.runtime.state, 'scene_summary', {}) or {}),
                authority='scene_coordinator',
                edit_surface='stable_scene_editor',
            )
            mutation = self.scene_authority_service.execute_obstacle_edit(
                scene,
                edit,
                source='scene_toolbar',
            )
            updated_scene = mutation.scene
            self.runtime.state_store.patch_scene(updated_scene.summary(), planning_scene=updated_scene, scene_revision=int(updated_scene.revision))
            runtime_asset_service = getattr(self.runtime, 'runtime_asset_service', None)
            robot_spec = getattr(self.runtime.state, 'robot_spec', None)
            if runtime_asset_service is not None and robot_spec is not None:
                runtime_asset_service.invalidate(robot_spec, reason='scene_edit')
            require_view(self.window, 'project_scene_obstacles_updated', updated_scene)

        run_presented(self.window, action, title='场景障碍更新失败')

    def clear_obstacles(self) -> None:
        """Clear runtime planning-scene obstacles through the stable UI action path."""
        def action() -> None:
            scene = self.scene_authority_service.ensure_scene(
                getattr(self.runtime.state, 'planning_scene', None),
                scene_summary=dict(getattr(self.runtime.state, 'scene_summary', {}) or {}),
                authority='scene_coordinator',
                edit_surface='stable_scene_editor',
            )
            mutation = self.scene_authority_service.execute_clear_obstacles(
                scene,
                source='scene_toolbar',
            )
            updated_scene = mutation.scene
            self.runtime.state_store.patch_scene(updated_scene.summary(), planning_scene=updated_scene, scene_revision=int(updated_scene.revision))
            runtime_asset_service = getattr(self.runtime, 'runtime_asset_service', None)
            robot_spec = getattr(self.runtime.state, 'robot_spec', None)
            if runtime_asset_service is not None and robot_spec is not None:
                runtime_asset_service.invalidate(robot_spec, reason='scene_edit')
            require_view(self.window, 'project_scene_obstacles_updated', updated_scene)

        run_presented(self.window, action, title='清空场景障碍失败')

    def capture(self) -> None:
        """Capture the current scene into the configured runtime export directory."""
        def action() -> None:
            export_root = require_dependency(getattr(self.runtime, 'export_root', None), 'runtime_facade.export_root')
            request = require_view(self.window, 'build_scene_capture_request', Path(export_root) / 'scene_capture.png')
            require_view(self.window, 'project_task_started', 'screenshot', '场景截图任务已启动')
            task = self.threader.start(
                worker=ScreenshotWorker(self._capture_from_request, request),
                on_finished=self._project_capture_success,
                on_failed_event=self._project_capture_failure_event,
                on_cancelled_event=self._project_capture_cancelled_event,
                task_kind='screenshot',
            )
            require_view(self.window, 'project_task_registered', task.task_id, task.task_kind)

        run_presented(self.window, action, title='截图失败')

    def _capture_from_request(self, request: dict[str, object], *, progress_cb=None, cancel_flag=None, correlation_id: str = '') -> dict[str, object]:
        """Render and persist a scene-capture request outside the UI thread."""
        return self.scene_capture_service.execute_request(
            request,
            progress_cb=progress_cb,
            cancel_flag=cancel_flag,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _extract_capture_telemetry(metadata_payload: Mapping[str, object] | None) -> dict[str, object]:
        """Extract capture telemetry from structured worker-event metadata."""
        metadata = dict(metadata_payload or {})
        telemetry = metadata.get('telemetry')
        if isinstance(telemetry, Mapping):
            return dict(cast(Mapping[str, object], telemetry))
        nested_metadata = metadata.get('metadata')
        if isinstance(nested_metadata, Mapping):
            nested_telemetry = nested_metadata.get('telemetry')
            if isinstance(nested_telemetry, Mapping):
                return dict(cast(Mapping[str, object], nested_telemetry))
        return {}

    def _record_capture_telemetry(self, telemetry_payload: Mapping[str, object] | None) -> None:
        """Project screenshot telemetry into the shared render-telemetry state store."""
        telemetry = dict(telemetry_payload or {})
        if not telemetry:
            return
        sampling_counters: tuple[RenderSamplingCounter, ...] = normalize_render_sampling_history(
            cast(tuple[RenderSamplingCounter, ...] | list[object] | None, telemetry.get('sampling_counters', ()) or ())
        )
        operation_span = telemetry.get('operation_span')
        if sampling_counters:
            self.runtime.state_store.record_render_sampling_counters(sampling_counters, notify=False)
        if isinstance(operation_span, Mapping):
            self.runtime.state_store.record_render_operation_span(
                str(operation_span.get('capability', 'screenshot') or 'screenshot'),
                str(operation_span.get('operation', 'capture_from_snapshot') or 'capture_from_snapshot'),
                backend=str(operation_span.get('backend', 'snapshot_renderer') or 'snapshot_renderer'),
                status=str(operation_span.get('status', 'succeeded') or 'succeeded'),
                duration_ms=float(operation_span.get('duration_ms', 0.0) or 0.0),
                sample_count=int(operation_span.get('sample_count', 0) or 0),
                source=str(operation_span.get('source', 'scene_capture_worker') or 'scene_capture_worker'),
                error_code=str(operation_span.get('error_code', '') or ''),
                message=str(operation_span.get('message', '') or ''),
                metadata=dict(operation_span.get('metadata', {}) or {}),
                started_at=operation_span.get('started_at'),
                finished_at=operation_span.get('finished_at'),
                notify=False,
            )
        self.runtime.state_store.notify_render()

    def _project_capture_success(self, payload: dict[str, object]) -> None:
        telemetry_payload = payload.get('telemetry', {})
        self._record_capture_telemetry(cast(Mapping[str, object], telemetry_payload or {}))
        require_view(self.window, 'project_scene_capture', payload.get('path'))

    def _project_capture_failure_event(self, event: WorkerFailedEvent) -> None:
        self._record_capture_telemetry(self._extract_capture_telemetry(getattr(event, 'metadata', {})))
        self.window.on_worker_failed(event)

    def _project_capture_cancelled_event(self, event: WorkerCancelledEvent) -> None:
        self._record_capture_telemetry(self._extract_capture_telemetry(getattr(event, 'metadata', {})))
        self.window.on_worker_cancelled()
