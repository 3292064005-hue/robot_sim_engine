from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from robot_sim.application.use_cases.capture_scene import CaptureSceneUseCase
from robot_sim.domain.errors import CancelledTaskError, ExportRobotError
from robot_sim.presentation.coordinators.scene_capture_support import (
    SceneCaptureTelemetry,
    build_capture_telemetry,
    build_failed_capture_error,
    ensure_capture_not_cancelled,
)


class SceneCaptureService:
    """Execute snapshot scene capture and normalize telemetry/error contracts.

    This service owns the non-UI screenshot orchestration path so the presentation
    coordinator only manages worker lifecycle and UI projection.
    """

    def __init__(self, capture_scene_use_case: CaptureSceneUseCase) -> None:
        if capture_scene_use_case is None:
            raise ValueError('scene capture service requires a capture_scene_use_case')
        self._capture_scene_use_case = capture_scene_use_case

    def execute_request(
        self,
        request: Mapping[str, object],
        *,
        progress_cb=None,
        cancel_flag=None,
        correlation_id: str = '',
    ) -> dict[str, object]:
        """Capture a structured snapshot request outside the UI thread.

        Args:
            request: Scene-capture payload built on the UI thread.
            progress_cb: Optional structured progress callback.
            cancel_flag: Optional cooperative cancellation probe.
            correlation_id: Stable task correlation identifier.

        Returns:
            dict[str, object]: ``{'path': ..., 'telemetry': ...}`` success payload.

        Raises:
            CancelledTaskError: If cooperative cancellation is requested before completion.
            ExportRobotError: If the snapshot payload is invalid or rendering/export fails.

        Boundary behavior:
            The service always attaches structured terminal telemetry to cancellation and
            failure paths so worker-event projection uses one normalized contract.
        """
        payload = dict(request or {})
        telemetry_source = 'scene_capture_worker'
        path_value = payload.get('path')
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
                raise ValueError('scene capture request is missing an output path')
            snapshot = payload.get('snapshot')
            if not isinstance(snapshot, Mapping):
                raise TypeError('scene capture snapshot must be a mapping')
            counters = tuple(
                self._capture_scene_use_case.snapshot_sampling_counters(
                    snapshot,
                    backend='snapshot_renderer',
                    source=telemetry_source,
                )
            )
            sample_count = self._capture_scene_use_case.snapshot_sample_count(snapshot)
            capture_provenance = self._capture_scene_use_case.snapshot_provenance(snapshot, backend='snapshot_renderer')
            details = self._capture_scene_use_case.execute_snapshot_details(
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
            raise CancelledTaskError(
                str(exc) or 'scene capture cancelled',
                error_code=exc.error_code,
                remediation_hint=exc.remediation_hint,
                metadata={**dict(exc.metadata), 'telemetry': self._terminal_telemetry(
                    path=path,
                    telemetry_source=telemetry_source,
                    sample_count=sample_count,
                    counters=counters,
                    started_at=started_at,
                    started_perf=started_perf,
                    status='cancelled',
                    message='scene capture cancelled',
                    correlation_id=correlation_id,
                    backend=capture_backend,
                    capture_level=capture_level,
                    capture_provenance=capture_provenance,
                ).as_dict()},
            ) from exc
        except (ExportRobotError, OSError, RuntimeError, TypeError, ValueError) as exc:
            telemetry = self._terminal_telemetry(
                path=path,
                telemetry_source=telemetry_source,
                sample_count=sample_count,
                counters=counters,
                started_at=started_at,
                started_perf=started_perf,
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
        telemetry = self._terminal_telemetry(
            path=Path(str(result)),
            telemetry_source=telemetry_source,
            sample_count=sample_count,
            counters=counters,
            started_at=started_at,
            started_perf=started_perf,
            status='succeeded',
            message='scene screenshot completed',
            correlation_id=correlation_id,
            backend=capture_backend,
            capture_level=capture_level,
            capture_provenance=capture_provenance,
        )
        return {'path': result, 'telemetry': telemetry.as_dict()}

    @staticmethod
    def _terminal_telemetry(
        *,
        path: Path,
        telemetry_source: str,
        sample_count: int,
        counters: tuple[object, ...],
        started_at: datetime,
        started_perf: float,
        status: str,
        message: str,
        correlation_id: str,
        error_code: str = '',
        backend: str = 'snapshot_renderer',
        capture_level: str = '',
        capture_provenance: Mapping[str, object] | None = None,
        extra_metadata: Mapping[str, object] | None = None,
    ) -> SceneCaptureTelemetry:
        """Build terminal screenshot telemetry for one capture outcome."""
        finished_at = datetime.now(timezone.utc)
        return build_capture_telemetry(
            path=path,
            telemetry_source=telemetry_source,
            sample_count=sample_count,
            counters=counters,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(perf_counter() - started_perf) * 1000.0,
            status=status,
            message=message,
            correlation_id=correlation_id,
            error_code=error_code,
            backend=backend,
            capture_level=capture_level,
            capture_provenance=capture_provenance,
            extra_metadata=extra_metadata,
        )
