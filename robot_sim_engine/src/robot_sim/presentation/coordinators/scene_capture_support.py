from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from robot_sim.domain.errors import CancelledTaskError, ExportRobotError


@dataclass(frozen=True)
class SceneCaptureTelemetry:
    """Structured screenshot telemetry bundle projected by scene capture flows."""

    operation_span: dict[str, object]
    sampling_counters: tuple[object, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            'operation_span': dict(self.operation_span),
            'sampling_counters': tuple(self.sampling_counters),
        }


def ensure_capture_not_cancelled(cancel_flag) -> None:
    """Raise ``CancelledTaskError`` when cooperative screenshot cancellation is requested."""
    if callable(cancel_flag) and bool(cancel_flag()):
        raise CancelledTaskError('scene capture cancelled')


def build_capture_telemetry(
    *,
    path: Path,
    telemetry_source: str,
    sample_count: int,
    counters: tuple[object, ...],
    started_at: datetime,
    finished_at: datetime,
    duration_ms: float,
    status: str,
    message: str,
    correlation_id: str,
    error_code: str = '',
    backend: str = 'snapshot_renderer',
    capture_level: str = '',
    capture_provenance: Mapping[str, object] | None = None,
    extra_metadata: Mapping[str, object] | None = None,
) -> SceneCaptureTelemetry:
    """Build structured screenshot telemetry for a terminal capture outcome."""
    metadata: dict[str, object] = {'correlation_id': correlation_id, 'path': str(path)}
    if capture_level:
        metadata['capture_level'] = str(capture_level)
    if capture_provenance:
        metadata['capture_provenance'] = dict(capture_provenance)
    if extra_metadata:
        metadata.update({str(key): value for key, value in dict(extra_metadata).items()})
    return SceneCaptureTelemetry(
        operation_span={
            'capability': 'screenshot',
            'operation': 'capture_from_snapshot',
            'backend': str(backend or 'snapshot_renderer'),
            'status': status,
            'duration_ms': duration_ms,
            'sample_count': sample_count,
            'source': telemetry_source,
            'error_code': error_code,
            'message': message,
            'metadata': metadata,
            'started_at': started_at,
            'finished_at': finished_at,
        },
        sampling_counters=tuple(counters),
    )


def build_failed_capture_error(exc: Exception, *, telemetry: Mapping[str, object]) -> ExportRobotError:
    """Normalize screenshot failures into ``ExportRobotError`` while preserving telemetry."""
    if isinstance(exc, ExportRobotError):
        return ExportRobotError(
            str(exc),
            error_code=exc.error_code,
            remediation_hint=exc.remediation_hint,
            metadata={**dict(exc.metadata), 'telemetry': dict(telemetry), 'exception_type': exc.__class__.__name__},
        )
    return ExportRobotError(
        str(exc),
        metadata={'telemetry': dict(telemetry), 'exception_type': exc.__class__.__name__},
    )
