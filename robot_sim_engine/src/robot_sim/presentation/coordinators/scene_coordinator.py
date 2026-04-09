from __future__ import annotations

<<<<<<< HEAD
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any, Mapping, cast

from robot_sim.model.render_telemetry import RenderSamplingCounter, normalize_render_sampling_history

from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.application.use_cases.capture_scene import CaptureSceneUseCase
from robot_sim.application.workers.screenshot_worker import ScreenshotWorker
from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent
from robot_sim.domain.errors import CancelledTaskError, ExportRobotError
from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented
from robot_sim.presentation.coordinators.scene_capture_support import (
    build_capture_telemetry,
    build_failed_capture_error,
    ensure_capture_not_cancelled,
)
from robot_sim.render.screenshot_service import ScreenshotService

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import SceneTaskView
=======
from pathlib import Path

from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


class SceneCoordinator:
    """Own scene-toolbar orchestration for the main window."""

<<<<<<< HEAD
    def __init__(
        self,
        window: 'SceneTaskView',
        *,
        runtime=None,
        threader=None,
        screenshot_service: ScreenshotService | None = None,
        capture_scene_use_case: CaptureSceneUseCase | None = None,
        capture_scene_uc: CaptureSceneUseCase | None = None,
        scene_authority_service: SceneAuthorityService | None = None,
    ) -> None:
        """Construct the stable scene coordinator.

        Args:
            window: Scene task view contract.
            runtime: Runtime facade dependency.
            threader: Background task orchestrator.
            screenshot_service: Optional screenshot service override.
            capture_scene_use_case: Preferred capture use-case dependency.
            capture_scene_uc: Backward-compatible alias for older callers.
            scene_authority_service: Optional scene authority service override.

        Raises:
            ValueError: If both capture use-case parameters are supplied but disagree.
        """
        if capture_scene_use_case is not None and capture_scene_uc is not None and capture_scene_use_case is not capture_scene_uc:
            raise ValueError('capture_scene_use_case and capture_scene_uc must reference the same use case when both are provided')
        self.window = window
        self.runtime = require_dependency(runtime, 'runtime_facade')
        self.threader = require_dependency(threader, 'threader')
        self.screenshot_service = screenshot_service or ScreenshotService()
        effective_capture_use_case = capture_scene_use_case or capture_scene_uc
        self.capture_scene_use_case = effective_capture_use_case or CaptureSceneUseCase(self.screenshot_service)
        self.scene_authority_service = scene_authority_service or SceneAuthorityService()
=======
    def __init__(self, window, *, runtime=None) -> None:
        self.window = window
        self.runtime = require_dependency(
            runtime if runtime is not None else getattr(window, 'runtime_facade', None),
            'runtime_facade',
        )
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    def fit(self) -> None:
        require_view(self.window, 'project_scene_fit')

    def clear_path(self) -> None:
        require_view(self.window, 'project_scene_path_cleared')

<<<<<<< HEAD
    def add_obstacle(self) -> None:
        """Create or replace one stable box obstacle through the scene authority service.

        Returns:
            None: Updates runtime scene state and UI projection in place.

        Raises:
            AttributeError: If required runtime or view contracts are unavailable.
            ValueError: If the editor payload is malformed.

        Boundary behavior:
            Duplicate identifiers are either replaced or deterministically suffixed based on
            the structured editor payload rather than implicit coordinator heuristics.
        """
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
            updated_scene = self.scene_authority_service.apply_obstacle_edit(
                scene,
                edit,
                source='scene_toolbar',
            )
            self.runtime.state_store.patch_scene(updated_scene.summary(), planning_scene=updated_scene, scene_revision=int(updated_scene.revision))
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
            updated_scene = scene.clear_obstacles()
            self.runtime.state_store.patch_scene(updated_scene.summary(), planning_scene=updated_scene, scene_revision=int(updated_scene.revision))
            require_view(self.window, 'project_scene_obstacles_updated', updated_scene)

        run_presented(self.window, action, title='清空场景障碍失败')

    def capture(self) -> None:
        """Capture the current scene into the configured runtime export directory.

        Returns:
            None: Schedules the scene-capture write path on the shared worker runtime.

        Raises:
            AttributeError: If required runtime or view contracts are unavailable.
        """

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
        """Render and persist a scene-capture request outside the UI thread.

        Args:
            request: Scene-capture payload built on the UI thread.
            progress_cb: Optional structured progress callback supplied by ``ScreenshotWorker``.
            cancel_flag: Optional cooperative cancellation probe supplied by ``ScreenshotWorker``.
            correlation_id: Stable task correlation identifier.

        Returns:
            dict[str, object]: Structured success payload containing the saved screenshot
                path plus span/counter telemetry captured for the snapshot render.

        Raises:
            CancelledTaskError: If cooperative cancellation is requested before terminal
                success. The exception metadata carries structured telemetry.
            ExportRobotError: Propagates screenshot rendering/export failures with
                structured telemetry attached to the exception metadata.
        """
        telemetry_source = 'scene_capture_worker'
        path_value = request.get('path')
        path = Path(str(path_value or 'scene_capture.png'))
        counters: tuple[object, ...] = ()
        sample_count = 0
        capture_level = ''
        capture_provenance: dict[str, object] = {}
        capture_backend = 'snapshot_renderer'
        if callable(progress_cb):
            progress_cb(5.0, 'preparing scene snapshot export', {'path': str(path), 'correlation_id': correlation_id})
        ensure_capture_not_cancelled(cancel_flag)
        started_at = datetime.now(timezone.utc)
        started_perf = perf_counter()
        try:
            if path_value in (None, ''):
                raise ValueError('scene capture path is required')
            snapshot_payload = request.get('snapshot', {})
            if snapshot_payload is None:
                snapshot = {}
            elif isinstance(snapshot_payload, Mapping):
                snapshot = dict(cast(Mapping[str, Any], snapshot_payload))
            else:
                raise TypeError('scene capture snapshot must be a mapping')
            path = Path(str(path_value))
            counters = tuple(
                self.capture_scene_use_case.snapshot_sampling_counters(
                    snapshot,
                    backend='snapshot_renderer',
                    source=telemetry_source,
                )
            )
            sample_count = self.capture_scene_use_case.snapshot_sample_count(snapshot)
            capture_provenance = self.capture_scene_use_case.snapshot_provenance(snapshot, backend='snapshot_renderer')
            details = self.capture_scene_use_case.execute_snapshot_details(
                snapshot,
                path,
                progress_cb=progress_cb,
                cancel_flag=cancel_flag,
                correlation_id=correlation_id,
            )
            if isinstance(details, Mapping):
                runtime_state = details.get('runtime_state')
                if runtime_state is not None:
                    capture_backend = str(getattr(runtime_state, 'backend', capture_backend) or capture_backend)
                    capture_level = str(getattr(runtime_state, 'level', '') or '')
                    capture_provenance = dict(getattr(runtime_state, 'provenance', capture_provenance) or capture_provenance)
                result = details.get('path', path)
            else:
                result = details
        except CancelledTaskError as exc:
            finished_at = datetime.now(timezone.utc)
            telemetry = build_capture_telemetry(
                path=path,
                telemetry_source=telemetry_source,
                sample_count=sample_count,
                counters=counters,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(perf_counter() - started_perf) * 1000.0,
                status='cancelled',
                message='scene capture cancelled',
                correlation_id=correlation_id,
                backend=capture_backend,
                capture_level=capture_level,
                capture_provenance=capture_provenance,
            )
            raise CancelledTaskError(
                str(exc) or 'scene capture cancelled',
                error_code=exc.error_code,
                remediation_hint=exc.remediation_hint,
                metadata={**dict(exc.metadata), 'telemetry': telemetry.as_dict()},
            ) from exc
        except (ExportRobotError, OSError, RuntimeError, TypeError, ValueError) as exc:
            finished_at = datetime.now(timezone.utc)
            telemetry = build_capture_telemetry(
                path=path,
                telemetry_source=telemetry_source,
                sample_count=sample_count,
                counters=counters,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(perf_counter() - started_perf) * 1000.0,
                status='failed',
                message=str(exc),
                correlation_id=correlation_id,
                error_code=str(getattr(exc, 'error_code', '') or ''),
                backend=capture_backend,
                capture_level=capture_level,
                capture_provenance=capture_provenance,
                extra_metadata={'exception_type': exc.__class__.__name__},
            )
            normalized_error = build_failed_capture_error(exc, telemetry=telemetry.as_dict())
            raw_telemetry_payload = normalized_error.metadata.get('telemetry', {}) or {}
            telemetry_payload = dict(raw_telemetry_payload) if isinstance(raw_telemetry_payload, Mapping) else {}
            raw_operation_span = telemetry_payload.get('operation_span', {}) or {}
            operation_span = dict(raw_operation_span) if isinstance(raw_operation_span, Mapping) else {}
            if not str(operation_span.get('error_code', '') or ''):
                operation_span['error_code'] = normalized_error.error_code
                telemetry_payload['operation_span'] = operation_span
                normalized_error.metadata['telemetry'] = telemetry_payload
            raise normalized_error from exc
        finished_at = datetime.now(timezone.utc)
        telemetry = build_capture_telemetry(
            path=Path(str(result)),
            telemetry_source=telemetry_source,
            sample_count=sample_count,
            counters=counters,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(perf_counter() - started_perf) * 1000.0,
            status='succeeded',
            message='scene screenshot completed',
            correlation_id=correlation_id,
            backend=capture_backend,
            capture_level=capture_level,
            capture_provenance=capture_provenance,
        )
        return {'path': result, 'telemetry': telemetry.as_dict()}

    @staticmethod
    def _extract_capture_telemetry(metadata_payload: Mapping[str, object] | None) -> dict[str, object]:
        """Extract capture telemetry from structured worker-event metadata.

        Args:
            metadata_payload: Worker event metadata payload.

        Returns:
            dict[str, object]: Normalized screenshot telemetry payload or an empty mapping.

        Raises:
            None: Defensive normalization only.
        """
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
        """Project screenshot telemetry into the shared render-telemetry state store.

        Args:
            telemetry_payload: Structured telemetry payload emitted by the capture worker.

        Returns:
            None: Writes bounded render telemetry histories and flushes render subscribers.

        Raises:
            None: Empty or malformed telemetry payloads are ignored defensively.
        """
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
        """Project a successful scene capture back into the UI shell.

        Args:
            payload: Structured success payload emitted by ``ScreenshotWorker``.

        Returns:
            None: Flushes render telemetry and updates the user-visible screenshot result.

        Raises:
            None: Projection errors are delegated to existing UI view contracts.
        """
        telemetry_payload = payload.get('telemetry', {})
        self._record_capture_telemetry(cast(Mapping[str, object], telemetry_payload or {}))
        require_view(self.window, 'project_scene_capture', payload.get('path'))

    def _project_capture_failure_event(self, event: WorkerFailedEvent) -> None:
        """Project a failed screenshot event through the canonical worker-failure path.

        Args:
            event: Structured worker failure event emitted by ``ScreenshotWorker``.

        Returns:
            None: Flushes render telemetry and delegates UI failure projection.

        Raises:
            None: Projection is side-effect only.
        """
        self._record_capture_telemetry(self._extract_capture_telemetry(getattr(event, 'metadata', {})))
        self.window.on_worker_failed(event)

    def _project_capture_cancelled_event(self, event: WorkerCancelledEvent) -> None:
        """Project a cancelled screenshot event through the canonical cancel path.

        Args:
            event: Structured worker cancellation event emitted by ``ScreenshotWorker``.

        Returns:
            None: Flushes render telemetry and delegates UI cancellation projection.

        Raises:
            None: Projection is side-effect only.
        """
        self._record_capture_telemetry(self._extract_capture_telemetry(getattr(event, 'metadata', {})))
        self.window.on_worker_cancelled()
=======
    def capture(self) -> None:
        """Capture the current scene into the configured runtime export directory.

        Raises:
            AttributeError: If the required runtime export root or view capture contract is missing.
        """
        def action() -> None:
            export_root = require_dependency(getattr(self.runtime, 'export_root', None), 'runtime_facade.export_root')
            path = Path(export_root) / 'scene_capture.png'
            result = require_view(self.window, 'capture_scene_screenshot', path)
            require_view(self.window, 'project_scene_capture', result)

        run_presented(self.window, action, title='截图失败')
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
